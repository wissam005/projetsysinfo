from decimal import Decimal
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.db.models import Sum

class Client(models.Model):
    

    nom = models.CharField(max_length=20)
    prenom = models.CharField(max_length=20)
    date_naissance = models.DateField(default='2000-01-01')
    telephone = PhoneNumberField(region='DZ', unique=True)
    email = models.EmailField(blank=True, null=True)
    adresse = models.TextField(blank=True, null=True)
    ville = models.CharField(max_length=100, blank=True, null=True)
    wilaya = models.CharField(max_length=100, blank=True, null=True)
    solde = models.DecimalField(max_digits=12, decimal_places=2, default=0.00,)
    date_inscription = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    remarques = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"CL-{self.id:03d} {self.prenom} {self.nom}"


    def calculer_solde_total(self):
        """Calcule le solde total du client (factures impayées)"""
        from django.db.models import Sum
        factures_impayees = self.factures.exclude(
            statut_paiement='PAYEE'
        )
        
        solde_factures = factures_impayees.aggregate(
            total=Sum('montant_restant')
        )['total'] or Decimal('0.00')
        
        return solde_factures
    
    def mettre_a_jour_solde(self):
        """Met à jour le solde du client"""
        self.solde = self.calculer_solde_total()
        self.save(update_fields=['solde'])
