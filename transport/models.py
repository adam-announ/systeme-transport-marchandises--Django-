from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Adresse(models.Model):
    rue = models.CharField(max_length=200)
    ville = models.CharField(max_length=100)
    code_postal = models.CharField(max_length=10)
    pays = models.CharField(max_length=50)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return f"{self.rue}, {self.ville}"

    def valider(self):
        return self.rue and self.ville and self.code_postal

class Utilisateur(models.Model):
    ROLES = [
        ('client', 'Client'),
        ('transporteur', 'Transporteur'),
        ('planificateur', 'Planificateur'),
        ('admin', 'Admin'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField()
    mot_de_passe = models.CharField(max_length=128)
    role = models.CharField(max_length=20, choices=ROLES)
    adresse = models.ForeignKey(Adresse, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.prenom} {self.nom}"

    def se_connecter(self):
        return True

    def se_deconnecter(self):
        return True

class Client(Utilisateur):
    telephone = models.CharField(max_length=20)

    def creer_commande(self):
        pass

    def suivre_commande(self):
        pass

    def generer_rapport(self):
        pass

class Transporteur(models.Model):
    utilisateur = models.OneToOneField(Utilisateur, on_delete=models.CASCADE)
    matricule = models.CharField(max_length=50)
    type_vehicule = models.CharField(max_length=50)
    capacite_charge = models.FloatField()
    disponibilite = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.matricule} - {self.utilisateur.nom}"

    def voir_mission(self):
        pass

    def mettre_a_jour_statut_livraison(self):
        pass

    def notifier_incident(self):
        pass

class Commande(models.Model):
    STATUTS = [
        ('en_attente', 'En attente'),
        ('assignee', 'Assignée'),
        ('en_cours', 'En cours'),
        ('livree', 'Livrée'),
        ('annulee', 'Annulée'),
    ]

    id = models.AutoField(primary_key=True)
    date_creation = models.DateTimeField(default=timezone.now)
    statut = models.CharField(max_length=20, choices=STATUTS, default='en_attente')
    poids = models.FloatField()
    type_marchandise = models.CharField(max_length=100)
    adresse_enlevement = models.ForeignKey(Adresse, on_delete=models.CASCADE, related_name='commandes_enlevement')
    adresse_livraison = models.ForeignKey(Adresse, on_delete=models.CASCADE, related_name='commandes_livraison')
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    transporteur = models.ForeignKey(Transporteur, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Commande #{self.id} - {self.type_marchandise}"

    def calculer_cout(self):
        # Calcul simple basé sur le poids et la distance
        return self.poids * 10  # Prix par kg

    def generer_bon_livraison(self):
        pass

class Itineraire(models.Model):
    id = models.AutoField(primary_key=True)
    point_depart = models.ForeignKey(Adresse, on_delete=models.CASCADE, related_name='itineraires_depart')
    point_arrivee = models.ForeignKey(Adresse, on_delete=models.CASCADE, related_name='itineraires_arrivee')
    points_intermediaires = models.TextField(blank=True)  # JSON des points
    distance = models.FloatField()
    temps_estime = models.IntegerField()  # en minutes
    commande = models.OneToOneField(Commande, on_delete=models.CASCADE)

    def __str__(self):
        return f"Itinéraire {self.id}"

    def calculer_distance(self):
        # Utiliser l'API Google Maps pour calculer la distance
        pass

    def optimiser(self):
        pass

class BonLivraison(models.Model):
    id = models.AutoField(primary_key=True)
    date_creation = models.DateTimeField(default=timezone.now)
    commande = models.OneToOneField(Commande, on_delete=models.CASCADE)
    transporteur = models.ForeignKey(Transporteur, on_delete=models.CASCADE)
    statut = models.CharField(max_length=50)

    def __str__(self):
        return f"Bon #{self.id} - Commande #{self.commande.id}"

    def generer(self):
        pass

    def valider(self):
        pass

class Journal(models.Model):
    id = models.AutoField(primary_key=True)
    date_action = models.DateTimeField(default=timezone.now)
    action = models.CharField(max_length=200)
    utilisateur = models.CharField(max_length=100)
    details = models.TextField()

    def __str__(self):
        return f"{self.action} - {self.date_action}"

    def enregistrer(self):
        pass

    def consulter(self):
        pass

class Notification(models.Model):
    id = models.AutoField(primary_key=True)
    date_creation = models.DateTimeField(default=timezone.now)
    type = models.CharField(max_length=50)
    contenu = models.TextField()
    destinataire = models.CharField(max_length=100)
    transporteur = models.ForeignKey(Transporteur, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"Notification {self.type} - {self.destinataire}"

    def envoyer(self):
        pass

class DonneesTrafic(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    localisation = models.CharField(max_length=200)
    intensite = models.CharField(max_length=50)
    type_incident = models.CharField(max_length=100)

    def __str__(self):
        return f"Trafic {self.localisation} - {self.intensite}"

    def fournir_infos_trafic(self):
        pass

class DonneesMeteo(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    localisation = models.CharField(max_length=200)
    temperature = models.FloatField()
    conditions_meteo = models.CharField(max_length=100)
    precipitation = models.FloatField()

    def __str__(self):
        return f"Météo {self.localisation} - {self.temperature}°C"

    def fournir_previsions(self):
        pass

class Admin(Utilisateur):
    def configurer_parametres_systeme(self):
        pass

    def consulter_journal_activite(self):
        pass

    def gerer_roles(self):
        pass

    def gerer_utilisateurs(self):
        pass

    def envoyer_notifications(self):
        pass

class Planificateur(Utilisateur):
    def affecter_commande_transporteur(self):
        pass

    def optimiser_itineraire(self):
        pass