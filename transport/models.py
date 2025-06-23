# transport/models.py - Version optimisée et unifiée

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

class Adresse(models.Model):
    rue = models.CharField(max_length=255)
    ville = models.CharField(max_length=100)
    code_postal = models.CharField(max_length=10)
    pays = models.CharField(max_length=100, default="Maroc")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Adresse"
        verbose_name_plural = "Adresses"
        ordering = ['ville', 'rue']
        indexes = [
            models.Index(fields=['ville']),
            models.Index(fields=['code_postal']),
        ]
    
    def __str__(self):
        return f"{self.rue}, {self.ville}"

class Client(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client')
    adresse = models.CharField(max_length=255)
    telephone = models.CharField(max_length=20)
    date_creation = models.DateTimeField(auto_now_add=True)
    actif = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"
    
    @property
    def nombre_commandes(self):
        return self.commande_set.count()

class Transporteur(models.Model):
    TYPES_VEHICULES = [
        ('CAMION_3T5', 'Camion 3.5T'),
        ('CAMION_7T5', 'Camion 7.5T'),
        ('CAMION_12T', 'Camion 12T'),
        ('CAMION_20T', 'Camion 20T'),
        ('SEMI_REMORQUE', 'Semi-remorque'),
        ('FOURGON', 'Fourgon'),
        ('UTILITAIRE', 'Utilitaire'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='transporteur')
    matricule = models.CharField(max_length=50, unique=True)
    type_vehicule = models.CharField(max_length=20, choices=TYPES_VEHICULES)
    capacite_charge = models.FloatField(validators=[MinValueValidator(0.1)])
    disponible = models.BooleanField(default=True)
    latitude_actuelle = models.FloatField(null=True, blank=True)
    longitude_actuelle = models.FloatField(null=True, blank=True)
    derniere_maj_position = models.DateTimeField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    note_moyenne = models.FloatField(
        default=5.0, 
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)]
    )
    actif = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Transporteur"
        verbose_name_plural = "Transporteurs"
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['disponible', 'actif']),
            models.Index(fields=['matricule']),
        ]
    
    def __str__(self):
        return f"{self.matricule} - {self.user.get_full_name() or self.user.username}"
    
    @property
    def taux_reussite(self):
        total = self.missiontransporteur_set.count()
        if total == 0:
            return 100
        completees = self.missiontransporteur_set.filter(statut='TERMINEE').count()
        return round((completees / total) * 100, 1)

class Commande(models.Model):
    STATUT_CHOICES = [
        ('EN_ATTENTE', 'En attente'),
        ('AFFECTEE', 'Affectée'),
        ('EN_TRANSIT', 'En transit'),
        ('LIVREE', 'Livrée'),
        ('ANNULEE', 'Annulée'),
    ]
    
    PRIORITE_CHOICES = [
        (0, 'Normale'),
        (1, 'Haute'),
        (2, 'Urgente'),
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    date_creation = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='EN_ATTENTE')
    poids = models.FloatField(validators=[MinValueValidator(0.1)])
    type_marchandise = models.CharField(max_length=100)
    adresse_enlevement = models.ForeignKey(
        Adresse, 
        on_delete=models.CASCADE, 
        related_name='commandes_enlevement'
    )
    adresse_livraison = models.ForeignKey(
        Adresse, 
        on_delete=models.CASCADE, 
        related_name='commandes_livraison'
    )
    transporteur = models.ForeignKey(
        Transporteur, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    priorite = models.IntegerField(choices=PRIORITE_CHOICES, default=0)
    prix_estime = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    instructions_speciales = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Commande"
        verbose_name_plural = "Commandes"
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['statut']),
            models.Index(fields=['date_creation']),
            models.Index(fields=['client']),
            models.Index(fields=['priorite']),
        ]
    
    def __str__(self):
        return f"Commande #{self.id} - {self.client}"
    
    @property
    def est_urgente(self):
        return self.priorite == 2

class MissionTransporteur(models.Model):
    STATUT_CHOICES = [
        ('ASSIGNEE', 'Assignée'),
        ('ACCEPTEE', 'Acceptée'),
        ('EN_COURS', 'En cours'),
        ('TERMINEE', 'Terminée'),
        ('ANNULEE', 'Annulée'),
    ]
    
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE)
    transporteur = models.ForeignKey(Transporteur, on_delete=models.CASCADE)
    date_assignation = models.DateTimeField(auto_now_add=True)
    date_acceptation = models.DateTimeField(null=True, blank=True)
    date_debut = models.DateTimeField(null=True, blank=True)
    date_fin = models.DateTimeField(null=True, blank=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='ASSIGNEE')
    itineraire_optimise = models.JSONField(default=dict, blank=True)
    distance_parcourue = models.FloatField(default=0)
    
    class Meta:
        verbose_name = "Mission"
        verbose_name_plural = "Missions"
        ordering = ['-date_assignation']
        unique_together = ['commande', 'transporteur']
        indexes = [
            models.Index(fields=['statut']),
            models.Index(fields=['transporteur', 'statut']),
        ]
    
    def __str__(self):
        return f"Mission #{self.id} - {self.transporteur.matricule}"

class Incident(models.Model):
    TYPE_CHOICES = [
        ('ACCIDENT', 'Accident'),
        ('PANNE', 'Panne véhicule'),
        ('RETARD', 'Retard'),
        ('MARCHANDISE', 'Problème marchandise'),
        ('METEO', 'Conditions météo'),
        ('TRAFIC', 'Problème de trafic'),
        ('CLIENT', 'Problème client'),
        ('AUTRE', 'Autre'),
    ]
    
    mission = models.ForeignKey(MissionTransporteur, on_delete=models.CASCADE)
    transporteur = models.ForeignKey(Transporteur, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.TextField()
    date_signalement = models.DateTimeField(auto_now_add=True)
    photo = models.ImageField(upload_to='incidents/', null=True, blank=True)
    resolu = models.BooleanField(default=False)
    date_resolution = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Incident"
        verbose_name_plural = "Incidents"
        ordering = ['-date_signalement']
    
    def __str__(self):
        return f"Incident {self.get_type_display()} - Mission #{self.mission.id}"

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
        ('URGENTE', 'Urgente'),
    ]
    
    destinataire = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications_recues')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    titre = models.CharField(max_length=200)
    message = models.TextField()
    date_creation = models.DateTimeField(auto_now_add=True)
    lu = models.BooleanField(default=False)
    commande = models.ForeignKey(Commande, on_delete=models.SET_NULL, null=True, blank=True)
    priorite = models.CharField(max_length=10, choices=PRIORITE_CHOICES, default='NORMALE')
    
    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['destinataire', 'lu']),
            models.Index(fields=['date_creation']),
        ]
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.destinataire.username}"
    
    def marquer_comme_lue(self):
        if not self.lu:
            self.lu = True
            self.save()

class ParametreSysteme(models.Model):
    TYPE_CHOICES = [
        ('STRING', 'Texte'),
        ('INTEGER', 'Entier'),
        ('FLOAT', 'Décimal'),
        ('BOOLEAN', 'Booléen'),
        ('JSON', 'JSON'),
    ]
    
    nom = models.CharField(max_length=100, unique=True)
    valeur = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='STRING')
    description = models.TextField(blank=True)
    modifiable = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Paramètre système"
        verbose_name_plural = "Paramètres système"
        ordering = ['nom']
    
    def __str__(self):
        return f"{self.nom} = {self.valeur}"
    
    def get_valeur(self):
        """Retourne la valeur dans le bon type"""
        if self.type == 'INTEGER':
            return int(self.valeur)
        elif self.type == 'FLOAT':
            return float(self.valeur)
        elif self.type == 'BOOLEAN':
            return self.valeur.lower() in ['true', '1', 'yes', 'oui']
        elif self.type == 'JSON':
            import json
            return json.loads(self.valeur)
        return self.valeur

# Modèles de monitoring et audit
class JournalActivite(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Création'),
        ('UPDATE', 'Modification'),
        ('DELETE', 'Suppression'),
        ('LOGIN', 'Connexion'),
        ('LOGOUT', 'Déconnexion'),
        ('ASSIGN', 'Affectation'),
    ]
    
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    objet_type = models.CharField(max_length=50)
    objet_id = models.PositiveIntegerField(null=True, blank=True)
    details = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Journal d'activité"
        verbose_name_plural = "Journal d'activité"
        ordering = ['-date']
        indexes = [
            models.Index(fields=['utilisateur']),
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"{self.utilisateur} - {self.get_action_display()} - {self.date}"