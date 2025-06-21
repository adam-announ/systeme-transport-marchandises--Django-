from rest_framework import serializers
from transport.models import Client, Transporteur, Adresse, Commande, MissionTransporteur, Incident, Notification

class AdresseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Adresse
        fields = ['id', 'rue', 'ville', 'code_postal', 'pays', 'latitude', 'longitude']

class ClientSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    class Meta:
        model = Client
        fields = ['id', 'username', 'email', 'adresse', 'telephone']

class TransporteurSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    class Meta:
        model = Transporteur
        fields = ['id', 'username', 'email', 'matricule', 'type_vehicule', 'capacite_charge', 'disponible', 'latitude_actuelle', 'longitude_actuelle', 'derniere_maj_position']

class CommandeSerializer(serializers.ModelSerializer):
    client = serializers.StringRelatedField()  # affiche Client.__str__ (username)
    transporteur = serializers.StringRelatedField(allow_null=True)
    adresse_enlevement = AdresseSerializer()
    adresse_livraison = AdresseSerializer()
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    class Meta:
        model = Commande
        fields = ['id', 'client', 'date_creation', 'statut', 'statut_display', 'poids', 'type_marchandise',
                  'adresse_enlevement', 'adresse_livraison', 'transporteur', 'priorite']

class MissionSerializer(serializers.ModelSerializer):
    transporteur = serializers.StringRelatedField()
    commande = serializers.PrimaryKeyRelatedField(read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    class Meta:
        model = MissionTransporteur
        fields = ['id', 'commande', 'transporteur', 'date_assignation', 'date_debut', 'date_fin', 'statut', 'statut_display', 'itineraire_optimise', 'distance_parcourue']

class IncidentSerializer(serializers.ModelSerializer):
    mission = serializers.PrimaryKeyRelatedField(queryset=MissionTransporteur.objects.all())
    transporteur = serializers.StringRelatedField(read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    class Meta:
        model = Incident
        fields = ['id', 'mission', 'transporteur', 'type', 'type_display', 'description', 'date_signalement', 'photo', 'resolu']
        read_only_fields = ['date_signalement', 'transporteur', 'resolu']

class NotificationSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    priorite = serializers.CharField(read_only=True)
    class Meta:
        model = Notification
        fields = ['id', 'type', 'type_display', 'titre', 'message', 'date_creation', 'lu', 'commande', 'priorite']
        read_only_fields = ['type', 'titre', 'message', 'date_creation', 'priorite', 'commande']
