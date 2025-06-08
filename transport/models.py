# transport/models.py
from django.db import models
from django.contrib.auth.models import User

class Adresse(models.Model):
    rue = models.CharField(max_length=255)
    ville = models.CharField(max_length=100)
    code_postal = models.CharField(max_length=10)
    pays = models.CharField(max_length=100)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.rue}, {self.ville}"

class Client(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    adresse = models.CharField(max_length=255)
    telephone = models.CharField(max_length=20)
    
    def __str__(self):
        return self.user.username

class Transporteur(models.Model):
    matricule = models.CharField(max_length=50, unique=True)
    type_vehicule = models.CharField(max_length=100)
    capacite_charge = models.FloatField()
    disponible = models.BooleanField(default=True)
    
    def __str__(self):
        return self.matricule

class Commande(models.Model):
    STATUT_CHOICES = [
        ('EN_ATTENTE', 'En attente'),
        ('AFFECTEE', 'Affectée'),
        ('EN_TRANSIT', 'En transit'),
        ('LIVREE', 'Livrée'),
        ('ANNULEE', 'Annulée'),
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    date_creation = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='EN_ATTENTE')
    poids = models.FloatField()
    type_marchandise = models.CharField(max_length=100)
    adresse_enlevement = models.ForeignKey(Adresse, on_delete=models.CASCADE, related_name='commandes_enlevement')
    adresse_livraison = models.ForeignKey(Adresse, on_delete=models.CASCADE, related_name='commandes_livraison')
    transporteur = models.ForeignKey(Transporteur, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"Commande #{self.id} - {self.client}"

class BonLivraison(models.Model):
    commande = models.OneToOneField(Commande, on_delete=models.CASCADE)
    date_creation = models.DateTimeField(auto_now_add=True)
    transporteur = models.ForeignKey(Transporteur, on_delete=models.CASCADE)
    statut = models.CharField(max_length=50)
    
    def __str__(self):
        return f"BL #{self.id} - Commande #{self.commande.id}"

class Itineraire(models.Model):
    point_depart = models.ForeignKey(Adresse, on_delete=models.CASCADE, related_name='itineraires_depart')
    point_arrivee = models.ForeignKey(Adresse, on_delete=models.CASCADE, related_name='itineraires_arrivee')
    points_intermediaires = models.JSONField(default=list, blank=True)
    distance = models.FloatField()
    temps_estime = models.IntegerField()  # en minutes
    
    def __str__(self):
        return f"{self.point_depart} -> {self.point_arrivee}"