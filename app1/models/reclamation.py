from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from .client import Client
from .expedition import Expedition
from .facture import Facture
from .incident import Incident

class Reclamation(models.Model):
    """
    Modèle pour centraliser et traiter les réclamations clients
    """
    
    NATURE_CHOICES = [
        ('RETARD', 'Retard de livraison'),
        ('PERTE', 'Perte de colis'),
        ('ENDOMMAGEMENT', 'Colis endommagé'),
        ('ERREUR_FACTURATION', 'Erreur de facturation'),
        ('MAUVAIS_SERVICE', 'Mauvaise qualité de service'),
        ('LITIGE_MONTANT', 'Litige sur le montant'),
        ('NON_LIVRAISON', 'Non-livraison'),
        ('COMPORTEMENT', 'Comportement du personnel'),
        ('AUTRE', 'Autre'),
    ]
    
    STATUT_CHOICES = [
        ('NOUVELLE', 'Nouvelle'),
        ('EN_COURS', 'En cours de traitement'),
        ('EN_ATTENTE_CLIENT', 'En attente de réponse client'),
        ('RESOLUE', 'Résolue'),
        ('REJETEE', 'Rejetée'),
        ('ANNULEE', 'Annulée'),
    ]
    
    PRIORITE_CHOICES = [
        ('BASSE', 'Basse'),
        ('NORMALE', 'Normale'),
        ('HAUTE', 'Haute'),
        ('URGENTE', 'Urgente'),
    ]
    
    # Numéro unique de réclamation
    numero_reclamation = models.CharField(max_length=50, unique=True, editable=False , default='REC-0000-0000')
    
    # Relations
    client = models.ForeignKey(
        Client, 
        on_delete=models.PROTECT,
        related_name='reclamations'
    )
    
    expedition = models.ForeignKey(
        Expedition, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reclamations',
        help_text="Expédition concernée"
    )
    
    facture = models.ForeignKey(
        Facture, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reclamations',
        help_text="Facture concernée"
    )
    
    incident = models.ForeignKey(
        Incident,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reclamations',
        help_text="Incident lié (si applicable)"
    )
    
    # Informations de la réclamation
    nature = models.CharField(max_length=25, choices=NATURE_CHOICES, default='AUTRE')
    objet = models.CharField(max_length=200, help_text="Objet de la réclamation")
    description = models.TextField(help_text="Description détaillée de la réclamation")
    
    # Dates
    date_reclamation = models.DateTimeField(default=timezone.now, help_text="Date de la réclamation")
    date_modification = models.DateTimeField(auto_now=True)
    date_resolution = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date de résolution"
    )
    
    # Statut et priorité
    statut = models.CharField(
        max_length=20, 
        choices=STATUT_CHOICES, 
        default='NOUVELLE'
    )
    
    priorite = models.CharField(
        max_length=10,
        choices=PRIORITE_CHOICES,
        default='NORMALE'
    )
    
    # Gestion et traitement
    agent_responsable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reclamations_assignees',
        help_text="Agent chargé de traiter la réclamation"
    )
    
    reponse = models.TextField(
        blank=True,
        null=True,
        help_text="Réponse apportée au client"
    )
    
    actions_correctives = models.TextField(
        blank=True,
        null=True,
        help_text="Actions correctives mises en place"
    )
    
    # Compensation
    compensation_accordee = models.BooleanField(
        default=False,
        help_text="Compensation accordée au client"
    )
    
    montant_compensation = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Montant de la compensation en DA"
    )
    
    type_compensation = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Type de compensation (remboursement, avoir, geste commercial...)"
    )
    
    # Satisfaction client
    CLIENT_SATISFAIT_CHOICES = [
        ('OUI', 'Oui'),
        ('NON', 'Non'),
        ('SANS_REPONSE', 'Sans réponse'),
    ]
    
    client_satisfait = models.CharField(
        max_length=15,
        choices=CLIENT_SATISFAIT_CHOICES,
        null=True,
        blank=True,
        help_text="Le client est-il satisfait de la résolution?"
    )
    
    # Documents
    document = models.FileField(
        upload_to='reclamations/%Y/%m/',
        null=True,
        blank=True,
        help_text="Document joint par le client"
    )
    
    remarques = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-date_reclamation']
        verbose_name = "Réclamation"
        verbose_name_plural = "Réclamations"
    
    def __str__(self):
        return f"{self.numero_reclamation} - {self.client} - {self.objet}"
    
    def generer_numero_reclamation(self):
        """Génère un numéro de réclamation unique au format REC-YYYYMMDD-XXXX"""
        from datetime import date
        aujourd_hui = date.today().strftime('%Y%m%d')
        
        count = Reclamation.objects.filter(
            numero_reclamation__startswith=f'REC-{aujourd_hui}'
        ).count() + 1
        
        return f'REC-{aujourd_hui}-{count:04d}'
    
    def save(self, *args, **kwargs):
        # Générer le numéro de réclamation
        if not self.numero_reclamation:
            self.numero_reclamation = self.generer_numero_reclamation()
        
        # Si la réclamation est résolue, mettre la date
        if self.statut in ['RESOLUE', 'REJETEE'] and not self.date_resolution:
            self.date_resolution = timezone.now()
        
        # Déterminer la priorité automatiquement si non définie
        if not self.pk and self.priorite == 'NORMALE':
            if self.nature in ['PERTE', 'NON_LIVRAISON']:
                self.priorite = 'HAUTE'
            elif self.montant_compensation and self.montant_compensation > 5000:
                self.priorite = 'HAUTE'
        
        super().save(*args, **kwargs)
    
    def delai_traitement(self):
        """Calcule le délai de traitement en jours"""
        if self.date_resolution:
            return (self.date_resolution - self.date_reclamation).days
        else:
            return (timezone.now() - self.date_reclamation).days
    
    def est_en_retard(self):
        """Vérifie si la réclamation dépasse le délai de traitement (7 jours)"""
        if self.statut in ['RESOLUE', 'REJETEE', 'ANNULEE']:
            return False
        return self.delai_traitement() > 7