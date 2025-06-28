from rest_framework import serializers
from .models import User, Commande, Vehicule, Livraison, Tournee, EtapeTournee, Notification

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'first_name', 'last_name', 'phone', 'is_active']
        extra_kwargs = {'password': {'write_only': True}}

class CommandeSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    transporteur_name = serializers.CharField(source='transporteur.get_full_name', read_only=True)
    
    class Meta:
        model = Commande
        fields = '__all__'

class VehiculeSerializer(serializers.ModelSerializer):
    transporteur_name = serializers.CharField(source='transporteur.get_full_name', read_only=True)
    
    class Meta:
        model = Vehicule
        fields = '__all__'

class LivraisonSerializer(serializers.ModelSerializer):
    commande_details = CommandeSerializer(source='commande', read_only=True)
    vehicule_details = VehiculeSerializer(source='vehicule', read_only=True)
    
    class Meta:
        model = Livraison
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'

class TourneeSerializer(serializers.ModelSerializer):
    etapes = serializers.SerializerMethodField()
    
    class Meta:
        model = Tournee
        fields = '__all__'
    
    def get_etapes(self, obj):
        return EtapeTourneeSerializer(obj.etapes.all(), many=True).data

class EtapeTourneeSerializer(serializers.ModelSerializer):
    commande_details = CommandeSerializer(source='commande', read_only=True)
    
    class Meta:
        model = EtapeTournee
        fields = '__all__'