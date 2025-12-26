from django.db import models, transaction
from decimal import Decimal
from django.utils import timezone
from .client import Client
from ..service import calculer_montants_facture, generer_numero_facture, generer_numero_paiement

class Facture(models.Model):
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='factures')
    numero_facture = models.CharField(max_length=50, unique=True, editable=False)
    date_emission = models.DateTimeField(auto_now_add=True)
    date_echeance = models.DateField(help_text="Date limite de paiement")
    date_modification = models.DateTimeField(auto_now=True)
    montant_ht = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    taux_tva = models.DecimalField(max_digits=5, decimal_places=2, default=19.00)
    montant_tva = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    montant_ttc = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    montant_paye = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    montant_restant = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)

    STATUT_CHOICES = [
        ('IMPAYEE', 'Impayée'),
        ('PARTIELLEMENT_PAYEE', 'Partiellement payée'),
        ('PAYEE', 'Payée intégralement'),
        ('ANNULEE', 'Annulée'),
    ]
    statut_paiement = models.CharField(max_length=25, choices=STATUT_CHOICES, default='IMPAYEE')
    remarques = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-date_emission']
        verbose_name = "Facture"
        verbose_name_plural = "Factures"

    def __str__(self):
        return f"{self.numero_facture} - {self.client} - {self.montant_ttc} DA"

    def save(self, *args, **kwargs):
        from ..service import calculer_montants_facture
        # Numéro de facture si nouveau
        if not self.numero_facture:
            self.numero_facture = generer_numero_facture()

        # Date d’échéance si non définie
        if not self.date_echeance:
            from datetime import timedelta
            self.date_echeance = timezone.now().date() + timedelta(days=30)

        super().save(*args, **kwargs)  # sauvegarde initiale
        calculer_montants_facture(self)
        super().save(update_fields=[
            'montant_ht', 'montant_tva', 'montant_ttc',
            'montant_paye', 'montant_restant', 'statut_paiement'
        ])

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            for paiement in self.paiements.all():
                paiement.annuler()
            self.expeditions.all().update(facture=None)
            super().delete(*args, **kwargs)

    def est_echue(self):
        from datetime import date
        return date.today() > self.date_echeance and self.statut_paiement != 'PAYEE'
