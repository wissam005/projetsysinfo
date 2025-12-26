from django.db import models, transaction
from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from .facture import Facture
from ..service import generer_numero_paiement, calculer_montants_facture

class Paiement(models.Model):
    facture = models.ForeignKey(Facture, on_delete=models.PROTECT, related_name='paiements')
    numero_paiement = models.CharField(max_length=50, unique=True, editable=False)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    
    METHODE_CHOICES = [
        ('ESPECES', 'Espèces'),
        ('CHEQUE', 'Chèque'),
        ('VIREMENT', 'Virement bancaire'),
        ('VIREMENT', 'Virement postale'),
        ('CARTE', 'Carte bancaire'),
        ('CARTE', 'Carte edahabia'),
        ('MOBILE', 'Paiement mobile'),
        ('AUTRE', 'Autre'),
    ]
    methode_paiement = models.CharField(max_length=20, choices=METHODE_CHOICES, default='ESPECES')
    reference_paiement = models.CharField(max_length=100, blank=True, null=True)
    date_paiement = models.DateTimeField(default=timezone.now)
    date_enregistrement = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    STATUT_CHOICES = [
        ('VALIDE', 'Validé'),
        ('EN_ATTENTE', 'En attente de validation'),
        ('ANNULE', 'Annulé'),
    ]
    statut = models.CharField(max_length=15, choices=STATUT_CHOICES, default='VALIDE')
    agent = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='paiements_enregistres')
    remarques = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-date_paiement']
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"

    def __str__(self):
        return f"{self.numero_paiement} - {self.montant} DA - {self.facture.numero_facture}"

    def clean(self):
        if self.montant <= 0:
            raise ValidationError("Le montant doit être supérieur à 0")
        if self.facture and self.montant > self.facture.montant_restant:
            raise ValidationError(f"Le montant du paiement ({self.montant} DA) dépasse le reste à payer ({self.facture.montant_restant} DA)")

    def save(self, *args, **kwargs):
        from django.db import transaction

        if not self.numero_paiement:
            self.numero_paiement = generer_numero_paiement()

        self.clean()
        super().save(*args, **kwargs)

        with transaction.atomic():
            self.mettre_a_jour_facture()
            self.mettre_a_jour_solde_client()

    def mettre_a_jour_facture(self):
        from ..service import calculer_montants_facture
        calculer_montants_facture(self.facture)
        self.facture.save(update_fields=['montant_paye', 'montant_restant', 'statut_paiement'])

    def mettre_a_jour_solde_client(self):
      client = self.facture.client
      reste = self.facture.montant_restant  # reste à payer après le paiement

      if self.statut == 'VALIDE':
        if reste > 0:
            # Paiement partiel : solde = montant restant à payer si supérieur au solde existant
            client.solde = max(client.solde, reste)
        else:
            # Paiement total : on réduit le solde existant si crédit existant
            client.solde = max(client.solde - self.facture.montant, 0)

        client.save(update_fields=['solde'])



    def annuler(self):
        from django.db import transaction
        if self.statut == 'ANNULE':
            return
        with transaction.atomic():
            self.statut = 'ANNULE'
            self.save(update_fields=['statut'])
            self.mettre_a_jour_facture()
            client = self.facture.client
            client.solde += self.montant
            client.save(update_fields=['solde'])

    def delete(self, *args, **kwargs):
        self.annuler()
        super().delete(*args, **kwargs)
