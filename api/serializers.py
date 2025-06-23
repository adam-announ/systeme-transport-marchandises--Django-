# api/serializers.py - Serializers optimisés

from rest_framework import serializers
from transport.models import (
    Client, Transporteur, Adresse, Commande, 
    MissionTransporteur, Incident, Notification
)

class AdresseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Adresse
        fields = ['id', 'rue', 'ville', 'code_postal', 'pays', 'latitude', 'longitude']

class ClientSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    nombre_commandes = serializers.ReadOnlyField()
    
    class Meta:
        model = Client
        fields = ['id', 'username', 'email', 'telephone', 'adresse', 'nombre_commandes', 'actif']

class TransporteurSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    taux_reussite = serializers.ReadOnlyField()
    
    class Meta:
        model = Transporteur
        fields = [
            'id', 'username', 'email', 'matricule', 'type_vehicule',
            'capacite_charge', 'disponible', 'note_moyenne', 'taux_reussite',
            'latitude_actuelle', 'longitude_actuelle', 'derniere_maj_position'
        ]

class CommandeSerializer(serializers.ModelSerializer):
    client = serializers.StringRelatedField(read_only=True)
    transporteur = serializers.StringRelatedField(read_only=True)
    adresse_enlevement = AdresseSerializer(read_only=True)
    adresse_livraison = AdresseSerializer(read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    priorite_display = serializers.CharField(source='get_priorite_display', read_only=True)
    est_urgente = serializers.ReadOnlyField()
    
    class Meta:
        model = Commande
        fields = [
            'id', 'client', 'date_creation', 'statut', 'statut_display',
            'poids', 'type_marchandise', 'adresse_enlevement', 'adresse_livraison',
            'transporteur', 'priorite', 'priorite_display', 'prix_estime',
            'instructions_speciales', 'est_urgente'
        ]

class MissionSerializer(serializers.ModelSerializer):
    transporteur = TransporteurSerializer(read_only=True)
    commande = CommandeSerializer(read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    duree_totale = serializers.ReadOnlyField()
    
    class Meta:
        model = MissionTransporteur
        fields = [
            'id', 'commande', 'transporteur', 'date_assignation',
            'date_debut', 'date_fin', 'statut', 'statut_display',
            'itineraire_optimise', 'distance_parcourue', 'duree_totale'
        ]

class IncidentSerializer(serializers.ModelSerializer):
    mission = serializers.PrimaryKeyRelatedField(read_only=True)
    transporteur = serializers.StringRelatedField(read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = Incident
        fields = [
            'id', 'mission', 'transporteur', 'type', 'type_display',
            'description', 'date_signalement', 'photo', 'resolu'
        ]
        read_only_fields = ['date_signalement', 'transporteur']

class NotificationSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    priorite_display = serializers.CharField(source='get_priorite_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'type', 'type_display', 'titre', 'message',
            'date_creation', 'lu', 'commande', 'priorite', 'priorite_display'
        ]
        read_only_fields = ['type', 'titre', 'message', 'date_creation', 'commande', 'priorite']
