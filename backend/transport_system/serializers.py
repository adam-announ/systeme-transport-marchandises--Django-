from rest_framework import serializers
from django.contrib.auth.models import User
from .models import *

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active']
        extra_kwargs = {'password': {'write_only': True}}

class AdresseSerializer(serializers.ModelSerializer):
    full_address = serializers.ReadOnlyField(source='get_full_address')
    
    class Meta:
        model = Adresse
        fields = '__all__'

class UtilisateurSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    adresse = AdresseSerializer(read_only=True)
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = Utilisateur
        fields = '__all__'

class ClientSerializer(serializers.ModelSerializer):
    utilisateur = UtilisateurSerializer(read_only=True)
    nb_commandes = serializers.SerializerMethodField()
    
    class Meta:
        model = Client
        fields = '__all__'
    
    def get_nb_commandes(self, obj):
        return obj.commandes.count()

class TransporteurSerializer(serializers.ModelSerializer):
    utilisateur = UtilisateurSerializer(read_only=True)
    nb_missions_actives = serializers.SerializerMethodField()
    distance_disponibilite = serializers.SerializerMethodField()
    
    class Meta:
        model = Transporteur
        fields = '__all__'
    
    def get_nb_missions_actives(self, obj):
        return obj.commandes.filter(
            statut__in=['assignee', 'acceptee', 'en_transit', 'en_cours_livraison']
        ).count()
    
    def get_distance_disponibilite(self, obj):
        # Calculer la distance depuis la position actuelle (si disponible)
        # Cette méthode pourrait être étendue pour calculer la distance réelle
        return None

class ItineraireSerializer(serializers.ModelSerializer):
    class Meta:
        model = Itineraire
        fields = '__all__'

class TrackingSerializer(serializers.ModelSerializer):
    utilisateur_nom = serializers.CharField(source='utilisateur.username', read_only=True)
    etape_display = serializers.CharField(source='get_etape_display', read_only=True)
    
    class Meta:
        model = Tracking
        fields = '__all__'

class CommandeListSerializer(serializers.ModelSerializer):
    client_nom = serializers.CharField(source='client.utilisateur.full_name', read_only=True)
    transporteur_nom = serializers.CharField(source='transporteur.utilisateur.full_name', read_only=True)
    adresse_enlevement = AdresseSerializer(read_only=True)
    adresse_livraison = AdresseSerializer(read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    priorite_display = serializers.CharField(source='get_priorite_display', read_only=True)
    duree_estimee = serializers.ReadOnlyField()
    
    class Meta:
        model = Commande
        fields = [
            'id', 'numero', 'client', 'client_nom', 'transporteur', 'transporteur_nom',
            'type_marchandise', 'description', 'poids', 'volume', 'valeur_declaree',
            'adresse_enlevement', 'adresse_livraison', 'statut', 'statut_display',
            'priorite', 'priorite_display', 'date_creation', 'date_enlevement_prevue',
            'date_livraison_prevue', 'prix_estime', 'prix_final', 'duree_estimee'
        ]

class CommandeDetailSerializer(serializers.ModelSerializer):
    client = ClientSerializer(read_only=True)
    transporteur = TransporteurSerializer(read_only=True)
    adresse_enlevement = AdresseSerializer()
    adresse_livraison = AdresseSerializer()
    itineraire = ItineraireSerializer(read_only=True)
    tracking = TrackingSerializer(many=True, read_only=True)
    bon_livraison = serializers.SerializerMethodField()
    incidents = serializers.SerializerMethodField()
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    priorite_display = serializers.CharField(source='get_priorite_display', read_only=True)
    type_marchandise_display = serializers.CharField(source='get_type_marchandise_display', read_only=True)
    
    class Meta:
        model = Commande
        fields = '__all__'
    
    def get_bon_livraison(self, obj):
        try:
            bon = obj.bon_livraison
            return BonLivraisonSerializer(bon).data
        except BonLivraison.DoesNotExist:
            return None
    
    def get_incidents(self, obj):
        incidents = obj.incidents.all()
        return IncidentSerializer(incidents, many=True).data

class CommandeCreateSerializer(serializers.ModelSerializer):
    adresse_enlevement = AdresseSerializer()
    adresse_livraison = AdresseSerializer()
    
    class Meta:
        model = Commande
        fields = [
            'type_marchandise', 'description', 'poids', 'volume', 'valeur_declaree',
            'instructions_speciales', 'adresse_enlevement', 'adresse_livraison',
            'contact_enlevement', 'contact_livraison', 'telephone_enlevement',
            'telephone_livraison', 'date_enlevement_prevue', 'date_livraison_prevue',
            'priorite'
        ]
    
    def create(self, validated_data):
        adresse_enlevement_data = validated_data.pop('adresse_enlevement')
        adresse_livraison_data = validated_data.pop('adresse_livraison')
        
        # Créer les adresses
        adresse_enlevement = Adresse.objects.create(**adresse_enlevement_data)
        adresse_livraison = Adresse.objects.create(**adresse_livraison_data)
        
        # Créer la commande
        commande = Commande.objects.create(
            adresse_enlevement=adresse_enlevement,
            adresse_livraison=adresse_livraison,
            **validated_data
        )
        
        return commande

class BonLivraisonSerializer(serializers.ModelSerializer):
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    
    class Meta:
        model = BonLivraison
        fields = '__all__'

class IncidentSerializer(serializers.ModelSerializer):
    transporteur_nom = serializers.CharField(source='transporteur.utilisateur.full_name', read_only=True)
    commande_numero = serializers.CharField(source='commande.numero', read_only=True)
    type_incident_display = serializers.CharField(source='get_type_incident_display', read_only=True)
    gravite_display = serializers.CharField(source='get_gravite_display', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    
    class Meta:
        model = Incident
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    type_notification_display = serializers.CharField(source='get_type_notification_display', read_only=True)
    commande_numero = serializers.CharField(source='commande.numero', read_only=True)
    
    class Meta:
        model = Notification
        fields = '__all__'

class JournalSerializer(serializers.ModelSerializer):
    utilisateur_nom = serializers.CharField(source='utilisateur.username', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = Journal
        fields = '__all__'

class ParametresSerializer(serializers.ModelSerializer):
    valeur_typee = serializers.SerializerMethodField()
    
    class Meta:
        model = Parametres
        fields = '__all__'
    
    def get_valeur_typee(self, obj):
        return obj.get_valeur()

class StatistiquesSerializer(serializers.Serializer):
    total_commandes = serializers.IntegerField()
    commandes_en_attente = serializers.IntegerField()
    commandes_en_cours = serializers.IntegerField()
    commandes_livrees = serializers.IntegerField()
    total_transporteurs = serializers.IntegerField()
    transporteurs_disponibles = serializers.IntegerField()
    total_clients = serializers.IntegerField()
    incidents_ouverts = serializers.IntegerField()
    chiffre_affaires_mensuel = serializers.DecimalField(max_digits=12, decimal_places=2)
    distance_totale_mensuelle = serializers.FloatField()

class DashboardSerializer(serializers.Serializer):
    utilisateur = UtilisateurSerializer()
    statistiques = StatistiquesSerializer()
    commandes_recentes = CommandeListSerializer(many=True)
    notifications_non_lues = NotificationSerializer(many=True)
    incidents_recents = IncidentSerializer(many=True)