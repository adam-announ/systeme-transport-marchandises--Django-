# transport/admin.py - Version corrigée pour correspondre aux modèles optimisés

from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    Client, Transporteur, Commande, Adresse, 
    MissionTransporteur, Incident, Notification, 
    ParametreSysteme, JournalActivite
)

# Configuration personnalisée de l'admin
admin.site.site_header = "Administration - Système de Transport"
admin.site.site_title = "Admin Transport"
admin.site.index_title = "Gestion du Système de Transport"

# Admin pour les Adresses
@admin.register(Adresse)
class AdresseAdmin(admin.ModelAdmin):
    list_display = ['rue', 'ville', 'code_postal', 'pays', 'date_creation']
    list_filter = ['ville', 'pays', 'date_creation']
    search_fields = ['rue', 'ville', 'code_postal']
    readonly_fields = ['date_creation']
    
    fieldsets = (
        ('Informations Adresse', {
            'fields': ('rue', 'ville', 'code_postal', 'pays')
        }),
        ('Coordonnées GPS', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('date_creation',),
            'classes': ('collapse',)
        })
    )

# Admin pour les Clients
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['user', 'telephone', 'adresse', 'nombre_commandes', 'actif', 'date_creation']
    list_filter = ['actif', 'date_creation']
    search_fields = ['user__username', 'user__email', 'telephone', 'adresse']
    readonly_fields = ['date_creation', 'nombre_commandes']
    
    def nombre_commandes(self, obj):
        return obj.nombre_commandes
    nombre_commandes.short_description = 'Nb Commandes'
    
    fieldsets = (
        ('Utilisateur', {
            'fields': ('user',)
        }),
        ('Informations Contact', {
            'fields': ('telephone', 'adresse')
        }),
        ('Statut', {
            'fields': ('actif',)
        }),
        ('Statistiques', {
            'fields': ('nombre_commandes', 'date_creation'),
            'classes': ('collapse',)
        })
    )

# Admin pour les Transporteurs
@admin.register(Transporteur)
class TransporteurAdmin(admin.ModelAdmin):
    list_display = [
        'matricule', 'user', 'type_vehicule', 'capacite_charge', 
        'disponible', 'statut_badge', 'note_moyenne', 'taux_reussite'
    ]
    list_filter = ['disponible', 'actif', 'type_vehicule', 'date_creation']
    search_fields = ['matricule', 'user__username', 'user__email']
    readonly_fields = ['date_creation', 'taux_reussite', 'derniere_maj_position']
    actions = ['marquer_disponible', 'marquer_indisponible']
    
    def statut_badge(self, obj):
        if obj.disponible and obj.actif:
            return format_html('<span style="color: green;">✓ Disponible</span>')
        elif obj.actif:
            return format_html('<span style="color: orange;">⏸ Occupé</span>')
        else:
            return format_html('<span style="color: red;">✗ Inactif</span>')
    statut_badge.short_description = 'Statut'
    
    def marquer_disponible(self, request, queryset):
        updated = queryset.update(disponible=True)
        self.message_user(request, f'{updated} transporteur(s) marqué(s) comme disponible(s).')
    marquer_disponible.short_description = "Marquer comme disponible"
    
    def marquer_indisponible(self, request, queryset):
        updated = queryset.update(disponible=False)
        self.message_user(request, f'{updated} transporteur(s) marqué(s) comme indisponible(s).')
    marquer_indisponible.short_description = "Marquer comme indisponible"
    
    fieldsets = (
        ('Utilisateur', {
            'fields': ('user',)
        }),
        ('Véhicule', {
            'fields': ('matricule', 'type_vehicule', 'capacite_charge')
        }),
        ('Statut', {
            'fields': ('disponible', 'actif')
        }),
        ('Performance', {
            'fields': ('note_moyenne', 'taux_reussite'),
            'classes': ('collapse',)
        }),
        ('Position', {
            'fields': ('latitude_actuelle', 'longitude_actuelle', 'derniere_maj_position'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('date_creation',),
            'classes': ('collapse',)
        })
    )

# Admin pour les Commandes
@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'client', 'date_creation', 'type_marchandise', 
        'poids', 'statut_colore', 'transporteur', 'priorite_badge'
    ]
    list_filter = ['statut', 'priorite', 'date_creation']
    search_fields = ['id', 'client__user__username', 'type_marchandise']
    date_hierarchy = 'date_creation'
    readonly_fields = ['date_creation']
    
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
    
    def priorite_badge(self, obj):
        couleurs = {0: '#6c757d', 1: '#ffc107', 2: '#dc3545'}
        couleur = couleurs.get(obj.priorite, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            couleur,
            obj.get_priorite_display()
        )
    priorite_badge.short_description = 'Priorité'
    
    fieldsets = (
        ('Informations Client', {
            'fields': ('client', 'date_creation')
        }),
        ('Détails Marchandise', {
            'fields': ('type_marchandise', 'poids', 'priorite')
        }),
        ('Adresses', {
            'fields': ('adresse_enlevement', 'adresse_livraison')
        }),
        ('Affectation et Statut', {
            'fields': ('transporteur', 'statut')
        }),
        ('Détails Supplémentaires', {
            'fields': ('prix_estime', 'instructions_speciales'),
            'classes': ('collapse',)
        })
    )

# Admin pour les Missions
@admin.register(MissionTransporteur)
class MissionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'commande', 'transporteur', 'date_assignation', 
        'statut_colore', 'distance_parcourue'
    ]
    list_filter = ['statut', 'date_assignation']
    search_fields = ['commande__id', 'transporteur__matricule', 'transporteur__user__username']
    readonly_fields = ['date_assignation', 'duree_totale']
    date_hierarchy = 'date_assignation'
    
    def statut_colore(self, obj):
        couleurs = {
            'ASSIGNEE': '#6c757d',
            'ACCEPTEE': '#17a2b8',
            'EN_COURS': '#007bff',
            'TERMINEE': '#28a745',
            'ANNULEE': '#dc3545'
        }
        couleur = couleurs.get(obj.statut, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            couleur,
            obj.get_statut_display()
        )
    statut_colore.short_description = 'Statut'
    
    fieldsets = (
        ('Mission', {
            'fields': ('commande', 'transporteur', 'statut')
        }),
        ('Dates', {
            'fields': ('date_assignation', 'date_acceptation', 'date_debut', 'date_fin', 'duree_totale')
        }),
        ('Itinéraire', {
            'fields': ('itineraire_optimise', 'distance_parcourue'),
            'classes': ('collapse',)
        })
    )

# Admin pour les Incidents
@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'mission', 'transporteur', 'type', 
        'date_signalement', 'resolu_badge'
    ]
    list_filter = ['type', 'resolu', 'date_signalement']
    search_fields = ['mission__commande__id', 'transporteur__matricule', 'description']
    readonly_fields = ['date_signalement']
    actions = ['marquer_resolu']
    
    def resolu_badge(self, obj):
        if obj.resolu:
            return format_html('<span style="color: green;">✓ Résolu</span>')
        else:
            return format_html('<span style="color: red;">⚠ En cours</span>')
    resolu_badge.short_description = 'Résolu'
    
    def marquer_resolu(self, request, queryset):
        updated = queryset.update(resolu=True, date_resolution=timezone.now())
        self.message_user(request, f'{updated} incident(s) marqué(s) comme résolu(s).')
    marquer_resolu.short_description = "Marquer comme résolu"
    
    fieldsets = (
        ('Incident', {
            'fields': ('mission', 'transporteur', 'type')
        }),
        ('Description', {
            'fields': ('description', 'photo')
        }),
        ('Résolution', {
            'fields': ('resolu', 'date_signalement', 'date_resolution'),
            'classes': ('collapse',)
        })
    )

# Admin pour les Notifications
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'destinataire', 'type', 'titre', 
        'date_creation', 'lu_badge', 'priorite'
    ]
    list_filter = ['type', 'lu', 'priorite', 'date_creation']
    search_fields = ['destinataire__username', 'titre', 'message']
    readonly_fields = ['date_creation']
    actions = ['marquer_comme_lue']
    
    def lu_badge(self, obj):
        if obj.lu:
            return format_html('<span style="color: green;">✓ Lu</span>')
        else:
            return format_html('<span style="color: orange;">⚪ Non lu</span>')
    lu_badge.short_description = 'Statut'
    
    def marquer_comme_lue(self, request, queryset):
        updated = queryset.update(lu=True)
        self.message_user(request, f'{updated} notification(s) marquée(s) comme lue(s).')
    marquer_comme_lue.short_description = "Marquer comme lue"

# Admin pour les Paramètres Système
@admin.register(ParametreSysteme)
class ParametreSystemeAdmin(admin.ModelAdmin):
    list_display = ['nom', 'valeur', 'type', 'modifiable']
    list_filter = ['type', 'modifiable']
    search_fields = ['nom', 'description']
    
    def get_readonly_fields(self, request, obj=None):
        if obj and not obj.modifiable:
            return ['nom', 'valeur', 'type', 'modifiable']
        return ['modifiable'] if obj else []

# Admin pour le Journal d'Activité
@admin.register(JournalActivite)
class JournalActiviteAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'utilisateur', 'action', 'objet_type', 
        'date', 'ip_address'
    ]
    list_filter = ['action', 'objet_type', 'date']
    search_fields = ['utilisateur__username', 'details', 'ip_address']
    readonly_fields = ['date']
    date_hierarchy = 'date'
    
    def has_add_permission(self, request):
        return False  # Pas d'ajout manuel
    
    def has_change_permission(self, request, obj=None):
        return False  # Pas de modification