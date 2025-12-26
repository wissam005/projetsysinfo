from decimal import Decimal
from datetime import date
from django.db.models import Sum

# Facture

def generer_numero_facture() -> str:
    """Génère un numéro de facture unique"""
    from .models import Facture  # import local pour éviter circular import
    aujourd_hui = date.today().strftime('%Y%m%d')
    count = Facture.objects.filter(numero_facture__startswith=f'FACT-{aujourd_hui}').count() + 1
    return f'FACT-{aujourd_hui}-{count:04d}'

def calculer_montants_facture(facture):
    """Calcule HT, TVA, TTC, payé, restant et statut"""
    from .models import Paiement  # import local pour éviter circular import

    # 1. Montant HT
    expeditions = facture.expeditions.all()
    facture.montant_ht = expeditions.aggregate(total=Sum('montant_total'))['total'] or Decimal('0.00')

    # 2. TVA
    facture.montant_tva = facture.montant_ht * (facture.taux_tva / Decimal('100'))

    # 3. TTC
    facture.montant_ttc = facture.montant_ht + facture.montant_tva

    # 4. Montant payé
    paiements = facture.paiements.filter(statut='VALIDE')
    facture.montant_paye = paiements.aggregate(total=Sum('montant'))['total'] or Decimal('0.00')

    # 5. Reste à payer
    facture.montant_restant = facture.montant_ttc - facture.montant_paye

    # 6. Statut
    if facture.montant_restant <= 0:
        facture.statut_paiement = 'PAYEE'
    elif facture.montant_paye > 0:
        facture.statut_paiement = 'PARTIELLEMENT_PAYEE'
    else:
        facture.statut_paiement = 'IMPAYEE'

    return facture

# Paiement

def generer_numero_paiement() -> str:
    """Génère un numéro de paiement unique"""
    from .models import Paiement  # import local
    aujourd_hui = date.today().strftime('%Y%m%d')
    count = Paiement.objects.filter(numero_paiement__startswith=f'PAIE-{aujourd_hui}').count() + 1
    return f'PAIE-{aujourd_hui}-{count:04d}'
