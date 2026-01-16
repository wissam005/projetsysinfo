from django.db.models import Count, Sum, Avg, Max, Min, Q
from django.db.models.functions import TruncDate
from datetime import datetime, timedelta
from collections import defaultdict

class StatsService:
    """Service pour les statistiques détaillées et les comparaisons"""
    
    def __init__(self, expedition_model, tournee_model, facture_model, paiement_model):
        self.Expedition = expedition_model
        self.Tournee = tournee_model
        self.Facture = facture_model
        self.Paiement = paiement_model
    
    # ============== COMPARAISONS ANNUELLES ==============
    
    def compare_years(self, year1, year2):
        """Compare les performances entre deux années"""
        start_y1 = datetime(year1, 1, 1)
        end_y1 = datetime(year1, 12, 31, 23, 59, 59)
        start_y2 = datetime(year2, 1, 1)
        end_y2 = datetime(year2, 12, 31, 23, 59, 59)
        
        # Expéditions
        exp_y1 = self.Expedition.objects.filter(
            date_creation__gte=start_y1,
            date_creation__lte=end_y1
        ).aggregate(
            count=Count('id'),
            total=Sum('montant_total')
        )
        
        exp_y2 = self.Expedition.objects.filter(
            date_creation__gte=start_y2,
            date_creation__lte=end_y2
        ).aggregate(
            count=Count('id'),
            total=Sum('montant_total')
        )
        
        # Tournées
        tour_y1 = self.Tournee.objects.filter(
            date_tournee__gte=start_y1,
            date_tournee__lte=end_y1
        ).count()
        
        tour_y2 = self.Tournee.objects.filter(
            date_tournee__gte=start_y2,
            date_tournee__lte=end_y2
        ).count()
        
        # Calcul des variations
        var_exp = ((exp_y2['count'] - exp_y1['count']) / exp_y1['count'] * 100) if exp_y1['count'] > 0 else 0
        var_montant = ((exp_y2['total'] - exp_y1['total']) / exp_y1['total'] * 100) if exp_y1['total'] else 0
        var_tournees = ((tour_y2 - tour_y1) / tour_y1 * 100) if tour_y1 > 0 else 0
        
        return {
            'year1': {
                'year': year1,
                'expeditions': exp_y1['count'] or 0,
                'montant_total': float(exp_y1['total'] or 0),
                'tournees': tour_y1
            },
            'year2': {
                'year': year2,
                'expeditions': exp_y2['count'] or 0,
                'montant_total': float(exp_y2['total'] or 0),
                'tournees': tour_y2
            },
            'variations': {
                'expeditions': round(var_exp, 2),
                'montant': round(var_montant, 2),
                'tournees': round(var_tournees, 2)
            }
        }
    
    # ============== STATISTIQUES PAR PÉRIODE ==============
    
    def get_daily_stats(self, start_date, end_date):
        """Statistiques quotidiennes"""
        data = self.Expedition.objects.filter(
            date_creation__gte=start_date,
            date_creation__lte=end_date
        ).annotate(
            jour=TruncDate('date_creation')
        ).values('jour').annotate(
            nombre=Count('id'),
            montant=Sum('montant_total')
        ).order_by('jour')
        
        return list(data)
    
    def get_monthly_summary(self, year, month):
        """Résumé mensuel détaillé"""
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
        # Expéditions
        expeditions = self.Expedition.objects.filter(
            date_creation__gte=start,
            date_creation__lte=end
        ).aggregate(
            total=Count('id'),
            montant_total=Sum('montant_total'),
            montant_moyen=Avg('montant_total'),
            poids_total=Sum('poids'),
            volume_total=Sum('volume')
        )
        
        # Par statut
        par_statut = self.Expedition.objects.filter(
            date_creation__gte=start,
            date_creation__lte=end
        ).values('statut').annotate(
            nombre=Count('id')
        )
        
        # Tournées
        tournees = self.Tournee.objects.filter(
            date_tournee__gte=start,
            date_tournee__lte=end
        ).aggregate(
            total=Count('id'),
            km_total=Sum('kilometrage'),
            duree_totale=Sum('duree'),
            carburant_total=Sum('consommation_carburant')
        )
        
        # Facturation
        facturation = self.Facture.objects.filter(
            date_facture__gte=start,
            date_facture__lte=end
        ).aggregate(
            nombre_factures=Count('id'),
            ca_ht=Sum('montant_ht'),
            ca_ttc=Sum('montant_ttc')
        )
        
        return {
            'periode': {
                'annee': year,
                'mois': month,
                'debut': start,
                'fin': end
            },
            'expeditions': {
                'total': expeditions['total'] or 0,
                'montant_total': float(expeditions['montant_total'] or 0),
                'montant_moyen': float(expeditions['montant_moyen'] or 0),
                'poids_total': float(expeditions['poids_total'] or 0),
                'volume_total': float(expeditions['volume_total'] or 0),
                'par_statut': list(par_statut)
            },
            'tournees': {
                'total': tournees['total'] or 0,
                'kilometrage_total': float(tournees['km_total'] or 0),
                'duree_totale': float(tournees['duree_totale'] or 0),
                'carburant_total': float(tournees['carburant_total'] or 0)
            },
            'facturation': {
                'nombre_factures': facturation['nombre_factures'] or 0,
                'ca_ht': float(facturation['ca_ht'] or 0),
                'ca_ttc': float(facturation['ca_ttc'] or 0)
            }
        }
    
    # ============== ANALYSES DE RENTABILITÉ ==============
    
    def get_rentabilite_par_service(self, start_date, end_date):
        """Analyse de rentabilité par type de service"""
        data = self.Expedition.objects.filter(
            date_creation__gte=start_date,
            date_creation__lte=end_date
        ).values(
            'type_service__nom'
        ).annotate(
            nombre_expeditions=Count('id'),
            ca_total=Sum('montant_total'),
            ca_moyen=Avg('montant_total'),
            poids_moyen=Avg('poids'),
            volume_moyen=Avg('volume')
        ).order_by('-ca_total')
        
        result = list(data)
        total_ca = sum(item['ca_total'] or 0 for item in result)
        
        for item in result:
            if total_ca > 0:
                item['part_ca'] = round((item['ca_total'] / total_ca) * 100, 2)
            else:
                item['part_ca'] = 0
        
        return result
    
    def get_rentabilite_par_destination(self, start_date, end_date):
        """Analyse de rentabilité par destination"""
        data = self.Expedition.objects.filter(
            date_creation__gte=start_date,
            date_creation__lte=end_date
        ).values(
            'destination__ville',
            'destination__pays'
        ).annotate(
            nombre_expeditions=Count('id'),
            ca_total=Sum('montant_total'),
            ca_moyen=Avg('montant_total')
        ).order_by('-ca_total')
        
        return list(data)
    
    # ============== STATISTIQUES DE PAIEMENT ==============
    
    def get_paiements_stats(self, start_date, end_date):
        """Statistiques sur les paiements"""
        # Paiements reçus
        paiements = self.Paiement.objects.filter(
            date_paiement__gte=start_date,
            date_paiement__lte=end_date
        ).aggregate(
            total_paiements=Count('id'),
            montant_total=Sum('montant_paye'),
            montant_moyen=Avg('montant_paye')
        )
        
        # Par mode de paiement
        par_mode = self.Paiement.objects.filter(
            date_paiement__gte=start_date,
            date_paiement__lte=end_date
        ).values('mode_paiement').annotate(
            nombre=Count('id'),
            montant=Sum('montant_paye')
        ).order_by('-montant')
        
        # Factures en attente
        factures_attente = self.Facture.objects.filter(
            date_facture__gte=start_date,
            date_facture__lte=end_date,
            statut='en attente'
        ).aggregate(
            nombre=Count('id'),
            montant_du=Sum('montant_ttc')
        )
        
        return {
            'paiements_recus': {
                'total': paiements['total_paiements'] or 0,
                'montant_total': float(paiements['montant_total'] or 0),
                'montant_moyen': float(paiements['montant_moyen'] or 0)
            },
            'par_mode': list(par_mode),
            'factures_attente': {
                'nombre': factures_attente['nombre'] or 0,
                'montant_du': float(factures_attente['montant_du'] or 0)
            }
        }
    
    # ============== PRÉVISIONS SIMPLES ==============
    
    def predict_next_month(self, model_type='expeditions'):
        """Prévision simple basée sur la moyenne des 3 derniers mois"""
        today = datetime.now()
        three_months_ago = today - timedelta(days=90)
        
        if model_type == 'expeditions':
            # Moyenne mensuelle des 3 derniers mois
            data = self.Expedition.objects.filter(
                date_creation__gte=three_months_ago,
                date_creation__lte=today
            ).aggregate(
                total=Count('id'),
                montant_total=Sum('montant_total')
            )
            
            avg_per_month = (data['total'] or 0) / 3
            avg_montant = (data['montant_total'] or 0) / 3
            
            return {
                'type': 'expeditions',
                'prevision_nombre': round(avg_per_month),
                'prevision_montant': round(float(avg_montant), 2),
                'periode': 'mois prochain',
                'methode': 'moyenne mobile 3 mois'
            }
        
        elif model_type == 'tournees':
            data = self.Tournee.objects.filter(
                date_tournee__gte=three_months_ago,
                date_tournee__lte=today
            ).aggregate(
                total=Count('id'),
                km_total=Sum('kilometrage')
            )
            
            avg_per_month = (data['total'] or 0) / 3
            avg_km = (data['km_total'] or 0) / 3
            
            return {
                'type': 'tournees',
                'prevision_nombre': round(avg_per_month),
                'prevision_km': round(float(avg_km), 2),
                'periode': 'mois prochain',
                'methode': 'moyenne mobile 3 mois'
            }
    
    # ============== INDICATEURS DE PERFORMANCE (KPI) ==============
    
    def calculate_kpis(self, start_date, end_date):
        """Calcule les principaux KPI"""
        # Délai moyen de livraison
        expeditions_livrees = self.Expedition.objects.filter(
            date_creation__gte=start_date,
            date_creation__lte=end_date,
            statut='livré',
            date_livraison__isnull=False
        )
        
        delais = []
        for exp in expeditions_livrees:
            delai = (exp.date_livraison - exp.date_creation).days
            if delai >= 0:
                delais.append(delai)
        
        delai_moyen = sum(delais) / len(delais) if delais else 0
        
        # Coût moyen par tournée
        cout_moyen_tournee = self.Tournee.objects.filter(
            date_tournee__gte=start_date,
            date_tournee__lte=end_date
        ).aggregate(
            km_total=Sum('kilometrage'),
            carburant_total=Sum('consommation_carburant'),
            count=Count('id')
        )
        
        # Taux de remplissage des véhicules
        total_capacite = 0
        total_utilise = 0
        
        tournees = self.Tournee.objects.filter(
            date_tournee__gte=start_date,
            date_tournee__lte=end_date
        ).select_related('vehicule')
        
        for tournee in tournees:
            if tournee.vehicule:
                total_capacite += tournee.vehicule.capacite
                # Somme des volumes des expéditions de cette tournée
                volume_utilise = tournee.expeditions.aggregate(
                    total=Sum('volume')
                )['total'] or 0
                total_utilise += volume_utilise
        
        taux_remplissage = (total_utilise / total_capacite * 100) if total_capacite > 0 else 0
        
        return {
            'delai_moyen_livraison': round(delai_moyen, 1),
            'cout_moyen_tournee': {
                'kilometrage': round(float(cout_moyen_tournee['km_total'] or 0) / (cout_moyen_tournee['count'] or 1), 2),
                'carburant': round(float(cout_moyen_tournee['carburant_total'] or 0) / (cout_moyen_tournee['count'] or 1), 2)
            },
            'taux_remplissage_vehicules': round(taux_remplissage, 2)
        }