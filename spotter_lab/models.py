from django.db import models

class FuelStation(models.Model):
    opis_id = models.CharField(max_length=50, unique=True)  
    name = models.CharField(max_length=255)  
    address = models.TextField()  
    city = models.CharField(max_length=100)  
    state = models.CharField(max_length=50)  
    rack_id = models.CharField(max_length=50, null=True, blank=True) 
    price = models.FloatField()  
    latitude = models.FloatField()  
    longitude = models.FloatField() 

    def __str__(self):
        return f"{self.name} - {self.city}, {self.state} (${self.price}/gal)"
