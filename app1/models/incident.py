from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from .expedition import Expedition
from .tournee import Tournee

class Incident(models.Model):
    """
    Modèle pour enregistrer et suivre les incidents lors des expéditions/tournées
    """
    
    TYPE_CHOICES = [
        ('RETARD', 'Retard de livraison'),
        ('PERTE', 'Perte de colis'),
        ('ENDOMMAGEMENT', 'Endommagement'),
        ('TECHNIQUE', 'Problème technique (véhicule)'),
        ('ACCIDENT', 'Accident de circulation'),
        ('METEO', 'Conditions météorologiques'),
        ('ADRESSE', 'Adresse incorrecte/introuvable'),
        ('REFUS', 'Refus de réception'),
        ('AUTRE', 'Autre'),
    ]
    
    GRAVITE_CHOICES = [
        ('FAIBLE', 'Faible'),
        ('MOYENNE', 'Moyenne'),
        ('ELEVEE', 'Élevée'),
        ('CRITIQUE', 'Critique'),
    ]
    
    STATUT_CHOICES = [
        ('OUVERT', 'Ouvert'),
        ('EN_COURS', 'En cours de traitement'),
        ('RESOLU', 'Résolu'),
        ('CLOS', 'Clos'),
    ]
    
    # Numéro unique d'incident
    numero_incident = models.CharField(max_length=50, unique=True, editable=False)
    
    # Relations
    expedition = models.ForeignKey(
        Expedition, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='incidents',
        help_text="Expédition concernée (si applicable)"
    )
    tournee = models.ForeignKey(
        Tournee, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='incidents',
        help_text="Tournée concernée (si applicable)"
    )
    
    # Informations de l'incident
    type_incident = models.CharField(max_length=20, choices=TYPE_CHOICES)
    gravite = models.CharField(
        max_length=10, 
        choices=GRAVITE_CHOICES,
        default='MOYENNE'
    )
    
    titre = models.CharField(max_length=200, help_text="Titre court de l'incident")
    description = models.TextField(help_text="Description détaillée de l'incident")
    
    # Localisation
    lieu_incident = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        help_text="Lieu où l'incident s'est produit"
    )
    
    # Dates et suivi
    date_incident = models.DateTimeField(
        default=timezone.now,
        help_text="Date et heure de l'incident"
    )
    date_creation = models.DateTimeField(default=timezone.now, help_text="Date de création de l'incident")
    date_resolution = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Date de résolution de l'incident"
    )
    
    statut = models.CharField(
        max_length=15, 
        choices=STATUT_CHOICES, 
        default='OUVERT'
    )
    
    # Responsabilité et traitement
    agent_rapporteur = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incidents_rapportes',
        help_text="Agent qui a rapporté l'incident"
    )
    
    agent_responsable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incidents_assignes',
        help_text="Agent chargé de traiter l'incident"
    )
    
    # Actions et résolution
    actions_entreprises = models.TextField(
        blank=True,
        null=True,
        help_text="Actions entreprises pour résoudre l'incident"
    )
    
    solution = models.TextField(
        blank=True,
        null=True,
        help_text="Solution apportée"
    )
    
    # Coûts et impacts
    cout_estime = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Coût estimé de l'incident en DA"
    )
    
    # Documents et preuves
    document = models.FileField(
        upload_to='incidents/%Y/%m/',
        null=True,
        blank=True,
        help_text="Document ou photo de l'incident"
    )
    
    # Alertes
    alerte_client_envoyee = models.BooleanField(
        default=False,
        help_text="Alerte envoyée au client"
    )
    
    alerte_direction_envoyee = models.BooleanField(
        default=False,
        help_text="Alerte envoyée à la direction"
    )
    
    remarques = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-date_incident']
        verbose_name = "Incident"
        verbose_name_plural = "Incidents"
    
    def __str__(self):
        return f"{self.numero_incident} - {self.get_type_incident_display()}"
    
    def generer_numero_incident(self):
        """Génère un numéro d'incident unique au format INC-YYYYMMDD-XXXX"""
        from datetime import date
        aujourd_hui = date.today().strftime('%Y%m%d')
        
        count = Incident.objects.filter(
            numero_incident__startswith=f'INC-{aujourd_hui}'
        ).count() + 1
        
        return f'INC-{aujourd_hui}-{count:04d}'
    
    def save(self, *args, **kwargs):
        # Générer le numéro d'incident
        if not self.numero_incident:
            self.numero_incident = self.generer_numero_incident()
        
        # Si l'incident est résolu, mettre la date de résolution
        if self.statut in ['RESOLU', 'CLOS'] and not self.date_resolution:
            self.date_resolution = timezone.now()
        
        # Mettre à jour le statut de l'expédition si nécessaire
        if self.expedition:
            if self.type_incident in ['PERTE', 'ENDOMMAGEMENT', 'REFUS']:
                self.expedition.statut = 'ECHEC'
                self.expedition.save(update_fields=['statut'])
        
        super().save(*args, **kwargs)
        
        # Générer des alertes si nécessaire
        self.generer_alertes()
    
    def generer_alertes(self):
        """Génère des alertes selon la gravité de l'incident"""
        if self.gravite in ['ELEVEE', 'CRITIQUE'] and not self.alerte_direction_envoyee:
            # TODO: Envoyer email/SMS à la direction
            self.alerte_direction_envoyee = True
            self.save(update_fields=['alerte_direction_envoyee'])
        
        if self.expedition and not self.alerte_client_envoyee:
            # TODO: Envoyer notification au client
            self.alerte_client_envoyee = True
            self.save(update_fields=['alerte_client_envoyee'])
    
    def est_resolu(self):
        """Vérifie si l'incident est résolu"""
        return self.statut in ['RESOLU', 'CLOS']
    
    def duree_traitement(self):
        """Calcule la durée de traitement de l'incident"""
        if self.date_resolution:
            return (self.date_resolution - self.date_creation).days
        return None