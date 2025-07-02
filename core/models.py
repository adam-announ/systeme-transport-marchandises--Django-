"""
Modèles de base pour le système de transport de marchandises
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

class User(AbstractUser):
    """Utilisateur personnalisé avec rôles"""
    ROLES = [
        ('client', 'Client'),
        ('admin', 'Administrateur'),
        ('planificateur', 'Planificateur'),
        ('transporteur', 'Transporteur'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=ROLES, default='client')
    telephone = models.CharField(max_length=20, blank=True)
    adresse = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    actif = models.BooleanField(default=True)

class Commande(models.Model):
    """Commande de transport"""
    STATUTS = [
        ('en_attente', 'En attente'),
        ('confirmee', 'Confirmée'),
        ('en_cours', 'En cours'),
        ('livree', 'Livrée'),
        ('annulee', 'Annulée'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero = models.CharField(max_length=20, unique=True)
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commandes')
    transporteur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='missions')
    
    # Informations de transport
    adresse_enlevement = models.TextField()
    adresse_livraison = models.TextField()
    latitude_enlevement = models.FloatField()
    longitude_enlevement = models.FloatField()
    latitude_livraison = models.FloatField()
    longitude_livraison = models.FloatField()
    
    # Détails de la marchandise
    description_marchandise = models.TextField()
    poids = models.FloatField(validators=[MinValueValidator(0.1)])
    volume = models.FloatField(validators=[MinValueValidator(0.1)])
    valeur_declaree = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Statut et dates
    statut = models.CharField(max_length=20, choices=STATUTS, default='en_attente')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_enlevement_prevue = models.DateTimeField()
    date_livraison_prevue = models.DateTimeField()
    date_enlevement_reelle = models.DateTimeField(null=True, blank=True)
    date_livraison_reelle = models.DateTimeField(null=True, blank=True)
    
    # Prix
    prix_estime = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    prix_final = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    def __str__(self):
        return f"Commande {self.numero}"

class Vehicule(models.Model):
    """Véhicule de transport"""
    TYPES = [
        ('camionnette', 'Camionnette'),
        ('camion', 'Camion'),
        ('semi_remorque', 'Semi-remorque'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transporteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicules')
    immatriculation = models.CharField(max_length=20, unique=True)
    type_vehicule = models.CharField(max_length=20, choices=TYPES)
    capacite_poids = models.FloatField(validators=[MinValueValidator(0.1)])
    capacite_volume = models.FloatField(validators=[MinValueValidator(0.1)])
    disponible = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.immatriculation} - {self.type_vehicule}"

class Itineraire(models.Model):
    """Itinéraire optimisé"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    commande = models.OneToOneField(Commande, on_delete=models.CASCADE)
    distance_km = models.FloatField()
    duree_minutes = models.IntegerField()
    points_passage = models.JSONField(default=list)
    instructions = models.JSONField(default=list)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Itinéraire {self.commande.numero}"

class BonLivraison(models.Model):
    """Bon de livraison"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    commande = models.OneToOneField(Commande, on_delete=models.CASCADE)
    numero_bon = models.CharField(max_length=20, unique=True)
    date_livraison = models.DateTimeField()
    nom_destinataire = models.CharField(max_length=100)
    signature_destinataire = models.TextField(blank=True)
    commentaires = models.TextField(blank=True)
    photo_livraison = models.ImageField(upload_to='livraisons/', blank=True)
    
    def __str__(self):
        return f"Bon {self.numero_bon}"

class Notification(models.Model):
    """Notifications système"""
    TYPES = [
        ('info', 'Information'),
        ('warning', 'Avertissement'),
        ('error', 'Erreur'),
        ('success', 'Succès'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    titre = models.CharField(max_length=200)
    message = models.TextField()
    type_notification = models.CharField(max_length=10, choices=TYPES, default='info')
    lue = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date_creation']

class JournalActivite(models.Model):
    """Journal d'activité du système"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    details = models.JSONField(default=dict)
    adresse_ip = models.GenericIPAddressField()
    date_action = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date_action']

class ConfigurationSysteme(models.Model):
    """Configuration du système"""
    cle = models.CharField(max_length=100, unique=True)
    valeur = models.TextField()
    description = models.TextField(blank=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.cle