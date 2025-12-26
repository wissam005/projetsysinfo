from django.db import models
from decimal import Decimal

class Destination(models.Model):

    ville = models.CharField(max_length=100)
    wilaya = models.CharField(max_length=100, blank=True, null=True)
    pays = models.CharField(max_length=100, default='Algérie')

    ZONE_CHOICES = [
        ('LOCALE', 'Locale (même wilaya)'),
        ('NATIONALE', 'Nationale'),
        ('INTERNATIONALE', 'Internationale'),
    ]
    zone_geographique = models.CharField(max_length=20, choices=ZONE_CHOICES)
    ZONE_LOGISTIQUE_CHOICES = [
        ('CENTRE', 'Centre (Alger, Blida...)'),
        ('EST', 'Est (Constantine, Annaba, Sétif...)'),
        ('OUEST', 'Ouest (Oran, Tlemcen, Sidi Bel Abbès...)'),
        ('SUD', 'Sud (Tamanrasset, Adrar, Bechar...)'),
    ]
    zone_logistique = models.CharField(max_length=10, choices=ZONE_LOGISTIQUE_CHOICES, default='CENTRE')
    distance_estimee = models.IntegerField(help_text="Distance en km depuis le dépôt principal")
    tarif_base = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Tarif de base en DA")
    delai_livraison_estime = models.IntegerField(default=1, help_text="Délai estimé en jours")
    code_postal = models.CharField(max_length=10, blank=True, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    remarques = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.ville} - {self.wilaya} - {self.pays}"
