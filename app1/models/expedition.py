from django.db import models
from django.utils import timezone
from django.db.models import Sum
from phonenumber_field.modelfields import PhoneNumberField
from datetime import timedelta
import math

from .client import Client
from .type_service import TypeService
from .destination import Destination
from .tarification import Tarification
from .chauffeur import Chauffeur
from .vehicule import Vehicule


class Expedition(models.Model):
    PAYS_CHOICES = [
        ('DZ', 'Algérie (+213)'),
        ('MA', 'Maroc (+212)'),
        ('TN', 'Tunisie (+216)'),
        ('FR', 'France (+33)'),
        ('ES', 'Espagne (+34)'),
        ('EG', 'Égypte (+20)'),
    ]
    
    STATUT_CHOICES = [
        ('EN_ATTENTE', 'En attente'),
        ('EN_TRANSIT', 'En transit'),
        ('LIVRE', 'Livré'),
        ('ECHEC', 'Échec'),
    ]
    
    # --- RELATIONS ---
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    type_service = models.ForeignKey(TypeService, on_delete=models.PROTECT)
    destination = models.ForeignKey(Destination, on_delete=models.PROTECT)
    tournee = models.ForeignKey(
        "app1.Tournee", 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='expeditions'
    )
    facture = models.ForeignKey(
        'Facture', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='expeditions',
        help_text="Facture à laquelle cette expédition est rattachée"
    )

    # --- INFOS DESTINATAIRE ---
    nom_destinataire = models.CharField(max_length=100)
    telephone_destinataire = PhoneNumberField(region='DZ', help_text="Ex: +213551234567")
    email = models.EmailField(null=True, blank=True)
    adresse_destinataire = models.TextField(help_text="Adresse complète de livraison")

    # --- CARACTÉRISTIQUES COLIS ---
    poids = models.DecimalField(max_digits=8, decimal_places=2, help_text="kg")
    volume = models.DecimalField(max_digits=8, decimal_places=2, help_text="m³")
    description = models.TextField(blank=True, null=True)

    # --- FINANCES & STATUTS ---
    montant_total = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        editable=False
    )
    statut = models.CharField(
        max_length=20, 
        choices=STATUT_CHOICES, 
        default='EN_ATTENTE'
    )

    # --- DATES ---
    date_creation = models.DateTimeField(auto_now_add=True)
    date_livraison_prevue = models.DateField(blank=True, null=True, editable=False)
    date_livraison_reelle = models.DateField(blank=True, null=True, editable=False)
    remarques = models.TextField(blank=True, null=True)

    def get_numero_expedition(self):
        return f"EXP-{self.id:06d}" 
    
    def save(self, *args, **kwargs):
        from datetime import date
        from .tracking import TrackingExpedition
        from tournee import Tournee 

        # Garder en mémoire si c'est une création
        is_new = self.pk is None

        # 1. CALCULS FINANCIERS ET DÉLAIS
        montant, delai = Tarification.obtenir_calculs(
            self.destination, self.type_service, self.poids, self.volume
        )
        self.montant_total = montant

        # 2. LOGIQUE D'AFFECTATION INTELLIGENTE (Si pas déjà affecté)
        if not self.tournee:
            # --- CAS A : SERVICE EXPRESS ---
            if self.type_service.type_service == 'EXPRESS':
                chauffeur_dispo = Chauffeur.objects.filter(
                    statut_disponibilite='DISPONIBLE'
                ).first()
                vehicule_dispo = Vehicule.objects.filter(statut='DISPONIBLE').first()
                
                if chauffeur_dispo and vehicule_dispo:
                    nouvelle_tournee = Tournee.objects.create(
                        chauffeur=chauffeur_dispo,
                        vehicule=vehicule_dispo,
                        date_depart=timezone.now(),
                        zone_cible=self.destination.zone_logistique,
                        statut='PREVUE'
                    )
                    self.tournee = nouvelle_tournee
                    self.statut = 'EN_ATTENTE'

            # --- CAS B : SERVICE STANDARD ---
            else:
                tournees_candidates = Tournee.objects.filter(
                    zone_cible=self.destination.zone_logistique,
                    statut='PREVUE',
                    date_depart__gte=timezone.now()
                ).order_by('date_depart')
                
                for tournee in tournees_candidates:
                    poids_actuel = tournee.expeditions.aggregate(
                        total=Sum('poids')
                    )['total'] or 0
                    volume_actuel = tournee.expeditions.aggregate(
                        total=Sum('volume')
                    )['total'] or 0
                    
                    if (float(poids_actuel) + float(self.poids) <= float(tournee.vehicule.capacite_poids) and 
                        float(volume_actuel) + float(self.volume) <= float(tournee.vehicule.capacite_volume)):
                        self.tournee = tournee
                        break
        
        # --- MISE À JOUR DU STATUT SELON LA TOURNÉE ---
        if self.tournee:
            self.statut = 'EN_TRANSIT' if self.tournee.statut == 'EN_COURS' else 'EN_ATTENTE'

        # 3. CALCUL DE LA DATE DE LIVRAISON PRÉVUE
        date_base = self.tournee.date_depart.date() if self.tournee else date.today()
        self.date_livraison_prevue = date_base + timedelta(days=math.ceil(float(delai)))
        
        # 4. SAUVEGARDE PHYSIQUE
        super().save(*args, **kwargs)

        # 5. GÉNÉRATION AUTOMATIQUE DU TRACKING
        if is_new:
            TrackingExpedition.objects.create(
                expedition=self, 
                statut_etape='COLIS_CREE',
                commentaire="Colis enregistré dans le système."
            )

        if self.tournee and not self.historique_tracking.filter(
            statut_etape='AFFECTE_TOURNEE'
        ).exists():
            TrackingExpedition.objects.create(
                expedition=self, 
                statut_etape='AFFECTE_TOURNEE',
                commentaire=f"Affecté à la Tournée {self.tournee.id}"
            )

    facture = models.ForeignKey(
        'Facture', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='expeditions',
        help_text="Facture à laquelle cette expédition est rattachée"
    )
