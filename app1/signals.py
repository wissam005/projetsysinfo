from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models.signals import post_save
from .models import Destination, TypeService, Tarification


@receiver(post_save, sender=Destination)
def creer_tarifications_automatiquement(sender, instance, created, **kwargs):
    """
    Dès qu'une nouvelle Destination est créée,
    on crée automatiquement ses tarifications
    """
    
    # Seulement si c'est une NOUVELLE destination (pas une modification)
    if created:
        
        if instance.zone_geographique == 'INTERNATIONALE':
            # Destination internationale → INTERNATIONAL uniquement
            international = TypeService.objects.get(type_service='INTERNATIONAL')
            Tarification.objects.get_or_create(
                destination=instance,
                type_service=international,
                defaults={
                    'tarif_poids': 25.00,
                    'tarif_volume': 50.00
                }
            )
        
        else:
            # Destination nationale → STANDARD et EXPRESS
            standard = TypeService.objects.get(type_service='STANDARD')
            express = TypeService.objects.get(type_service='EXPRESS')
            
            Tarification.objects.get_or_create(
                destination=instance,
                type_service=standard,
                defaults={
                    'tarif_poids': 10.00,
                    'tarif_volume': 20.00
                }
            )
            
            Tarification.objects.get_or_create(
                destination=instance,
                type_service=express,
                defaults={
                    'tarif_poids': 10.00,
                    'tarif_volume': 20.00
                }
            )

@receiver(post_save, sender='app1.Expedition')
def expedition_saved(sender, instance, created, **kwargs):
    if instance.facture:
        from .service import calculer_montants_facture
        calculer_montants_facture(instance.facture)
        instance.facture.save(update_fields=[
            'montant_ht', 'montant_tva', 'montant_ttc',
            'montant_restant', 'statut_paiement'
        ])

@receiver(post_delete, sender='app1.Expedition')
def expedition_deleted(sender, instance, **kwargs):
    if instance.facture:
        from .service import calculer_montants_facture
        calculer_montants_facture(instance.facture)
        instance.facture.save(update_fields=[
            'montant_ht', 'montant_tva', 'montant_ttc',
            'montant_restant', 'statut_paiement'
        ])

@receiver(post_save, sender='app1.Paiement')
def paiement_saved(sender, instance, created, **kwargs):
    if instance.statut == 'VALIDE':
        client = instance.facture.client
        client.mettre_a_jour_solde()

@receiver(post_delete, sender='app1.Paiement')
def paiement_deleted(sender, instance, **kwargs):
    client = instance.facture.client
    client.mettre_a_jour_solde()

@receiver(post_save, sender='app1.Facture')
def facture_saved(sender, instance, created, **kwargs):
    if not created:
        client = instance.client
        client.mettre_a_jour_solde()