"""
Modèles améliorés pour le système de transport de marchandises
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image

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
    
    # Nouveaux champs pour géolocalisation
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    derniere_connexion_ip = models.GenericIPAddressField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

class Adresse(models.Model):
    """Modèle pour les adresses avec géocodage"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rue = models.CharField(max_length=200)
    ville = models.CharField(max_length=100)
    code_postal = models.CharField(max_length=10)
    pays = models.CharField(max_length=100, default='Maroc')
    latitude = models.FloatField()
    longitude = models.FloatField()
    date_creation = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.rue}, {self.ville} {self.code_postal}"
    
    @property
    def adresse_complete(self):
        return f"{self.rue}, {self.ville} {self.code_postal}, {self.pays}"

class TypeMarchandise(models.Model):
    """Types de marchandises"""
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    tarif_base = models.DecimalField(max_digits=10, decimal_places=2)
    coefficient_volume = models.FloatField(default=1.0)
    coefficient_poids = models.FloatField(default=1.0)
    fragile = models.BooleanField(default=False)
    dangereux = models.BooleanField(default=False)
    
    def __str__(self):
        return self.nom

class Commande(models.Model):
    """Commande de transport améliorée"""
    STATUTS = [
        ('en_attente', 'En attente'),
        ('confirmee', 'Confirmée'),
        ('en_cours', 'En cours'),
        ('livree', 'Livrée'),
        ('annulee', 'Annulée'),
        ('retournee', 'Retournée'),
        ('incident', 'Incident'),
    ]
    
    PRIORITES = [
        ('normale', 'Normale'),
        ('urgente', 'Urgente'),
        ('express', 'Express'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero = models.CharField(max_length=20, unique=True)
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commandes')
    transporteur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='missions')
    
    # Adresses
    adresse_enlevement = models.ForeignKey(Adresse, on_delete=models.CASCADE, related_name='enlevements')
    adresse_livraison = models.ForeignKey(Adresse, on_delete=models.CASCADE, related_name='livraisons')
    
    # Détails de la marchandise
    type_marchandise = models.ForeignKey(TypeMarchandise, on_delete=models.CASCADE)
    description_marchandise = models.TextField()
    poids = models.FloatField(validators=[MinValueValidator(0.1)])
    volume = models.FloatField(validators=[MinValueValidator(0.1)])
    valeur_declaree = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    instructions_speciales = models.TextField(blank=True)
    
    # Statut et priorité
    statut = models.CharField(max_length=20, choices=STATUTS, default='en_attente')
    priorite = models.CharField(max_length=20, choices=PRIORITES, default='normale')
    
    # Dates
    date_creation = models.DateTimeField(auto_now_add=True)
    date_enlevement_prevue = models.DateTimeField()
    date_livraison_prevue = models.DateTimeField()
    date_enlevement_reelle = models.DateTimeField(null=True, blank=True)
    date_livraison_reelle = models.DateTimeField(null=True, blank=True)
    
    # Prix et facturation
    prix_estime = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    prix_final = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    facturee = models.BooleanField(default=False)
    
    # Suivi et QR Code
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True)
    code_suivi = models.CharField(max_length=50, unique=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.code_suivi:
            self.code_suivi = f"TR{self.id.hex[:8].upper()}"
        
        super().save(*args, **kwargs)
        
        # Générer QR Code
        if not self.qr_code:
            self.generer_qr_code()
    
    def generer_qr_code(self):
        """Génère un QR code pour le suivi de la commande"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(f"https://transport-system.com/suivi/{self.code_suivi}")
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, 'PNG')
        
        filename = f'qr_code_{self.numero}.png'
        filebuffer = File(buffer, name=filename)
        self.qr_code.save(filename, filebuffer)
        buffer.close()
    
    def __str__(self):
        return f"Commande {self.numero}"

class Vehicule(models.Model):
    """Véhicule de transport amélioré"""
    TYPES = [
        ('camionnette', 'Camionnette'),
        ('camion', 'Camion'),
        ('semi_remorque', 'Semi-remorque'),
        ('fourgon', 'Fourgon'),
    ]
    
    ETATS = [
        ('excellent', 'Excellent'),
        ('bon', 'Bon'),
        ('moyen', 'Moyen'),
        ('reparation', 'En réparation'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transporteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicules')
    immatriculation = models.CharField(max_length=20, unique=True)
    marque = models.CharField(max_length=50)
    modele = models.CharField(max_length=50)
    annee = models.IntegerField()
    type_vehicule = models.CharField(max_length=20, choices=TYPES)
    
    # Capacités
    capacite_poids = models.FloatField(validators=[MinValueValidator(0.1)])
    capacite_volume = models.FloatField(validators=[MinValueValidator(0.1)])
    
    # État et maintenance
    etat = models.CharField(max_length=20, choices=ETATS, default='bon')
    kilometrage = models.IntegerField(default=0)
    derniere_revision = models.DateField(null=True, blank=True)
    prochaine_revision = models.DateField(null=True, blank=True)
    assurance_valide = models.BooleanField(default=True)
    controle_technique_valide = models.BooleanField(default=True)
    
    # Disponibilité
    disponible = models.BooleanField(default=True)
    position_latitude = models.FloatField(null=True, blank=True)
    position_longitude = models.FloatField(null=True, blank=True)
    derniere_mise_a_jour_position = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.immatriculation} - {self.marque} {self.modele}"

class Itineraire(models.Model):
    """Itinéraire optimisé avec plus de détails"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    commande = models.OneToOneField(Commande, on_delete=models.CASCADE)
    distance_km = models.FloatField()
    duree_minutes = models.IntegerField()
    cout_carburant = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    # Données de routage
    points_passage = models.JSONField(default=list)
    instructions = models.JSONField(default=list)
    polyline = models.TextField(blank=True)  # Pour Google Maps
    
    # Conditions
    conditions_meteo = models.JSONField(default=dict)
    conditions_trafic = models.CharField(max_length=50, blank=True)
    
    # Optimisation
    optimise = models.BooleanField(default=False)
    date_optimisation = models.DateTimeField(null=True, blank=True)
    algorithme_utilise = models.CharField(max_length=50, blank=True)
    
    date_creation = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Itinéraire {self.commande.numero} - {self.distance_km}km"

class PositionTransporteur(models.Model):
    """Suivi GPS des transporteurs"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transporteur = models.ForeignKey(User, on_delete=models.CASCADE)
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, null=True, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    altitude = models.FloatField(null=True, blank=True)
    vitesse = models.FloatField(null=True, blank=True)  # km/h
    cap = models.FloatField(null=True, blank=True)  # degrés
    precision = models.FloatField(null=True, blank=True)  # mètres
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']

class BonLivraison(models.Model):
    """Bon de livraison amélioré"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    commande = models.OneToOneField(Commande, on_delete=models.CASCADE)
    numero_bon = models.CharField(max_length=20, unique=True)
    
    # Livraison
    date_livraison = models.DateTimeField()
    nom_destinataire = models.CharField(max_length=100)
    signature_destinataire = models.TextField(blank=True)
    photo_destinataire = models.ImageField(upload_to='signatures/', blank=True)
    
    # Détails
    commentaires = models.TextField(blank=True)
    photo_livraison = models.ImageField(upload_to='livraisons/', blank=True)
    etat_marchandise = models.CharField(max_length=50, default='bon_etat')
    
    # Validation
    valide_par_client = models.BooleanField(default=False)
    date_validation_client = models.DateTimeField(null=True, blank=True)
    note_client = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    commentaire_client = models.TextField(blank=True)
    
    def __str__(self):
        return f"Bon {self.numero_bon}"

class Incident(models.Model):
    """Gestion des incidents"""
    TYPES = [
        ('retard', 'Retard'),
        ('panne', 'Panne véhicule'),
        ('accident', 'Accident'),
        ('marchandise', 'Problème marchandise'),
        ('route', 'Problème de route'),
        ('autre', 'Autre'),
    ]
    
    STATUTS = [
        ('ouvert', 'Ouvert'),
        ('en_cours', 'En cours de traitement'),
        ('resolu', 'Résolu'),
        ('ferme', 'Fermé'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name='incidents')
    reporteur = models.ForeignKey(User, on_delete=models.CASCADE)
    
    type_incident = models.CharField(max_length=20, choices=TYPES)
    titre = models.CharField(max_length=200)
    description = models.TextField()
    statut = models.CharField(max_length=20, choices=STATUTS, default='ouvert')
    
    # Localisation
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    # Dates
    date_creation = models.DateTimeField(auto_now_add=True)
    date_resolution = models.DateTimeField(null=True, blank=True)
    
    # Média
    photo = models.ImageField(upload_to='incidents/', blank=True)
    
    def __str__(self):
        return f"Incident {self.type_incident} - {self.commande.numero}"

class Notification(models.Model):
    """Notifications système améliorées"""
    TYPES = [
        ('info', 'Information'),
        ('warning', 'Avertissement'),
        ('error', 'Erreur'),
        ('success', 'Succès'),
        ('urgent', 'Urgent'),
    ]
    
    CANAUX = [
        ('systeme', 'Système'),
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    titre = models.CharField(max_length=200)
    message = models.TextField()
    type_notification = models.CharField(max_length=10, choices=TYPES, default='info')
    canal = models.CharField(max_length=20, choices=CANAUX, default='systeme')
    
    # Statut
    lue = models.BooleanField(default=False)
    date_lecture = models.DateTimeField(null=True, blank=True)
    
    # Liens
    lien_action = models.URLField(blank=True)
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, null=True, blank=True)
    
    date_creation = models.DateTimeField(auto_now_add=True)
    date_expiration = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-date_creation']

class JournalActivite(models.Model):
    """Journal d'activité système amélioré"""
    NIVEAUX = [
        ('info', 'Information'),
        ('warning', 'Avertissement'),
        ('error', 'Erreur'),
        ('critical', 'Critique'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    niveau = models.CharField(max_length=20, choices=NIVEAUX, default='info')
    details = models.JSONField(default=dict)
    
    # Contexte
    commande = models.ForeignKey(Commande, on_delete=models.SET_NULL, null=True, blank=True)
    adresse_ip = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    
    date_action = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date_action']

class ConfigurationSysteme(models.Model):
    """Configuration système avancée"""
    TYPES = [
        ('string', 'Chaîne'),
        ('integer', 'Entier'),
        ('float', 'Décimal'),
        ('boolean', 'Booléen'),
        ('json', 'JSON'),
    ]
    
    cle = models.CharField(max_length=100, unique=True)
    valeur = models.TextField()
    type_valeur = models.CharField(max_length=20, choices=TYPES, default='string')
    description = models.TextField(blank=True)
    categorie = models.CharField(max_length=50, default='general')
    modifiable = models.BooleanField(default=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    def get_valeur_typee(self):
        """Retourne la valeur avec le bon type"""
        if self.type_valeur == 'integer':
            return int(self.valeur)
        elif self.type_valeur == 'float':
            return float(self.valeur)
        elif self.type_valeur == 'boolean':
            return self.valeur.lower() in ('true', '1', 'yes', 'on')
        elif self.type_valeur == 'json':
            import json
            return json.loads(self.valeur)
        return self.valeur
    
    def __str__(self):
        return self.cle

class Tarification(models.Model):
    """Système de tarification avancé"""
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    # Tarifs de base
    tarif_base_km = models.DecimalField(max_digits=8, decimal_places=4)
    tarif_base_poids = models.DecimalField(max_digits=8, decimal_places=4)
    tarif_base_volume = models.DecimalField(max_digits=8, decimal_places=4)
    
    # Coefficients
    coefficient_urgence = models.FloatField(default=1.5)
    coefficient_express = models.FloatField(default=2.0)
    coefficient_weekend = models.FloatField(default=1.2)
    coefficient_nuit = models.FloatField(default=1.3)
    
    # Zones géographiques
    zones_speciales = models.JSONField(default=dict)
    
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.nom