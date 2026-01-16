from django.db.models import Count, Sum, Q, F, Avg
from django.db.models.functions import TruncMonth, TruncYear
from datetime import datetime, timedelta
from decimal import Decimal

class AnalyticsService:
    """Service pour les analyses commerciales et opérationnelles"""
    
    def __init__(self, expedition_model, tournee_model, facture_model, client_model, chauffeur_model, incident_model):
        self.Expedition = expedition_model
        self.Tournee = tournee_model
        self.Facture = facture_model
        self.Client = client_model
        self.Chauffeur = chauffeur_model
        self.Incident = incident_model
    
    # ============== ANALYSES COMMERCIALES ==============
    
    def get_expeditions_evolution(self, start_date, end_date, period='month'):
        """
        Calcule l'évolution du nombre d'expéditions sur une période
        period: 'month' ou 'year'
        """
        trunc_func = TruncMonth('date_creation') if period == 'month' else TruncYear('date_creation')
        
        data = self.Expedition.objects.filter(
            date_creation__gte=start_date,
            date_creation__lte=end_date
        ).annotate(
            periode=trunc_func
        ).values('periode').annotate(
            nombre_expeditions=Count('id'),
            montant_total=Sum('montant_total')
        ).order_by('periode')
        
        # Calcul des taux d'évolution
        result = list(data)
        for i in range(1, len(result)):
            prev_count = result[i-1]['nombre_expeditions']
            curr_count = result[i]['nombre_expeditions']
            if prev_count > 0:
                taux_evolution = ((curr_count - prev_count) / prev_count) * 100
                result[i]['taux_evolution_volume'] = round(taux_evolution, 2)
            
            prev_montant = result[i-1]['montant_total'] or 0
            curr_montant = result[i]['montant_total'] or 0
            if prev_montant > 0:
                taux_evolution_ca = ((curr_montant - prev_montant) / prev_montant) * 100
                result[i]['taux_evolution_ca'] = round(taux_evolution_ca, 2)
        
        return result
    
    def get_chiffre_affaires_evolution(self, start_date, end_date, period='month'):
        """Évolution du chiffre d'affaires"""
        trunc_func = TruncMonth('date_facture') if period == 'month' else TruncYear('date_facture')
        
        data = self.Facture.objects.filter(
            date_facture__gte=start_date,
            date_facture__lte=end_date
        ).annotate(
            periode=trunc_func
        ).values('periode').annotate(
            ca_ht=Sum('montant_ht'),
            ca_ttc=Sum('montant_ttc'),
            nombre_factures=Count('id')
        ).order_by('periode')
        
        return list(data)
    
    def get_top_clients(self, start_date, end_date, limit=10, by='volume'):
        """
        Récupère les meilleurs clients
        by: 'volume' (nombre d'expéditions) ou 'valeur' (montant total)
        """
        order_field = '-nombre_expeditions' if by == 'volume' else '-montant_total'
        
        data = self.Expedition.objects.filter(
            date_creation__gte=start_date,
            date_creation__lte=end_date
        ).values(
            'client__id',
            'client__nom',
            'client__prenom',
            'client__email'
        ).annotate(
            nombre_expeditions=Count('id'),
            montant_total=Sum('montant_total')
        ).order_by(order_field)[:limit]
        
        return list(data)
    
    def get_destinations_populaires(self, start_date, end_date, limit=10):
        """Destinations les plus sollicitées"""
        data = self.Expedition.objects.filter(
            date_creation__gte=start_date,
            date_creation__lte=end_date
        ).values(
            'destination__ville',
            'destination__pays'
        ).annotate(
            nombre_expeditions=Count('id'),
            montant_total=Sum('montant_total')
        ).order_by('-nombre_expeditions')[:limit]
        
        return list(data)
    
    def get_services_performance(self, start_date, end_date):
        """Performance par type de service"""
        data = self.Expedition.objects.filter(
            date_creation__gte=start_date,
            date_creation__lte=end_date
        ).values(
            'type_service__nom',
            'type_service__description'
        ).annotate(
            nombre_expeditions=Count('id'),
            montant_total=Sum('montant_total'),
            montant_moyen=Avg('montant_total')
        ).order_by('-nombre_expeditions')
        
        return list(data)
    
    # ============== ANALYSES OPÉRATIONNELLES ==============
    
    def get_tournees_evolution(self, start_date, end_date, period='month'):
        """Évolution du nombre de tournées"""
        trunc_func = TruncMonth('date_tournee') if period == 'month' else TruncYear('date_tournee')
        
        data = self.Tournee.objects.filter(
            date_tournee__gte=start_date,
            date_tournee__lte=end_date
        ).annotate(
            periode=trunc_func
        ).values('periode').annotate(
            nombre_tournees=Count('id'),
            kilometrage_total=Sum('kilometrage'),
            duree_totale=Sum('duree'),
            conso_carburant_totale=Sum('consommation_carburant')
        ).order_by('periode')
        
        result = list(data)
        for i in range(1, len(result)):
            prev = result[i-1]['nombre_tournees']
            curr = result[i]['nombre_tournees']
            if prev > 0:
                taux = ((curr - prev) / prev) * 100
                result[i]['taux_evolution'] = round(taux, 2)
        
        return result
    
    def get_taux_reussite_livraisons(self, start_date, end_date):
        """Calcule le taux de réussite des livraisons"""
        total = self.Expedition.objects.filter(
            date_creation__gte=start_date,
            date_creation__lte=end_date
        ).count()
        
        if total == 0:
            return {
                'total': 0,
                'livres': 0,
                'echecs': 0,
                'retards': 0,
                'en_cours': 0,
                'taux_reussite': 0,
                'taux_echec': 0
            }
        
        livres = self.Expedition.objects.filter(
            date_creation__gte=start_date,
            date_creation__lte=end_date,
            statut='livré'
        ).count()
        
        echecs = self.Expedition.objects.filter(
            date_creation__gte=start_date,
            date_creation__lte=end_date,
            statut='échec de livraison'
        ).count()
        
        # Compter les retards via les incidents
        retards = self.Incident.objects.filter(
            expedition__date_creation__gte=start_date,
            expedition__date_creation__lte=end_date,
            type_incident__icontains='retard'
        ).values('expedition').distinct().count()
        
        en_cours = total - livres - echecs
        
        return {
            'total': total,
            'livres': livres,
            'echecs': echecs,
            'retards': retards,
            'en_cours': en_cours,
            'taux_reussite': round((livres / total) * 100, 2),
            'taux_echec': round((echecs / total) * 100, 2),
            'taux_retard': round((retards / total) * 100, 2)
        }
    
    def get_top_chauffeurs(self, start_date, end_date, limit=10):
        """Meilleurs chauffeurs par performance"""
        data = self.Tournee.objects.filter(
            date_tournee__gte=start_date,
            date_tournee__lte=end_date
        ).values(
            'chauffeur__id',
            'chauffeur__nom',
            'chauffeur__prenom'
        ).annotate(
            nombre_tournees=Count('id'),
            kilometrage_total=Sum('kilometrage'),
            nombre_livraisons=Count('expeditions'),
            duree_moyenne=Avg('duree')
        ).order_by('-nombre_tournees')[:limit]
        
        # Ajouter le taux de réussite pour chaque chauffeur
        result = list(data)
        for chauffeur in result:
            tournees = self.Tournee.objects.filter(
                chauffeur__id=chauffeur['chauffeur__id'],
                date_tournee__gte=start_date,
                date_tournee__lte=end_date
            )
            
            total_exp = self.Expedition.objects.filter(tournee__in=tournees).count()
            livrees = self.Expedition.objects.filter(
                tournee__in=tournees,
                statut='livré'
            ).count()
            
            chauffeur['taux_reussite'] = round((livrees / total_exp * 100), 2) if total_exp > 0 else 0
        
        return result
    
    def get_zones_incidents(self, start_date, end_date, limit=10):
        """Zones géographiques avec le plus d'incidents"""
        data = self.Incident.objects.filter(
            date_incident__gte=start_date,
            date_incident__lte=end_date,
            expedition__isnull=False
        ).values(
            'expedition__destination__ville',
            'expedition__destination__pays'
        ).annotate(
            nombre_incidents=Count('id'),
            types_incidents=Count('type_incident', distinct=True)
        ).order_by('-nombre_incidents')[:limit]
        
        return list(data)
    
    def get_periodes_forte_activite(self, start_date, end_date):
        """Identifie les périodes de forte activité"""
        # Par mois
        par_mois = self.Expedition.objects.filter(
            date_creation__gte=start_date,
            date_creation__lte=end_date
        ).annotate(
            mois=TruncMonth('date_creation')
        ).values('mois').annotate(
            nombre_expeditions=Count('id')
        ).order_by('-nombre_expeditions')[:3]
        
        # Par jour de la semaine
        from django.db.models.functions import ExtractWeekDay
        par_jour_semaine = self.Expedition.objects.filter(
            date_creation__gte=start_date,
            date_creation__lte=end_date
        ).annotate(
            jour_semaine=ExtractWeekDay('date_creation')
        ).values('jour_semaine').annotate(
            nombre_expeditions=Count('id')
        ).order_by('-nombre_expeditions')
        
        jours = {1: 'Dimanche', 2: 'Lundi', 3: 'Mardi', 4: 'Mercredi', 
                 5: 'Jeudi', 6: 'Vendredi', 7: 'Samedi'}
        
        result_jours = []
        for item in par_jour_semaine:
            result_jours.append({
                'jour': jours.get(item['jour_semaine'], 'Inconnu'),
                'nombre_expeditions': item['nombre_expeditions']
            })
        
        return {
            'mois_forts': list(par_mois),
            'jours_forts': result_jours
        }
    
    # ============== STATISTIQUES GLOBALES ==============
    
    def get_kpi_dashboard(self, start_date, end_date):
        """Récupère tous les KPI pour le tableau de bord"""
        # Expéditions
        total_expeditions = self.Expedition.objects.filter(
            date_creation__gte=start_date,
            date_creation__lte=end_date
        ).count()
        
        montant_total_exp = self.Expedition.objects.filter(
            date_creation__gte=start_date,
            date_creation__lte=end_date
        ).aggregate(total=Sum('montant_total'))['total'] or 0
        
        # Factures
        ca_ttc = self.Facture.objects.filter(
            date_facture__gte=start_date,
            date_facture__lte=end_date
        ).aggregate(total=Sum('montant_ttc'))['total'] or 0
        
        # Tournées
        total_tournees = self.Tournee.objects.filter(
            date_tournee__gte=start_date,
            date_tournee__lte=end_date
        ).count()
        
        km_total = self.Tournee.objects.filter(
            date_tournee__gte=start_date,
            date_tournee__lte=end_date
        ).aggregate(total=Sum('kilometrage'))['total'] or 0
        
        # Clients actifs
        clients_actifs = self.Expedition.objects.filter(
            date_creation__gte=start_date,
            date_creation__lte=end_date
        ).values('client').distinct().count()
        
        # Incidents
        total_incidents = self.Incident.objects.filter(
            date_incident__gte=start_date,
            date_incident__lte=end_date
        ).count()
        
        return {
            'expeditions': {
                'total': total_expeditions,
                'montant_total': float(montant_total_exp)
            },
            'chiffre_affaires': {
                'ttc': float(ca_ttc)
            },
            'tournees': {
                'total': total_tournees,
                'kilometrage_total': float(km_total)
            },
            'clients_actifs': clients_actifs,
            'incidents': {
                'total': total_incidents
            }
        }