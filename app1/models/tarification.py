from django.db import models
from decimal import Decimal
from .destination import Destination
from .type_service import TypeService


class Tarification(models.Model):

    
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE)
    type_service = models.ForeignKey(TypeService, on_delete=models.CASCADE)
    tarif_poids = models.DecimalField(max_digits=10, decimal_places=2, default=10.00, help_text="Tarif par kg en DA")
    tarif_volume = models.DecimalField(max_digits=10, decimal_places=2, default=20.00, help_text="Tarif par m³ en DA")

    class Meta:
        unique_together = ['destination', 'type_service']

    def __str__(self):
        return f"{self.destination.ville} - {self.destination.wilaya} - {self.type_service}"

    def calculer_prix(cls, destination, type_service ,self, poids, volume):
        from decimal import Decimal


        # 1. Chercher si une règle de tarification existe
        tarification = cls.objects.filter(
            destination=destination, 
            type_service=type_service
        ).first()
        
        if tarification:
            # Utiliser les tarifs personnalisés
            tarif_poids = tarification.tarif_poids
            tarif_volume = tarification.tarif_volume
        else:
            # Utiliser les tarifs par défaut
            tarif_poids = Decimal('10.00')
            tarif_volume = Decimal('20.00')
        
        # 2. Calcul du montant
        poids_decimal = Decimal(str(poids))
        volume_decimal = Decimal(str(volume))
        
        if self.type_service.type_service == 'EXPRESS':
            # EXPRESS : tarif de base calculé selon distance
            tarif_base_express = Decimal(str(self.destination.distance_estimee)) * Decimal('25.00')
            prix = tarif_base_express + (poids * self.tarif_poids) + (volume * self.tarif_volume)
        else:
            # STANDARD et INTERNATIONAL : tarif_base normal
            prix = self.destination.tarif_base + (poids * self.tarif_poids) + (volume * self.tarif_volume)
        
        return prix
    
    def calculer_delai(self):

        if self.type_service.type_service == 'EXPRESS':
            # EXPRESS : délai selon distance
            if self.destination.distance_estimee < 500:
                return 1  # 1 jour
            else:
                return 2  # 2 jours
        else:
            # STANDARD et INTERNATIONAL : délai de la destination
            return self.destination.delai_livraison_estime
    