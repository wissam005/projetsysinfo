from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
class Chauffeur(models.Model):

    nom = models.CharField(max_length=50)
    prenom = models.CharField(max_length=50)
    date_naissance = models.DateField(default='2000-01-01')
    telephone = PhoneNumberField(region='DZ')
    email = models.EmailField(blank=True, null=True)
    adresse = models.TextField(blank=True, null=True)
    ville = models.CharField(max_length=100, blank=True, null=True)
    wilaya = models.CharField(max_length=100, blank=True, null=True)
    numero_permis = models.CharField(max_length=50, unique=True)
    date_obtention_permis = models.DateField()
    date_expiration_permis = models.DateField()
    date_embauche = models.DateField()
    salaire = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    STATUT_CHOICES = [
        ('DISPONIBLE', 'Disponible'),
        ('EN_TOURNEE', 'En tournée'),
        ('CONGE', 'En congé'),
        ('MALADIE', 'Maladie'),
        ('AUTRE', 'Autre raison'),
    ]
    statut_disponibilite = models.CharField(max_length=20, choices=STATUT_CHOICES, default='DISPONIBLE')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    remarques = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.prenom} {self.nom} - {self.get_id_chauffeur()}"

    def get_id_chauffeur(self):
        return f"CH-{self.id:03d}"
