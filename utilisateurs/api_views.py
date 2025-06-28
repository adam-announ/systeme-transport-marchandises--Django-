from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import timedelta
from .models import User, Commande, Vehicule, Livraison, Tournee, Notification
from .serializers import (
    UserSerializer, CommandeSerializer, VehiculeSerializer, 
    LivraisonSerializer, TourneeSerializer, NotificationSerializer
)

class CommandeViewSet(viewsets.ModelViewSet):
    serializer_class = CommandeSerializer
    permission_classes = []
    
    def get_queryset(self):
        if not hasattr(self.request, 'session') or 'user_id' not in self.request.session:
            return Commande.objects.none()
        
        user_id = self.request.session['user_id']
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Commande.objects.none()
        
        if hasattr(user, 'role'):
            if user.role == 'client':
                return Commande.objects.filter(client=user)
            elif user.role == 'transporteur':
                return Commande.objects.filter(Q(transporteur=user) | Q(statut='en_attente'))
            elif user.role in ['admin', 'planificateur']:
                return Commande.objects.all()
        return Commande.objects.none()
    
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        if 'user_id' not in request.session:
            return Response({'error': 'Non authentifié'}, status=401)
        
        try:
            user = User.objects.get(id=request.session['user_id'])
        except User.DoesNotExist:
            return Response({'error': 'Utilisateur introuvable'}, status=404)
        stats = {}
        
        if user.role == 'client':
            stats = {
                'total': Commande.objects.filter(client=user).count(),
                'en_cours': Commande.objects.filter(client=user, statut__in=['affectee', 'en_cours']).count(),
                'livrees': Commande.objects.filter(client=user, statut='livree').count(),
            }
        elif user.role == 'transporteur':
            stats = {
                'disponibles': Commande.objects.filter(statut='en_attente').count(),
                'mes_commandes': Commande.objects.filter(transporteur=user).count(),
                'en_cours': Commande.objects.filter(transporteur=user, statut='en_cours').count(),
            }
        
        return Response(stats)

class VehiculeViewSet(viewsets.ModelViewSet):
    serializer_class = VehiculeSerializer
    permission_classes = []
    
    def get_queryset(self):
        if 'user_id' not in self.request.session:
            return Vehicule.objects.none()
        
        try:
            user = User.objects.get(id=self.request.session['user_id'])
        except User.DoesNotExist:
            return Vehicule.objects.none()
        
        if user.role == 'transporteur':
            return Vehicule.objects.filter(transporteur=user)
        elif user.role in ['admin', 'planificateur']:
            return Vehicule.objects.all()
        return Vehicule.objects.none()

class LivraisonViewSet(viewsets.ModelViewSet):
    serializer_class = LivraisonSerializer
    permission_classes = []
    
    def get_queryset(self):
        if 'user_id' not in self.request.session:
            return Livraison.objects.none()
        
        try:
            user = User.objects.get(id=self.request.session['user_id'])
        except User.DoesNotExist:
            return Livraison.objects.none()
        
        if user.role == 'transporteur':
            return Livraison.objects.filter(commande__transporteur=user)
        elif user.role == 'client':
            return Livraison.objects.filter(commande__client=user)
        elif user.role in ['admin', 'planificateur']:
            return Livraison.objects.all()
        return Livraison.objects.none()
    
    @action(detail=True, methods=['post'])
    def update_position(self, request, pk=None):
        livraison = self.get_object()
        lat = request.data.get('latitude')
        lng = request.data.get('longitude')
        
        if lat and lng:
            livraison.latitude_actuelle = lat
            livraison.longitude_actuelle = lng
            livraison.save()
            return Response({'status': 'Position mise à jour'})
        
        return Response({'error': 'Coordonnées manquantes'}, status=400)

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = []
    
    def get_queryset(self):
        if 'user_id' not in self.request.session:
            return Notification.objects.none()
        
        try:
            user = User.objects.get(id=self.request.session['user_id'])
            return Notification.objects.filter(utilisateur=user)
        except User.DoesNotExist:
            return Notification.objects.none()
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        if 'user_id' not in request.session:
            return Response({'error': 'Non authentifié'}, status=401)
        
        try:
            user = User.objects.get(id=request.session['user_id'])
            count = Notification.objects.filter(
                utilisateur=user, 
                lu=False
            ).update(lu=True, date_lecture=timezone.now())
            
            return Response({'marked_read': count})
        except User.DoesNotExist:
            return Response({'error': 'Utilisateur introuvable'}, status=404)