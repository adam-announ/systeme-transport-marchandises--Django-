# transport/admin.py
from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import Client, Transporteur, Commande, Adresse, BonLivraison, Itineraire

# Configuration personnalisée de l'admin
admin.site.site_header = "Administration - Système de Transport"
admin.site.site_title = "Admin Transport"
admin.site.index_title = "Gestion du Système de Transport"

# Admin pour les Adresses
@admin.register(Adresse)
class AdresseAdmin(admin.ModelAdmin):
    list_display = ['rue', 'ville', 'code_postal', 'pays']
    list_filter = ['ville', 'pays']
    search_fields = ['rue', 'ville', 'code_postal']

# Admin pour les Clients
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['user', 'telephone', 'adresse', 'nombre_commandes']
    search_fields = ['user__username', 'user__email', 'telephone']
    
    def nombre_commandes(self, obj):
        return obj.commande_set.count()
    nombre_commandes.short_description = 'Nombre de commandes'

# Admin pour les Transporteurs
@admin.register(Transporteur)
class TransporteurAdmin(admin.ModelAdmin):
    list_display = ['matricule', 'type_vehicule', 'capacite_charge', 'disponible', 'statut_badge']
    list_filter = ['disponible', 'type_vehicule']
    search_fields = ['matricule']
    actions = ['marquer_disponible', 'marquer_indisponible']
    
    def statut_badge(self, obj):
        if obj.disponible:
            return format_html('<span style="color: green;">✓ Disponible</span>')
        return format_html('<span style="color: red;">✗ Indisponible</span>')
    statut_badge.short_description = 'Statut'
    
    def marquer_disponible(self, request, queryset):
        queryset.update(disponible=True)
    marquer_disponible.short_description = "Marquer comme disponible"
    
    def marquer_indisponible(self, request, queryset):
        queryset.update(disponible=False)
    marquer_indisponible.short_description = "Marquer comme indisponible"

# Admin pour les Commandes
@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ['id', 'client', 'date_creation', 'type_marchandise', 'poids', 'statut_colore', 'transporteur']
    list_filter = ['statut', 'date_creation', 'transporteur']
    search_fields = ['id', 'client__user__username', 'type_marchandise']
    date_hierarchy = 'date_creation'
    readonly_fields = ['date_creation']
    
    fieldsets = (
        ('Informations Client', {
            'fields': ('client', 'date_creation')
        }),
        ('Détails Marchandise', {
            'fields': ('type_marchandise', 'poids')
        }),
        ('Adresses', {
            'fields': ('adresse_enlevement', 'adresse_livraison')
        }),
        ('Affectation et Statut', {
            'fields': ('transporteur', 'statut')
        }),
    )
    
    def statut_colore(self, obj):
        couleurs = {
            'EN_ATTENTE': '#ffc107',
            'AFFECTEE': '#17a2b8',
            'EN_TRANSIT': '#007bff',
            'LIVREE': '#28a745',
            'ANNULEE': '#dc3545'
        }
        couleur = couleurs.get(obj.statut, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            couleur,
            obj.get_statut_display()
        )
    statut_colore.short_description = 'Statut'

# Admin pour les Bons de Livraison
@admin.register(BonLivraison)
class BonLivraisonAdmin(admin.ModelAdmin):
    list_display = ['id', 'commande', 'transporteur', 'date_creation', 'statut']
    list_filter = ['date_creation', 'statut']
    date_hierarchy = 'date_creation'

# Admin pour les Itinéraires
@admin.register(Itineraire)
class ItineraireAdmin(admin.ModelAdmin):
    list_display = ['point_depart', 'point_arrivee', 'distance', 'temps_estime_format']
    list_filter = ['distance']
    
    def temps_estime_format(self, obj):
        heures = obj.temps_estime // 60
        minutes = obj.temps_estime % 60
        return f"{heures}h {minutes}min"
    temps_estime_format.short_description = 'Temps estimé'
