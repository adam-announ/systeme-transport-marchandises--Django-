"""
Configuration de l'interface d'administration Django
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Commande, Vehicule, Itineraire, BonLivraison, Notification, JournalActivite, ConfigurationSysteme

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'actif', 'date_creation')
    list_filter = ('role', 'actif', 'date_creation')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informations supplémentaires', {
            'fields': ('role', 'telephone', 'adresse', 'actif')
        }),
    )

@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ('numero', 'client', 'transporteur', 'statut', 'date_creation')
    list_filter = ('statut', 'date_creation')
    search_fields = ('numero', 'client__username', 'transporteur__username')
    readonly_fields = ('id', 'date_creation')

@admin.register(Vehicule)
class VehiculeAdmin(admin.ModelAdmin):
    list_display = ('immatriculation', 'transporteur', 'type_vehicule', 'disponible')
    list_filter = ('type_vehicule', 'disponible')
    search_fields = ('immatriculation', 'transporteur__username')

@admin.register(Itineraire)
class ItineraireAdmin(admin.ModelAdmin):
    list_display = ('commande', 'distance_km', 'duree_minutes', 'date_creation')
    readonly_fields = ('id', 'date_creation')

@admin.register(BonLivraison)
class BonLivraisonAdmin(admin.ModelAdmin):
    list_display = ('numero_bon', 'commande', 'date_livraison', 'nom_destinataire')
    search_fields = ('numero_bon', 'commande__numero', 'nom_destinataire')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('titre', 'utilisateur', 'type_notification', 'lue', 'date_creation')
    list_filter = ('type_notification', 'lue', 'date_creation')
    search_fields = ('titre', 'utilisateur__username')

@admin.register(JournalActivite)
class JournalActiviteAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'action', 'date_action', 'adresse_ip')
    list_filter = ('date_action',)
    search_fields = ('utilisateur__username', 'action')
    readonly_fields = ('date_action',)

@admin.register(ConfigurationSysteme)
class ConfigurationSystemeAdmin(admin.ModelAdmin):
    list_display = ('cle', 'valeur', 'date_modification')
    search_fields = ('cle', 'description')