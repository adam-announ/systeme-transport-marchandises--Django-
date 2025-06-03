from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

class Adresse(models.Model):
    rue = models.CharField(max_length=200)
    ville = models.CharField(max_length=100)
    code_postal = models.CharField(max_length=10)
    pays = models.CharField(max_length=50, default='Maroc')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Adresse"
        verbose_name_plural = "Adresses"

    def __str__(self):
        return f"{self.rue}, {self.ville}"

    def get_full_address(self):
        return f"{self.rue}, {self.ville}, {self.code_postal}, {self.pays}"

class Utilisateur(models.Model):
    ROLES = [
        ('client', 'Client'),
        ('transporteur', 'Transporteur'),
        ('planificateur', 'Planificateur'),
        ('admin', 'Administrateur'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telephone = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=20, choices=ROLES)
    adresse = models.ForeignKey(Adresse, on_delete=models.SET_NULL, null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        return f"{self.prenom} {self.nom}"

    @property
    def full_name(self):
        return f"{self.prenom} {self.nom}"

class Client(models.Model):
    utilisateur = models.OneToOneField(Utilisateur, on_delete=models.CASCADE)
    entreprise = models.CharField(max_length=200, blank=True)
    siret = models.CharField(max_length=20, blank=True)
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rating = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(5)], 
        default=5.0
    )
    
    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"

    def __str__(self):
        return f"Client: {self.utilisateur.full_name}"

class Transporteur(models.Model):
    TYPES_VEHICULE = [
        ('camionnette', 'Camionnette'),
        ('camion', 'Camion'),
        ('semi_remorque', 'Semi-remorque'),
        ('fourgon', 'Fourgon'),
    ]
    
    STATUTS = [
        ('disponible', 'Disponible'),
        ('en_mission', 'En mission'),
        ('maintenance', 'En maintenance'),
        ('repos', 'En repos'),
    ]

    utilisateur = models.OneToOneField(Utilisateur, on_delete=models.CASCADE)
    matricule = models.CharField(max_length=50, unique=True)
    type_vehicule = models.CharField(max_length=20, choices=TYPES_VEHICULE)
    capacite_charge = models.FloatField(help_text="Capacité en kg")
    capacite_volume = models.FloatField(help_text="Capacité en m³", null=True, blank=True)
    disponibilite = models.BooleanField(default=True)
    statut = models.CharField(max_length=20, choices=STATUTS, default='disponible')
    permis_conduire = models.CharField(max_length=50)
    experience_annees = models.IntegerField(default=0)
    rating = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(5)], 
        default=5.0
    )
    position_latitude = models.FloatField(null=True, blank=True)
    position_longitude = models.FloatField(null=True, blank=True)
    derniere_position_update = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Transporteur"
        verbose_name_plural = "Transporteurs"

    def __str__(self):
        return f"{self.matricule} - {self.utilisateur.full_name}"

    def update_position(self, latitude, longitude):
        self.position_latitude = latitude
        self.position_longitude = longitude
        self.derniere_position_update = timezone.now()
        self.save()

class Commande(models.Model):
    STATUTS = [
        ('brouillon', 'Brouillon'),
        ('en_attente', 'En attente'),
        ('assignee', 'Assignée'),
        ('acceptee', 'Acceptée'),
        ('en_cours_enlevement', 'En cours d\'enlèvement'),
        ('en_transit', 'En transit'),
        ('en_cours_livraison', 'En cours de livraison'),
        ('livree', 'Livrée'),
        ('annulee', 'Annulée'),
        ('probleme', 'Problème signalé'),
    ]

    PRIORITES = [
        ('basse', 'Basse'),
        ('normale', 'Normale'),
        ('haute', 'Haute'),
        ('urgente', 'Urgente'),
    ]

    TYPES_MARCHANDISE = [
        ('electronique', 'Électronique'),
        ('textile', 'Textile'),
        ('alimentaire', 'Alimentaire'),
        ('mobilier', 'Mobilier'),
        ('chimique', 'Produits chimiques'),
        ('fragile', 'Fragile'),
        ('dangereux', 'Matières dangereuses'),
        ('autre', 'Autre'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero = models.CharField(max_length=20, unique=True, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='commandes')
    transporteur = models.ForeignKey(
        Transporteur, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='commandes'
    )
    
    # Informations marchandise
    type_marchandise = models.CharField(max_length=20, choices=TYPES_MARCHANDISE)
    description = models.TextField(blank=True)
    poids = models.FloatField(validators=[MinValueValidator(0.1)])
    volume = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0.1)])
    valeur_declaree = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    instructions_speciales = models.TextField(blank=True)
    
    # Adresses
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
    
    # Contact
    contact_enlevement = models.CharField(max_length=100, blank=True)
    contact_livraison = models.CharField(max_length=100, blank=True)
    telephone_enlevement = models.CharField(max_length=20, blank=True)
    telephone_livraison = models.CharField(max_length=20, blank=True)
    
    # Statut et timing
    statut = models.CharField(max_length=20, choices=STATUTS, default='en_attente')
    priorite = models.CharField(max_length=10, choices=PRIORITES, default='normale')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_enlevement_prevue = models.DateTimeField(null=True, blank=True)
    date_livraison_prevue = models.DateTimeField(null=True, blank=True)
    date_enlevement_effective = models.DateTimeField(null=True, blank=True)
    date_livraison_effective = models.DateTimeField(null=True, blank=True)
    
    # Prix
    prix_estime = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    prix_final = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Commande"
        verbose_name_plural = "Commandes"
        ordering = ['-created_at']

    def __str__(self):
        return f"Commande {self.numero}"

    def save(self, *args, **kwargs):
        if not self.numero:
            # Générer un numéro unique
            from datetime import datetime
            today = datetime.now()
            prefix = f"CMD{today.strftime('%Y%m%d')}"
            last_command = Commande.objects.filter(
                numero__startswith=prefix
            ).order_by('-numero').first()
            
            if last_command:
                last_number = int(last_command.numero[-4:])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.numero = f"{prefix}{new_number:04d}"
        
        super().save(*args, **kwargs)

    @property
    def duree_estimee(self):
        if self.date_enlevement_prevue and self.date_livraison_prevue:
            return self.date_livraison_prevue - self.date_enlevement_prevue
        return None

class Itineraire(models.Model):
    commande = models.OneToOneField(Commande, on_delete=models.CASCADE, related_name='itineraire')
    points_intermediaires = models.JSONField(default=list, blank=True)
    distance_km = models.FloatField(null=True, blank=True)
    duree_minutes = models.IntegerField(null=True, blank=True)
    polyline = models.TextField(blank=True)
    cout_carburant = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    instructions = models.JSONField(default=list, blank=True)
    optimise = models.BooleanField(default=False)
    date_calcul = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Itinéraire"
        verbose_name_plural = "Itinéraires"

    def __str__(self):
        return f"Itinéraire - {self.commande.numero}"

class Tracking(models.Model):
    ETAPES = [
        ('commande_creee', 'Commande créée'),
        ('transporteur_assigne', 'Transporteur assigné'),
        ('enlevement_en_cours', 'Enlèvement en cours'),
        ('marchandise_enlevee', 'Marchandise enlevée'),
        ('en_transit', 'En transit'),
        ('arrivee_destination', 'Arrivée à destination'),
        ('livraison_en_cours', 'Livraison en cours'),
        ('livree', 'Livrée'),
        ('incident', 'Incident signalé'),
    ]

    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name='tracking')
    etape = models.CharField(max_length=30, choices=ETAPES)
    description = models.TextField(blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    photo = models.ImageField(upload_to='tracking_photos/', null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Suivi"
        verbose_name_plural = "Suivis"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.commande.numero} - {self.get_etape_display()}"

class BonLivraison(models.Model):
    STATUTS = [
        ('en_attente', 'En attente'),
        ('signe_client', 'Signé par le client'),
        ('valide', 'Validé'),
        ('litige', 'En litige'),
    ]

    commande = models.OneToOneField(Commande, on_delete=models.CASCADE, related_name='bon_livraison')
    numero = models.CharField(max_length=20, unique=True, editable=False)
    statut = models.CharField(max_length=20, choices=STATUTS, default='en_attente')
    signature_client = models.TextField(blank=True)  # Base64 de la signature
    signature_transporteur = models.TextField(blank=True)
    nom_receptionnaire = models.CharField(max_length=100, blank=True)
    commentaires = models.TextField(blank=True)
    photo_livraison = models.ImageField(upload_to='livraisons/', null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_signature = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Bon de livraison"
        verbose_name_plural = "Bons de livraison"

    def __str__(self):
        return f"Bon {self.numero} - {self.commande.numero}"

    def save(self, *args, **kwargs):
        if not self.numero:
            from datetime import datetime
            today = datetime.now()
            prefix = f"BL{today.strftime('%Y%m%d')}"
            last_bon = BonLivraison.objects.filter(
                numero__startswith=prefix
            ).order_by('-numero').first()
            
            if last_bon:
                last_number = int(last_bon.numero[-4:])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.numero = f"{prefix}{new_number:04d}"
        
        super().save(*args, **kwargs)

class Incident(models.Model):
    TYPES = [
        ('panne', 'Panne véhicule'),
        ('accident', 'Accident'),
        ('retard', 'Retard'),
        ('marchandise_endommagee', 'Marchandise endommagée'),
        ('refus_livraison', 'Refus de livraison'),
        ('probleme_acces', 'Problème d\'accès'),
        ('autre', 'Autre'),
    ]

    GRAVITES = [
        ('faible', 'Faible'),
        ('moyenne', 'Moyenne'),
        ('elevee', 'Élevée'),
        ('critique', 'Critique'),
    ]

    STATUTS = [
        ('ouvert', 'Ouvert'),
        ('en_cours', 'En cours de traitement'),
        ('resolu', 'Résolu'),
        ('ferme', 'Fermé'),
    ]

    commande = models.ForeignKey(
        Commande, 
        on_delete=models.CASCADE, 
        related_name='incidents',
        null=True, 
        blank=True
    )
    transporteur = models.ForeignKey(
        Transporteur, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    type_incident = models.CharField(max_length=30, choices=TYPES)
    gravite = models.CharField(max_length=10, choices=GRAVITES, default='moyenne')
    statut = models.CharField(max_length=10, choices=STATUTS, default='ouvert')
    titre = models.CharField(max_length=200)
    description = models.TextField()
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    photo = models.ImageField(upload_to='incidents/', null=True, blank=True)
    date_incident = models.DateTimeField()
    date_creation = models.DateTimeField(auto_now_add=True)
    date_resolution = models.DateTimeField(null=True, blank=True)
    resolution_commentaire = models.TextField(blank=True)
    traite_par = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='incidents_traites'
    )

    class Meta:
        verbose_name = "Incident"
        verbose_name_plural = "Incidents"
        ordering = ['-date_creation']

    def __str__(self):
        return f"Incident {self.type_incident} - {self.titre}"

class Notification(models.Model):
    TYPES = [
        ('commande', 'Nouvelle commande'),
        ('assignation', 'Assignation transporteur'),
        ('statut', 'Changement de statut'),
        ('incident', 'Incident signalé'),
        ('livraison', 'Livraison effectuée'),
        ('systeme', 'Notification système'),
    ]

    destinataire = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type_notification = models.CharField(max_length=20, choices=TYPES)
    titre = models.CharField(max_length=200)
    message = models.TextField()
    commande = models.ForeignKey(
        Commande, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    lue = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_lecture = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-date_creation']

    def __str__(self):
        return f"{self.titre} - {self.destinataire.username}"

    def marquer_comme_lue(self):
        if not self.lue:
            self.lue = True
            self.date_lecture = timezone.now()
            self.save()

class Journal(models.Model):
    ACTIONS = [
        ('creation', 'Création'),
        ('modification', 'Modification'),
        ('suppression', 'Suppression'),
        ('assignation', 'Assignation'),
        ('changement_statut', 'Changement de statut'),
        ('connexion', 'Connexion'),
        ('deconnexion', 'Déconnexion'),
    ]

    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTIONS)
    modele = models.CharField(max_length=50, blank=True)
    objet_id = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    adresse_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    date_action = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Journal d'activité"
        verbose_name_plural = "Journal d'activités"
        ordering = ['-date_action']

    def __str__(self):
        return f"{self.action} - {self.utilisateur} - {self.date_action}"

class Parametres(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    valeur = models.TextField()
    description = models.TextField(blank=True)
    type_valeur = models.CharField(
        max_length=20,
        choices=[
            ('string', 'Chaîne'),
            ('integer', 'Entier'),
            ('float', 'Décimal'),
            ('boolean', 'Booléen'),
            ('json', 'JSON'),
        ],
        default='string'
    )
    modifiable = models.BooleanField(default=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Paramètre"
        verbose_name_plural = "Paramètres"

    def __str__(self):
        return self.nom

    def get_valeur(self):
        if self.type_valeur == 'integer':
            return int(self.valeur)
        elif self.type_valeur == 'float':
            return float(self.valeur)
        elif self.type_valeur == 'boolean':
            return self.valeur.lower() == 'true'
        elif self.type_valeur == 'json':
            import json
            return json.loads(self.valeur)
        return self.valeur