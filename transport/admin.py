from django.contrib import admin
from .models import *

@admin.register(Adresse)
class AdresseAdmin(admin.ModelAdmin):
    list_display = ['rue', 'ville', 'code_postal', 'pays']
    list_filter = ['ville', 'pays']
    search_fields = ['rue', 'ville', 'code_postal']

@admin.register(Utilisateur)
class UtilisateurAdmin(admin.ModelAdmin):
    list_display = ['nom', 'prenom', 'email', 'role']
    list_filter = ['role']
    search_fields = ['nom', 'prenom', 'email']
    readonly_fields = ['user']

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['nom', 'prenom', 'email', 'telephone']
    search_fields = ['nom', 'prenom', 'email', 'telephone']

@admin.register(Transporteur)
class TransporteurAdmin(admin.ModelAdmin):
    list_display = ['matricule', 'type_vehicule', 'capacite_charge', 'disponibilite', 'get_nom']
    list_filter = ['type_vehicule', 'disponibilite']
    search_fields = ['matricule', 'utilisateur__nom']
    
    def get_nom(self, obj):
        return f"{obj.utilisateur.prenom} {obj.utilisateur.nom}"
    get_nom.short_description = 'Nom'

@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ['id', 'type_marchandise', 'poids', 'statut', 'date_creation', 'get_client', 'get_transporteur']
    list_filter = ['statut', 'type_marchandise', 'date_creation']
    search_fields = ['id', 'type_marchandise', 'client__nom']
    readonly_fields = ['date_creation']
    
    def get_client(self, obj):
        return f"{obj.client.prenom} {obj.client.nom}"
    get_client.short_description = 'Client'
    
    def get_transporteur(self, obj):
        if obj.transporteur:
            return f"{obj.transporteur.utilisateur.prenom} {obj.transporteur.utilisateur.nom}"
        return "Non assigné"
    get_transporteur.short_description = 'Transporteur'

@admin.register(Itineraire)
class ItineraireAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_commande', 'distance', 'temps_estime']
    search_fields = ['commande__id']
    
    def get_commande(self, obj):
        return f"Commande #{obj.commande.id}"
    get_commande.short_description = 'Commande'

@admin.register(BonLivraison)
class BonLivraisonAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_commande', 'statut', 'date_creation']
    list_filter = ['statut', 'date_creation']
    readonly_fields = ['date_creation']
    
    def get_commande(self, obj):
        return f"Commande #{obj.commande.id}"
    get_commande.short_description = 'Commande'

@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = ['action', 'utilisateur', 'date_action']
    list_filter = ['utilisateur', 'date_action']
    search_fields = ['action', 'utilisateur', 'details']
    readonly_fields = ['date_action']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['type', 'destinataire', 'date_creation', 'get_transporteur']
    list_filter = ['type', 'date_creation']
    search_fields = ['contenu', 'destinataire']
    readonly_fields = ['date_creation']
    
    def get_transporteur(self, obj):
        if obj.transporteur:
            return f"{obj.transporteur.utilisateur.prenom} {obj.transporteur.utilisateur.nom}"
        return "N/A"
    get_transporteur.short_description = 'Transporteur'

@admin.register(DonneesTrafic)
class DonneesTraficAdmin(admin.ModelAdmin):
    list_display = ['localisation', 'intensite', 'type_incident', 'timestamp']
    list_filter = ['intensite', 'type_incident', 'timestamp']
    search_fields = ['localisation', 'type_incident']
    readonly_fields = ['timestamp']

@admin.register(DonneesMeteo)
class DonneesMeteoAdmin(admin.ModelAdmin):
    list_display = ['localisation', 'temperature', 'conditions_meteo', 'timestamp']
    list_filter = ['conditions_meteo', 'timestamp']
    search_fields = ['localisation', 'conditions_meteo']
    readonly_fields = ['timestamp']

# Configuration générale de l'interface admin
admin.site.site_header = "Administration TransportPro"
admin.site.site_title = "TransportPro Admin"
admin.site.index_title = "Panneau d'administration"