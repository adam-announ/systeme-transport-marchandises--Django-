# transport/models.py - Version corrigée avec améliorations

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

class Adresse(models.Model):
    rue = models.CharField(max_length=255, verbose_name="Rue")
    ville = models.CharField(max_length=100, verbose_name="Ville")
    code_postal = models.CharField(max_length=10, verbose_name="Code postal")
    pays = models.CharField(max_length=100, default="Maroc", verbose_name="Pays")
    latitude = models.FloatField(null=True, blank=True, verbose_name="Latitude")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Longitude")
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Adresse"
        verbose_name_plural = "Adresses"
        ordering = ['ville', 'rue']
    
    def __str__(self):
        return f"{self.rue}, {self.ville}"

class Client(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client')
    adresse = models.CharField(max_length=255, verbose_name="Adresse")
    telephone = models.CharField(max_length=20, verbose_name="Téléphone")
    date_creation = models.DateTimeField(auto_now_add=True)
    actif = models.BooleanField(default=True, verbose_name="Compte actif")
    
    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"
    
    @property
    def nombre_commandes(self):
        return self.commande_set.count()
    
    @property
    def commandes_livrees(self):
        return self.commande_set.filter(statut='LIVREE').count()

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
    matricule = models.CharField(max_length=50, unique=True, verbose_name="Matricule véhicule")
    type_vehicule = models.CharField(max_length=20, choices=TYPES_VEHICULES, verbose_name="Type de véhicule")
    capacite_charge = models.FloatField(
        validators=[MinValueValidator(0.1)], 
        verbose_name="Capacité de charge (kg)"
    )
    disponible = models.BooleanField(default=True, verbose_name="Disponible")
    latitude_actuelle = models.FloatField(null=True, blank=True, verbose_name="Latitude actuelle")
    longitude_actuelle = models.FloatField(null=True, blank=True, verbose_name="Longitude actuelle")
    derniere_maj_position = models.DateTimeField(null=True, blank=True, verbose_name="Dernière MAJ position")
    date_creation = models.DateTimeField(auto_now_add=True)
    note_moyenne = models.FloatField(
        default=5.0, 
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)],
        verbose_name="Note moyenne"
    )
    actif = models.BooleanField(default=True, verbose_name="Compte actif")
    
    class Meta:
        verbose_name = "Transporteur"
        verbose_name_plural = "Transporteurs"
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"{self.matricule} - {self.user.get_full_name() or self.user.username}"
    
    @property
    def missions_completees(self):
        return self.missiontransporteur_set.filter(statut='TERMINEE').count()
    
    @property
    def taux_reussite(self):
        total = self.missiontransporteur_set.count()
        if total == 0:
            return 100
        completees = self.missions_completees
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
    poids = models.FloatField(validators=[MinValueValidator(0.1)], verbose_name="Poids (kg)")
    type_marchandise = models.CharField(max_length=100, verbose_name="Type de marchandise")
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
        blank=True,
        verbose_name="Prix estimé"
    )
    date_livraison_souhaitee = models.DateTimeField(null=True, blank=True)
    instructions_speciales = models.TextField(blank=True, verbose_name="Instructions spéciales")
    
    class Meta:
        verbose_name = "Commande"
        verbose_name_plural = "Commandes"
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['statut']),
            models.Index(fields=['date_creation']),
            models.Index(fields=['client']),
        ]
    
    def __str__(self):
        return f"Commande #{self.id} - {self.client}"
    
    @property
    def est_urgente(self):
        return self.priorite == 2
    
    @property
    def temps_ecoule(self):
        return timezone.now() - self.date_creation

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
    distance_parcourue = models.FloatField(default=0, verbose_name="Distance parcourue (km)")
    temps_reel = models.IntegerField(null=True, blank=True, verbose_name="Temps réel (minutes)")
    note_client = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Note du client"
    )
    commentaire_client = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Mission"
        verbose_name_plural = "Missions"
        ordering = ['-date_assignation']
        unique_together = ['commande', 'transporteur']
    
    def __str__(self):
        return f"Mission #{self.id} - {self.transporteur.matricule}"
    
    @property
    def duree_totale(self):
        if self.date_debut and self.date_fin:
            return self.date_fin - self.date_debut
        return None

class BonLivraison(models.Model):
    STATUT_CHOICES = [
        ('EN_COURS', 'En cours'),
        ('SIGNE', 'Signé'),
        ('TERMINE', 'Terminé'),
    ]
    
    commande = models.OneToOneField(Commande, on_delete=models.CASCADE)
    date_creation = models.DateTimeField(auto_now_add=True)
    transporteur = models.ForeignKey(Transporteur, on_delete=models.CASCADE)
    statut = models.CharField(max_length=50, choices=STATUT_CHOICES, default='EN_COURS')
    signature_client = models.ImageField(upload_to='signatures/', null=True, blank=True)
    signature_transporteur = models.ImageField(upload_to='signatures/', null=True, blank=True)
    commentaire = models.TextField(blank=True)
    date_livraison_effective = models.DateTimeField(null=True, blank=True)
    photo_livraison = models.ImageField(upload_to='livraisons/', null=True, blank=True)
    
    class Meta:
        verbose_name = "Bon de livraison"
        verbose_name_plural = "Bons de livraison"
    
    def __str__(self):
        return f"BL #{self.id} - Commande #{self.commande.id}"

class Itineraire(models.Model):
    point_depart = models.ForeignKey(Adresse, on_delete=models.CASCADE, related_name='itineraires_depart')
    point_arrivee = models.ForeignKey(Adresse, on_delete=models.CASCADE, related_name='itineraires_arrivee')
    points_intermediaires = models.JSONField(default=list, blank=True)
    distance = models.FloatField(verbose_name="Distance (km)")
    temps_estime = models.IntegerField(verbose_name="Temps estimé (minutes)")
    type_route = models.CharField(max_length=50, default='nationale')
    polyline = models.TextField(blank=True)  # Pour stocker la polyline Google Maps
    cout_carburant = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    peages = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    class Meta:
        verbose_name = "Itinéraire"
        verbose_name_plural = "Itinéraires"
    
    def __str__(self):
        return f"{self.point_depart} → {self.point_arrivee} ({self.distance}km)"

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
    
    GRAVITE_CHOICES = [
        ('FAIBLE', 'Faible'),
        ('MOYENNE', 'Moyenne'),
        ('ELEVEE', 'Élevée'),
        ('CRITIQUE', 'Critique'),
    ]
    
    mission = models.ForeignKey(MissionTransporteur, on_delete=models.CASCADE)
    transporteur = models.ForeignKey(Transporteur, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    gravite = models.CharField(max_length=10, choices=GRAVITE_CHOICES, default='MOYENNE')
    description = models.TextField()
    date_signalement = models.DateTimeField(auto_now_add=True)
    photo = models.ImageField(upload_to='incidents/', null=True, blank=True)
    resolu = models.BooleanField(default=False)
    date_resolution = models.DateTimeField(null=True, blank=True)
    solution = models.TextField(blank=True)
    
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
        ('PROMOTION', 'Promotion'),
        ('RAPPEL', 'Rappel'),
    ]
    
    PRIORITE_CHOICES = [
        ('BASSE', 'Basse'),
        ('NORMALE', 'Normale'),
        ('HAUTE', 'Haute'),
        ('URGENTE', 'Urgente'),
    ]
    
    destinataire = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications_recues')
    transporteur = models.ForeignKey(Transporteur, on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    titre = models.CharField(max_length=200)
    message = models.TextField()
    date_creation = models.DateTimeField(auto_now_add=True)
    date_lecture = models.DateTimeField(null=True, blank=True)
    lu = models.BooleanField(default=False)
    commande = models.ForeignKey(Commande, on_delete=models.SET_NULL, null=True, blank=True)
    priorite = models.CharField(max_length=10, choices=PRIORITE_CHOICES, default='NORMALE')
    action_url = models.URLField(blank=True)  # URL vers une action spécifique
    
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
            self.date_lecture = timezone.now()
            self.save()

class DonneesMeteo(models.Model):
    CONDITION_CHOICES = [
        ('ENSOLEILLE', 'Ensoleillé'),
        ('NUAGEUX', 'Nuageux'),
        ('PLUIE', 'Pluie'),
        ('NEIGE', 'Neige'),
        ('BROUILLARD', 'Brouillard'),
        ('ORAGE', 'Orage'),
    ]
    
    zone = models.CharField(max_length=100)
    date_creation = models.DateTimeField(auto_now_add=True)
    temperature = models.FloatField(verbose_name="Température (°C)")
    conditions = models.CharField(max_length=20, choices=CONDITION_CHOICES)
    vent_vitesse = models.FloatField(verbose_name="Vitesse du vent (km/h)")
    vent_direction = models.CharField(max_length=10, blank=True)
    visibilite = models.IntegerField(verbose_name="Visibilité (m)")
    precipitation = models.FloatField(default=0, verbose_name="Précipitations (mm)")
    alerte = models.BooleanField(default=False)
    niveau_alerte = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Données météo"
        verbose_name_plural = "Données météo"
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"Météo {self.zone} - {self.get_conditions_display()}"

class DonneesTrafic(models.Model):
    NIVEAU_CHOICES = [
        ('FLUIDE', 'Fluide'),
        ('NORMAL', 'Normal'),
        ('DENSE', 'Dense'),
        ('BLOQUE', 'Bloqué'),
    ]
    
    zone = models.CharField(max_length=100)
    date_creation = models.DateTimeField(auto_now_add=True)
    niveau = models.CharField(max_length=20, choices=NIVEAU_CHOICES, default='NORMAL')
    vitesse_moyenne = models.FloatField(verbose_name="Vitesse moyenne (km/h)")
    temps_retard = models.IntegerField(default=0, verbose_name="Retard estimé (min)")
    incidents = models.JSONField(default=list, blank=True)
    routes_affectees = models.JSONField(default=list, blank=True)
    
    class Meta:
        verbose_name = "Données trafic"
        verbose_name_plural = "Données trafic"
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"Trafic {self.zone} - {self.get_niveau_display()}"

class ParametreSysteme(models.Model):
    TYPE_CHOICES = [
        ('STRING', 'Texte'),
        ('INTEGER', 'Entier'),
        ('FLOAT', 'Décimal'),
        ('BOOLEAN', 'Booléen'),
        ('JSON', 'JSON'),
    ]
    
    nom = models.CharField(max_length=100, unique=True)
    valeur = models.TextField()  # Changé en TextField pour supporter JSON
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='STRING')
    description = models.TextField(blank=True)
    categorie = models.CharField(max_length=50, default='Général')
    modifiable = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Paramètre système"
        verbose_name_plural = "Paramètres système"
        ordering = ['categorie', 'nom']
    
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

class JournalActivite(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Création'),
        ('UPDATE', 'Modification'),
        ('DELETE', 'Suppression'),
        ('LOGIN', 'Connexion'),
        ('LOGOUT', 'Déconnexion'),
        ('ASSIGN', 'Affectation'),
        ('COMPLETE', 'Finalisation'),
    ]
    
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    objet_type = models.CharField(max_length=50)  # Type d'objet modifié
    objet_id = models.PositiveIntegerField(null=True, blank=True)
    details = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Journal d'activité"
        verbose_name_plural = "Journal d'activité"
        ordering = ['-date']
        indexes = [
            models.Index(fields=['utilisateur']),
            models.Index(fields=['date']),
            models.Index(fields=['action']),
        ]
    
    def __str__(self):
        return f"{self.utilisateur} - {self.get_action_display()} - {self.date}"

class SupportMessage(models.Model):
    STATUT_CHOICES = [
        ('NOUVEAU', 'Nouveau'),
        ('EN_COURS', 'En cours'),
        ('RESOLU', 'Résolu'),
        ('FERME', 'Fermé'),
    ]
    
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages_envoyes')
    destinataire = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages_recus')
    sujet = models.CharField(max_length=200, blank=True)
    contenu = models.TextField()
    date_envoi = models.DateTimeField(auto_now_add=True)
    lu = models.BooleanField(default=False)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='NOUVEAU')
    priorite = models.CharField(max_length=10, choices=Notification.PRIORITE_CHOICES, default='NORMALE')
    piece_jointe = models.FileField(upload_to='support/', null=True, blank=True)
    
    class Meta:
        verbose_name = "Message support"
        verbose_name_plural = "Messages support"
        ordering = ['-date_envoi']
    
    def __str__(self):
        return f"Msg de {self.sender.username} à {self.destinataire.username}"

# Modèles pour les évaluations et retours
class EvaluationTransporteur(models.Model):
    mission = models.OneToOneField(MissionTransporteur, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    transporteur = models.ForeignKey(Transporteur, on_delete=models.CASCADE)
    note_ponctualite = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    note_professionnalisme = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    note_etat_marchandise = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    note_globale = models.FloatField()
    commentaire = models.TextField(blank=True)
    date_evaluation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Évaluation transporteur"
        verbose_name_plural = "Évaluations transporteurs"
    
    def save(self, *args, **kwargs):
        # Calculer la note globale
        self.note_globale = (
            self.note_ponctualite + 
            self.note_professionnalisme + 
            self.note_etat_marchandise
        ) / 3
        super().save(*args, **kwargs)
        
        # Mettre à jour la note moyenne du transporteur
        self.transporteur.note_moyenne = self.transporteur.evaluationtransporteur_set.aggregate(
            models.Avg('note_globale')
        )['note_globale__avg'] or 5.0
        self.transporteur.save()
    
    def __str__(self):
        return f"Évaluation {self.transporteur} - {self.note_globale}/5"