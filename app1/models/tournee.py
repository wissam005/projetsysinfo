from django.db import models
from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError
from .chauffeur import Chauffeur
from .vehicule import Vehicule
from .destination import Destination
from .tracking import TrackingExpedition

class Tournee(models.Model):
    
    chauffeur = models.ForeignKey(Chauffeur, on_delete=models.PROTECT) ##fonction pour savoir si le chauffeur est disponible 
    vehicule = models.ForeignKey(Vehicule, on_delete=models.PROTECT) ##la meme chose 
    date_depart = models.DateTimeField()
    date_retour_prevue = models.DateTimeField(blank=True, null=True)
    date_retour_reelle = models.DateTimeField(blank=True, null=True)
    zone_cible = models.CharField(
        max_length=10, 
        choices=Destination.ZONE_LOGISTIQUE_CHOICES
    )
    kilometrage_depart = models.PositiveIntegerField(blank=True,null=True,editable=False, help_text="Auto-rempli depuis le véhicule au départ")
    kilometrage_arrivee = models.PositiveIntegerField(blank=True, null=True, help_text="À saisir au retour")
    kilometrage_parcouru = models.PositiveIntegerField(blank=True, null=True, editable=False)
    consommation_carburant = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True, help_text="En litres"
    )
    
    statut = models.CharField(
        max_length=20, 
        choices=[('PREVUE', 'Prévue'), ('EN_COURS', 'En cours'), ('TERMINEE', 'Terminée')],
        default='PREVUE'
    )

    remarques = models.TextField(blank=True, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        date_f = self.date_depart.strftime('%d/%m/%Y %H:%M')
        return f"Tournée {self.id} | {date_f} | {self.zone_cible} - {self.statut}"

    def save(self, *args, **kwargs):
        from decimal import Decimal
        from django.utils import timezone
        from .tracking import TrackingExpedition
        from django.core.exceptions import ValidationError


        ##modif 1 
        if not self.pk:
         if self.chauffeur.statut_disponibilite != 'DISPONIBLE':
            raise ValidationError(
                f"Chauffeur {self.chauffeur} non disponible"
            )
         if self.vehicule.statut != 'DISPONIBLE':
            raise ValidationError(
                f"Véhicule {self.vehicule.numero_immatriculation} non disponible"
            )

        # 0. Détecter le changement de statut pour le tracking
        old_status = None
        if self.pk:
            old_status = Tournee.objects.get(pk=self.pk).statut

        # 1. AUTOMATISATION : Kilométrage et Consommation
        if not self.pk and not self.kilometrage_depart:
            self.kilometrage_depart = self.vehicule.kilometrage

        if self.kilometrage_arrivee and self.kilometrage_depart:
            distance = self.kilometrage_arrivee - self.kilometrage_depart
            if distance < 0:
               raise ValidationError("Le kilométrage d'arrivée est invalide")
            self.kilometrage_parcouru = distance
            # Calcul Decimal pour éviter les erreurs de type avec float
            self.consommation_carburant = (Decimal(distance) / Decimal('100')) * self.vehicule.consommation_moyenne

        # 2. LOGIQUE DE FLUX (Statuts Véhicule et Chauffeur)
        if self.statut in ['PREVUE', 'EN_COURS']:
            self.vehicule.statut = 'EN_TOURNEE'
            self.chauffeur.statut_disponibilite = 'EN_TOURNEE'
        elif self.statut == 'TERMINEE':
            self.vehicule.statut = 'DISPONIBLE'
            self.chauffeur.statut_disponibilite = 'DISPONIBLE'
            if self.kilometrage_arrivee:
                self.vehicule.kilometrage = self.kilometrage_arrivee

        # 3. SAUVEGARDE DES OBJETS LIÉS ET DE LA TOURNÉE
        self.vehicule.save()
        self.chauffeur.save()
        super().save(*args, **kwargs)

        # 4. LOGIQUE AUTOMATIQUE DE TRACKING (BACKEND)
        
        # A. Passage en TRANSIT (Quand la tournée démarre)
        if old_status == 'PREVUE' and self.statut == 'EN_COURS':
            for exp in self.expeditions.all():
                exp.statut = 'EN_TRANSIT'
                exp.save() # Met à jour le statut du colis
                TrackingExpedition.objects.create(
                    expedition=exp, 
                    statut_etape='EN_TRANSIT',
                    commentaire=f"Camion {self.vehicule.numero_immatriculation} en route."
                )

        # B. Clôture de mission (LIVRAISON ou ECHEC/RETOUR)
        elif old_status == 'EN_COURS' and self.statut == 'TERMINEE':
            for exp in self.expeditions.all():
                if exp.statut == 'ECHEC':
                    # On crée l'étape d'échec puis celle du retour physique au dépôt
                    TrackingExpedition.objects.create(
                        expedition=exp, 
                        statut_etape='ECHEC_LIVRAISON', 
                        commentaire="Incident lors de la livraison."
                    )
                    TrackingExpedition.objects.create(
                        expedition=exp, 
                        statut_etape='RETOUR_DEPOT', 
                        commentaire="Colis retourné au dépôt par le chauffeur."
                    )
                else:
                    # Livraison réussie par défaut si pas d'échec marqué
                    exp.statut = 'LIVRE'
                    exp.date_livraison_reelle = timezone.now().date()
                    exp.save()
                    TrackingExpedition.objects.create(
                        expedition=exp, 
                        statut_etape='LIVRE',
                        commentaire="Livraison confirmée à la fermeture de la tournée."
                    )

    def verifier_chargement(self):
        """Déclenche l'étape EN_CHARGEMENT 2h avant le départ"""
        from datetime import timedelta
        from django.utils import timezone
        
        temps_restant = self.date_depart - timezone.now()
        if self.statut == 'PREVUE' and timedelta(hours=0) < temps_restant <= timedelta(hours=2):
            for exp in self.expeditions.all():
                if not exp.historique_tracking.filter(statut_etape='EN_CHARGEMENT').exists():
                    TrackingExpedition.objects.create(
                        expedition=exp, 
                        statut_etape='EN_CHARGEMENT',
                        commentaire="Colis chargé dans le véhicule."
                    )

    def verifier_et_demarrer(self):
        """Vérifie les ressources et démarre la tournée"""
        from django.utils import timezone
        
        est_heure_depart = timezone.now() >= self.date_depart
        chauffeur_pret = self.chauffeur.statut_disponibilite in ['DISPONIBLE', 'EN_TOURNEE']
        vehicule_pret = self.vehicule.statut in ['DISPONIBLE', 'EN_TOURNEE']

        if self.statut == 'PREVUE' and est_heure_depart:
            if chauffeur_pret and vehicule_pret:
                self.statut = 'EN_COURS'
                self.save() # Le save() ci-dessus déclenchera le tracking EN_TRANSIT
                return True, "Tournée démarrée."
            else:
                return False, "Ressources indisponibles (Chauffeur/Véhicule)."
        return False, "Conditions de départ non remplies."
