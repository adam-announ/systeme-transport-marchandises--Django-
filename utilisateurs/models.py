from django.db import models
from django.contrib.auth.hashers import make_password

class User(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('driver', 'Driver'),
        ('client', 'Client'),
        ('transporteur', 'Transporteur'),
    ]

    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=50, unique=True)
    email = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=15, choices=ROLE_CHOICES)
    first_name = models.CharField(max_length=50, null=True, blank=True)
    last_name = models.CharField(max_length=50, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        managed = False  
        db_table = 'users'  

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def get_role_display(self):
        return dict(self.ROLE_CHOICES).get(self.role, self.role)

    def __str__(self):
        return self.username

class Commande(models.Model):
    STATUS_CHOICES = [
        ('en_attente', 'En attente'),
        ('affectee', 'Affectée'),
        ('en_cours', 'En cours'),
        ('livree', 'Livrée'),
        ('annulee', 'Annulée'),
    ]
    
    id = models.AutoField(primary_key=True)
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commandes_client')
    transporteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commandes_transporteur', null=True, blank=True)
    origine = models.CharField(max_length=200)
    destination = models.CharField(max_length=200)
    description_marchandise = models.TextField()
    poids = models.DecimalField(max_digits=10, decimal_places=2)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_livraison_prevue = models.DateTimeField()
    statut = models.CharField(max_length=20, choices=STATUS_CHOICES, default='en_attente')
    prix = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        managed = False
        db_table = 'commandes'
    
    def __str__(self):
        return f"Commande #{self.id} - {self.origine} vers {self.destination}"

class Vehicule(models.Model):
    TYPE_CHOICES = [
        ('camionnette', 'Camionnette'),
        ('camion', 'Camion'),
        ('semi_remorque', 'Semi-remorque'),
    ]
    
    id = models.AutoField(primary_key=True)
    transporteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicules')
    immatriculation = models.CharField(max_length=20, unique=True)
    type_vehicule = models.CharField(max_length=20, choices=TYPE_CHOICES)
    capacite_max = models.DecimalField(max_digits=10, decimal_places=2)
    disponible = models.BooleanField(default=True)
    
    class Meta:
        managed = False
        db_table = 'vehicules'
    
    def __str__(self):
        return f"{self.immatriculation} - {self.get_type_vehicule_display()}"

class Livraison(models.Model):
    STATUS_CHOICES = [
        ('en_attente', 'En attente'),
        ('en_cours', 'En cours'),
        ('livree', 'Livrée'),
        ('incident', 'Incident'),
    ]
    
    id = models.AutoField(primary_key=True)
    commande = models.OneToOneField(Commande, on_delete=models.CASCADE)
    vehicule = models.ForeignKey(Vehicule, on_delete=models.CASCADE)
    statut = models.CharField(max_length=20, choices=STATUS_CHOICES, default='en_attente')
    position_actuelle = models.CharField(max_length=200, blank=True)
    date_debut = models.DateTimeField(null=True, blank=True)
    date_fin = models.DateTimeField(null=True, blank=True)
    notes_livraison = models.TextField(blank=True)
    
    class Meta:
        managed = False
        db_table = 'livraisons'
    
    def __str__(self):
        return f"Livraison #{self.id} - Commande #{self.commande.id}"

class Notification(models.Model):
    TYPE_CHOICES = [
        ('nouvelle_commande', 'Nouvelle commande'),
        ('commande_affectee', 'Commande affectée'),
        ('statut_livraison', 'Statut livraison'),
        ('incident', 'Incident'),
    ]
    
    id = models.AutoField(primary_key=True)
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type_notification = models.CharField(max_length=30, choices=TYPE_CHOICES)
    titre = models.CharField(max_length=200)
    message = models.TextField()
    lu = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        managed = False
        db_table = 'notifications'
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"{self.titre} - {self.utilisateur.username}"