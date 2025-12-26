from django.db import models
from .expedition import Expedition

class TrackingExpedition(models.Model):
    expedition = models.ForeignKey(Expedition, on_delete=models.CASCADE, related_name='historique_tracking')
    date_evenement = models.DateTimeField(auto_now_add=True)
    
    STATUT_TRACKING_CHOICES = [
        ('COLIS_CREE', 'Colis enregistré'),
        ('AFFECTE_TOURNEE', 'Affecté à une tournée'),
        ('EN_CHARGEMENT', 'En cours de chargement (2h avant départ)'),
        ('EN_TRANSIT', 'En transit (Camion en route)'),
        ('LIVRE', 'Livré à destination'),
        ('ECHEC_LIVRAISON', 'Échec de livraison (Incident)'),
        ('RETOUR_DEPOT', 'Retour au dépôt'),
    ]
    
    statut_etape = models.CharField(max_length=30, choices=STATUT_TRACKING_CHOICES, blank=True)
    commentaire = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-date_evenement']