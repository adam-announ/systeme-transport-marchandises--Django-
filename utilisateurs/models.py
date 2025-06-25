from django.db import models
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class User(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('client', 'Client'),
        ('transporteur', 'Transporteur'),
        ('planificateur', 'Planificateur')
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
        managed = True
        db_table = 'users'

    def save(self, *args, **kwargs):
        # Hasher le mot de passe si ce n'est pas déjà fait
        if self.password and not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def get_role_display(self):
        return dict(self.ROLE_CHOICES).get(self.role, self.role)
    
    def get_full_name(self):
        """Retourne le nom complet de l'utilisateur"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    def __str__(self):
        return self.username

class Commande(models.Model):
    STATUS_CHOICES = [
        ('en_attente', 'En attente'),
        ('affectee', 'Affectée'),
        ('planifiee', 'Planifiée'),  # Nouveau statut
        ('en_cours', 'En cours'),
        ('livree', 'Livrée'),
        ('annulee', 'Annulée'),
    ]
    
    PRIORITY_CHOICES = [
        ('basse', 'Basse'),
        ('normale', 'Normale'),
        ('haute', 'Haute'),
        ('urgente', 'Urgente'),
    ]
    
    id = models.AutoField(primary_key=True)
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commandes_client')
    transporteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commandes_transporteur', null=True, blank=True)
    planificateur = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='commandes_planifiees', null=True, blank=True)  # Nouveau champ
    origine = models.CharField(max_length=200)
    destination = models.CharField(max_length=200)
    description_marchandise = models.TextField()
    poids = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    date_creation = models.DateTimeField(auto_now_add=True)
    date_livraison_prevue = models.DateTimeField()
    date_livraison_planifiee = models.DateTimeField(null=True, blank=True)  # Nouveau champ pour la planification
    statut = models.CharField(max_length=20, choices=STATUS_CHOICES, default='en_attente')
    priorite = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normale')  # Nouveau champ
    prix = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    distance_estimee = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)  # En km
    duree_estimee = models.DurationField(null=True, blank=True)  # Durée estimée du transport
    
    class Meta:
        managed = True
        db_table = 'commandes'
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['statut', 'date_creation']),
            models.Index(fields=['transporteur', 'statut']),
            models.Index(fields=['planificateur', 'statut']),
        ]
    
    def get_statut_display(self):
        return dict(self.STATUS_CHOICES).get(self.statut, self.statut)
    
    def get_priorite_display(self):
        return dict(self.PRIORITY_CHOICES).get(self.priorite, self.priorite)
    
    def is_modifiable(self):
        """Vérifie si la commande peut encore être modifiée"""
        return self.statut in ['en_attente', 'affectee', 'planifiee']
    
    def is_cancellable(self):
        """Vérifie si la commande peut être annulée"""
        return self.statut in ['en_attente', 'affectee', 'planifiee']
    
    def is_urgent(self):
        """Vérifie si la commande est urgente"""
        return self.priorite == 'urgente'
    
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
    capacite_max = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    disponible = models.BooleanField(default=True)
    # Champs supplémentaires optionnels
    marque = models.CharField(max_length=50, blank=True, null=True)
    modele = models.CharField(max_length=50, blank=True, null=True)
    annee = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(1900), MaxValueValidator(2030)])
    couleur = models.CharField(max_length=30, blank=True, null=True)
    notes = models.TextField(blank=True)
    date_ajout = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        managed = True
        db_table = 'vehicules'
        ordering = ['-date_ajout']
    
    def get_type_vehicule_display(self):
        return dict(self.TYPE_CHOICES).get(self.type_vehicule, self.type_vehicule)
    
    def is_available_for_weight(self, poids):
        """Vérifie si le véhicule peut transporter le poids donné"""
        return self.disponible and float(poids) <= float(self.capacite_max)
    
    def is_available_for_date(self, date_debut, date_fin):
        """Vérifie si le véhicule est disponible pour une période donnée"""
        if not self.disponible:
            return False
        
        # Vérifier les tournées en conflit
        tournees_conflits = Tournee.objects.filter(
            vehicule=self,
            statut__in=['planifiee', 'en_cours'],
            date_debut_prevue__lt=date_fin,
            date_fin_prevue__gt=date_debut
        )
        
        return not tournees_conflits.exists()
    
    def get_current_livraison(self):
        """Retourne la livraison en cours pour ce véhicule"""
        try:
            return self.livraisons.get(statut__in=['en_attente', 'en_cours'])
        except Livraison.DoesNotExist:
            return None
    
    @property
    def total_livraisons(self):
        """Retourne le nombre total de livraisons effectuées"""
        return self.livraisons.filter(statut='livree').count()
    
    @property
    def km_parcourus(self):
        """Retourne le nombre de km parcourus (simulé)"""
        return self.total_livraisons * 50  # Simulation: 50km par livraison
    
    @property
    def note_moyenne(self):
        """Retourne la note moyenne (à implémenter selon votre système)"""
        return 4.2 if self.total_livraisons > 0 else None
    
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
    commande = models.OneToOneField(Commande, on_delete=models.CASCADE, related_name='livraison')
    vehicule = models.ForeignKey(Vehicule, on_delete=models.CASCADE, related_name='livraisons')
    tournee = models.ForeignKey('Tournee', on_delete=models.SET_NULL, related_name='livraisons', null=True, blank=True)
    statut = models.CharField(max_length=20, choices=STATUS_CHOICES, default='en_attente')
    position_actuelle = models.CharField(max_length=200, blank=True)
    latitude_actuelle = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)  # Nouveau champ
    longitude_actuelle = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)  # Nouveau champ
    date_debut = models.DateTimeField(null=True, blank=True)
    date_fin = models.DateTimeField(null=True, blank=True)
    notes_livraison = models.TextField(blank=True)
    
    class Meta:
        managed = True
        db_table = 'livraisons'
        ordering = ['-commande__date_creation']
    
    def get_statut_display(self):
        return dict(self.STATUS_CHOICES).get(self.statut, self.statut)
    
    def save(self, *args, **kwargs):
        # Mettre à jour automatiquement les dates selon le statut
        if self.statut == 'en_cours' and not self.date_debut:
            self.date_debut = timezone.now()
        elif self.statut == 'livree' and not self.date_fin:
            self.date_fin = timezone.now()
            # Mettre à jour le statut de la commande
            self.commande.statut = 'livree'
            self.commande.save()
        
        # Mettre à jour la disponibilité du véhicule
        if self.statut in ['livree', 'incident']:
            self.vehicule.disponible = True
            self.vehicule.save()
        elif self.statut in ['en_attente', 'en_cours']:
            self.vehicule.disponible = False
            self.vehicule.save()
        
        super().save(*args, **kwargs)
    
    @property
    def duree_livraison(self):
        """Retourne la durée de livraison si terminée"""
        if self.date_debut and self.date_fin:
            return self.date_fin - self.date_debut
        return None
    
    @property
    def is_en_retard(self):
        """Vérifie si la livraison est en retard"""
        if self.statut != 'livree':
            return timezone.now() > self.commande.date_livraison_prevue
        return self.date_fin > self.commande.date_livraison_prevue if self.date_fin else False
    
    def __str__(self):
        return f"Livraison #{self.id} - Commande #{self.commande.id}"

class Notification(models.Model):
    TYPE_CHOICES = [
        ('nouvelle_commande', 'Nouvelle commande'),
        ('commande_affectee', 'Commande affectée'),
        ('commande_planifiee', 'Commande planifiée'),  # Nouveau type
        ('tournee_creee', 'Tournée créée'),  # Nouveau type
        ('statut_livraison', 'Statut livraison'),
        ('incident', 'Incident'),
        ('system', 'Système'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Basse'),
        ('normal', 'Normale'),
        ('high', 'Haute'),
        ('urgent', 'Urgente'),
    ]
    
    id = models.AutoField(primary_key=True)
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type_notification = models.CharField(max_length=30, choices=TYPE_CHOICES)
    titre = models.CharField(max_length=200)
    message = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    lu = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_lecture = models.DateTimeField(null=True, blank=True)
    # Liens optionnels
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    livraison = models.ForeignKey(Livraison, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    tournee = models.ForeignKey('Tournee', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    
    class Meta:
        managed = True
        db_table = 'notifications'
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['utilisateur', '-date_creation']),
            models.Index(fields=['lu', '-date_creation']),
        ]
    
    def get_type_notification_display(self):
        return dict(self.TYPE_CHOICES).get(self.type_notification, self.type_notification)
    
    def get_priority_display(self):
        return dict(self.PRIORITY_CHOICES).get(self.priority, self.priority)
    
    def mark_as_read(self):
        """Marque la notification comme lue"""
        if not self.lu:
            self.lu = True
            self.date_lecture = timezone.now()
            self.save(update_fields=['lu', 'date_lecture'])
    
    @property
    def is_recent(self):
        """Vérifie si la notification est récente (moins de 24h)"""
        return (timezone.now() - self.date_creation).days < 1
    
    def __str__(self):
        return f"{self.titre} - {self.utilisateur.username}"

# Modèle pour l'historique des actions (optionnel)
class HistoriqueAction(models.Model):
    ACTION_CHOICES = [
        ('create', 'Création'),
        ('update', 'Modification'),
        ('delete', 'Suppression'),
        ('status_change', 'Changement de statut'),
        ('assignment', 'Affectation'),
        ('planning', 'Planification'),  # Nouveau type d'action
    ]
    
    id = models.AutoField(primary_key=True)
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='actions')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    description = models.TextField()
    table_name = models.CharField(max_length=50)  # Nom de la table concernée
    record_id = models.IntegerField()  # ID de l'enregistrement concerné
    ancien_valeur = models.JSONField(null=True, blank=True)  # Ancienne valeur (JSON)
    nouvelle_valeur = models.JSONField(null=True, blank=True)  # Nouvelle valeur (JSON)
    date_action = models.DateTimeField(auto_now_add=True)
    adresse_ip = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        managed = True
        db_table = 'historique_actions'
        ordering = ['-date_action']
        indexes = [
            models.Index(fields=['utilisateur', '-date_action']),
            models.Index(fields=['table_name', 'record_id']),
        ]
    
    def get_action_display(self):
        return dict(self.ACTION_CHOICES).get(self.action, self.action)
    
    def __str__(self):
        return f"{self.utilisateur.username} - {self.get_action_display()} - {self.date_action}"

# Modèle pour les paramètres système (optionnel)
class ParametreSysteme(models.Model):
    TYPE_CHOICES = [
        ('string', 'Chaîne de caractères'),
        ('integer', 'Nombre entier'),
        ('float', 'Nombre décimal'),
        ('boolean', 'Booléen'),
        ('json', 'JSON'),
    ]
    
    id = models.AutoField(primary_key=True)
    cle = models.CharField(max_length=100, unique=True)
    valeur = models.TextField()
    type_valeur = models.CharField(max_length=10, choices=TYPE_CHOICES, default='string')
    description = models.TextField(blank=True)
    modifiable = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        managed = True
        db_table = 'parametres_systeme'
        ordering = ['cle']
    
    def get_typed_value(self):
        """Retourne la valeur convertie selon son type"""
        if self.type_valeur == 'integer':
            return int(self.valeur)
        elif self.type_valeur == 'float':
            return float(self.valeur)
        elif self.type_valeur == 'boolean':
            return self.valeur.lower() in ['true', '1', 'yes', 'on']
        elif self.type_valeur == 'json':
            import json
            return json.loads(self.valeur)
        return self.valeur
    
    def __str__(self):
        return f"{self.cle}: {self.valeur}"

class Tournee(models.Model):
    STATUS_CHOICES = [
        ('planifiee', 'Planifiée'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
    ]
    
    id = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=200)
    planificateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tournees_planifiees')
    transporteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tournees_assignees')
    vehicule = models.ForeignKey(Vehicule, on_delete=models.CASCADE, related_name='tournees')
    statut = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planifiee')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_debut_prevue = models.DateTimeField()
    date_fin_prevue = models.DateTimeField()
    date_debut_reelle = models.DateTimeField(null=True, blank=True)
    date_fin_reelle = models.DateTimeField(null=True, blank=True)
    distance_totale = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    duree_prevue = models.DurationField(null=True, blank=True)
    duree_reelle = models.DurationField(null=True, blank=True)
    optimisee = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    
    class Meta:
        managed = True
        db_table = 'tournees'
        ordering = ['-date_creation']
    
    def get_statut_display(self):
        return dict(self.STATUS_CHOICES).get(self.statut, self.statut)
    
    @property
    def nb_etapes(self):
        return self.etapes.count()
    
    @property
    def nb_commandes(self):
        return self.etapes.filter(commande__isnull=False).values('commande').distinct().count()
    
    @property
    def poids_total(self):
        total = 0
        for etape in self.etapes.filter(commande__isnull=False):
            total += float(etape.commande.poids)
        return total
    
    def __str__(self):
        return f"Tournée {self.nom} - {self.transporteur.get_full_name()}"

class EtapeTournee(models.Model):
    TYPE_CHOICES = [
        ('depot', 'Dépôt'),
        ('collecte', 'Collecte'),
        ('livraison', 'Livraison'),
        ('pause', 'Pause'),
    ]
    
    STATUS_CHOICES = [
        ('en_attente', 'En attente'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('retard', 'En retard'),
        ('annulee', 'Annulée'),
    ]
    
    id = models.AutoField(primary_key=True)
    tournee = models.ForeignKey(Tournee, on_delete=models.CASCADE, related_name='etapes')
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, null=True, blank=True, related_name='etapes_tournee')
    ordre = models.IntegerField()
    type_etape = models.CharField(max_length=20, choices=TYPE_CHOICES)
    statut = models.CharField(max_length=20, choices=STATUS_CHOICES, default='en_attente')
    adresse = models.CharField(max_length=500)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    heure_prevue = models.DateTimeField()
    heure_arrivee = models.DateTimeField(null=True, blank=True)
    heure_depart = models.DateTimeField(null=True, blank=True)
    duree_prevue = models.DurationField()
    duree_reelle = models.DurationField(null=True, blank=True)
    distance_precedente = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        managed = True
        db_table = 'etapes_tournee'
        ordering = ['tournee', 'ordre']
        unique_together = ['tournee', 'ordre']
    
    def get_type_etape_display(self):
        return dict(self.TYPE_CHOICES).get(self.type_etape, self.type_etape)
    
    def get_statut_display(self):
        return dict(self.STATUS_CHOICES).get(self.statut, self.statut)
    
    @property
    def is_en_retard(self):
        if self.heure_arrivee:
            return self.heure_arrivee > self.heure_prevue
        return timezone.now() > self.heure_prevue if self.statut == 'en_cours' else False
    
    def __str__(self):
        return f"Étape {self.ordre} - {self.get_type_etape_display()} - {self.tournee.nom}"