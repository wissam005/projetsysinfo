from django.db import models

class TypeService(models.Model):

    TYPE_CHOICES = [
        ('STANDARD', 'Standard'),
        ('EXPRESS', 'Express'),
        ('INTERNATIONAL', 'International'),
    ]
    type_service = models.CharField(max_length=20, choices=TYPE_CHOICES, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.type_service
