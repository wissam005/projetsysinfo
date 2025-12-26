from django.db import models
from decimal import Decimal

class Vehicule(models.Model):

    numero_immatriculation = models.CharField(max_length=50, unique=True)
    marque = models.CharField(max_length=100)
    modele = models.CharField(max_length=100)
    annee = models.IntegerField()

    TYPE_CHOICES = [
        ('CAMIONNETTE', 'Camionnette'),
        ('CAMION', 'Camion'),
        ('FOURGON', 'Fourgon'),
        ('MOTO', 'Moto'),
    ]
    type_vehicule = models.CharField(max_length=20, choices=TYPE_CHOICES)
    capacite_poids = models.DecimalField(max_digits=8, decimal_places=2, help_text="Capacité en kg")
    capacite_volume = models.DecimalField(max_digits=8, decimal_places=2, help_text="Volume en m³")
    consommation_moyenne = models.DecimalField(max_digits=5, decimal_places=2, help_text="Consommation en L/100km")

    ETAT_CHOICES = [
        ('EXCELLENT', 'Excellent'),
        ('BON', 'Bon'),
        ('MOYEN', 'Moyen'),
        ('MAUVAIS', 'Mauvais'),
    ]
    etat = models.CharField(max_length=20, choices=ETAT_CHOICES, default='BON')

    STATUT_CHOICES = [
        ('DISPONIBLE', 'Disponible'),
        ('EN_TOURNEE', 'En tournée'),
        ('EN_MAINTENANCE', 'En maintenance'),
        ('HORS_SERVICE', 'Hors service'),
    ]
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='DISPONIBLE')
    date_derniere_revision = models.DateField(blank=True, null=True)
    date_prochaine_revision = models.DateField(blank=True, null=True)
    ##notif chaque 3 mois de rev pour le vehicule et aussi modif le klm
    kilometrage = models.PositiveIntegerField(default=0, help_text="Compteur kilométrique total")
    date_acquisition = models.DateField()
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    remarques = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.marque} {self.modele} - {self.numero_immatriculation}"
