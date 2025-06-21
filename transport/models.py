# transport/models.py - Version mise à jour
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

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
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    matricule = models.CharField(max_length=50, unique=True)
    type_vehicule = models.CharField(max_length=100)
    capacite_charge = models.FloatField()
    disponible = models.BooleanField(default=True)
    latitude_actuelle = models.FloatField(null=True, blank=True)
    longitude_actuelle = models.FloatField(null=True, blank=True)
    derniere_maj_position = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.matricule} - {self.user.username}"

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
    priorite = models.IntegerField(default=0)  # 0=normale, 1=haute, 2=urgente
    
    def __str__(self):
        return f"Commande #{self.id} - {self.client}"

class MissionTransporteur(models.Model):
    STATUT_CHOICES = [
        ('ASSIGNEE', 'Assignée'),
        ('EN_COURS', 'En cours'),
        ('TERMINEE', 'Terminée'),
        ('ANNULEE', 'Annulée'),
    ]
    
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE)
    transporteur = models.ForeignKey(Transporteur, on_delete=models.CASCADE)
    date_assignation = models.DateTimeField(auto_now_add=True)
    date_debut = models.DateTimeField(null=True, blank=True)
    date_fin = models.DateTimeField(null=True, blank=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='ASSIGNEE')
    itineraire_optimise = models.JSONField(default=dict, blank=True)
    distance_parcourue = models.FloatField(default=0)
    
    def __str__(self):
        return f"Mission {self.id} - {self.transporteur.matricule}"

class BonLivraison(models.Model):
    commande = models.OneToOneField(Commande, on_delete=models.CASCADE)
    date_creation = models.DateTimeField(auto_now_add=True)
    transporteur = models.ForeignKey(Transporteur, on_delete=models.CASCADE)
    statut = models.CharField(max_length=50)
    signature_client = models.ImageField(upload_to='signatures/', null=True, blank=True)
    commentaire = models.TextField(blank=True)
    
    def __str__(self):
        return f"BL #{self.id} - Commande #{self.commande.id}"

class Itineraire(models.Model):
    point_depart = models.ForeignKey(Adresse, on_delete=models.CASCADE, related_name='itineraires_depart')
    point_arrivee = models.ForeignKey(Adresse, on_delete=models.CASCADE, related_name='itineraires_arrivee')
    points_intermediaires = models.JSONField(default=list, blank=True)
    distance = models.FloatField()
    temps_estime = models.IntegerField()  # en minutes
    type_route = models.CharField(max_length=50, default='nationale')
    
    def __str__(self):
        return f"{self.point_depart} -> {self.point_arrivee}"

class Incident(models.Model):
    TYPE_CHOICES = [
        ('ACCIDENT', 'Accident'),
        ('PANNE', 'Panne véhicule'),
        ('RETARD', 'Retard'),
        ('MARCHANDISE', 'Problème marchandise'),
        ('METEO', 'Conditions météo'),
        ('AUTRE', 'Autre'),
    ]
    
    mission = models.ForeignKey(MissionTransporteur, on_delete=models.CASCADE)
    transporteur = models.ForeignKey(Transporteur, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.TextField()
    date_signalement = models.DateTimeField(auto_now_add=True)
    photo = models.ImageField(upload_to='incidents/', null=True, blank=True)
    resolu = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Incident {self.type} - Mission {self.mission.id}"

class Notification(models.Model):
    TYPE_CHOICES = [
        ('MISSION', 'Nouvelle mission'),
        ('STATUT', 'Changement de statut'),
        ('INCIDENT', 'Incident signalé'),
        ('SYSTEME', 'Message système'),
    ]
    
    PRIORITE_CHOICES = [
        ('BASSE', 'Basse'),
        ('NORMALE', 'Normale'),
        ('HAUTE', 'Haute'),
    ]
    
    destinataire = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications_recues')
    transporteur = models.ForeignKey(Transporteur, on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    titre = models.CharField(max_length=200)
    message = models.TextField()
    date_creation = models.DateTimeField(auto_now_add=True)
    lu = models.BooleanField(default=False)
    commande = models.ForeignKey(Commande, on_delete=models.SET_NULL, null=True, blank=True)
    priorite = models.CharField(max_length=10, choices=PRIORITE_CHOICES, default='NORMALE')
    
    def __str__(self):
        return f"{self.type} - {self.destinataire.username}"

class DonneesMeteo(models.Model):
    zone = models.CharField(max_length=100)
    date_creation = models.DateTimeField(auto_now_add=True)
    temperature = models.FloatField()
    conditions = models.CharField(max_length=50)  # ensoleillé, nuageux, pluie, neige
    vent_vitesse = models.FloatField()  # km/h
    vent_direction = models.CharField(max_length=10, blank=True)  # N, S, E, O
    visibilite = models.IntegerField()  # en mètres
    precipitation = models.FloatField(default=0)  # mm
    alerte = models.BooleanField(default=False)
    niveau_alerte = models.CharField(max_length=20, blank=True)  # basse, moyenne, haute
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"Météo {self.zone} - {self.date_creation}"

class DonneesTrafic(models.Model):
    NIVEAU_CHOICES = [
        ('fluide', 'Fluide'),
        ('normal', 'Normal'),
        ('dense', 'Dense'),
        ('bloque', 'Bloqué'),
    ]
    
    zone = models.CharField(max_length=100)
    date_creation = models.DateTimeField(auto_now_add=True)
    niveau = models.CharField(max_length=20, choices=NIVEAU_CHOICES, default='normal')
    vitesse_moyenne = models.FloatField()  # km/h
    temps_retard = models.IntegerField(default=0)  # minutes
    incidents = models.JSONField(default=list, blank=True)
    routes_affectees = models.JSONField(default=list, blank=True)
    
    def __str__(self):
        return f"Trafic {self.zone} - {self.niveau}"

class ParametreSysteme(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    valeur = models.CharField(max_length=255)
    type = models.CharField(max_length=20)  # string, int, float, bool
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.nom} = {self.valeur}"

class JournalActivite(models.Model):
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    details = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.utilisateur} - {self.action} - {self.date}"