# api/views.py - ViewSets optimisés

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from django.db.models import Q
from transport.models import (
    Client, Transporteur, Adresse, Commande, 
    MissionTransporteur, Incident, Notification
)
from .serializers import (
    ClientSerializer, TransporteurSerializer, AdresseSerializer,
    CommandeSerializer, MissionSerializer, IncidentSerializer, NotificationSerializer
)

class ClientViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les clients"""
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Client.objects.select_related('user').all()
        # Utilisateur normal ne voit que son profil
        return Client.objects.filter(user=user)

class TransporteurViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les transporteurs"""
    serializer_class = TransporteurSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Transporteur.objects.select_related('user').all()
        return Transporteur.objects.filter(user=user)
    
    @action(detail=True, methods=['post'])
    def update_position(self, request, pk=None):
        """Mettre à jour la position du transporteur"""
        transporteur = self.get_object()
        if request.user != transporteur.user and not request.user.is_staff:
            raise PermissionDenied("Non autorisé")
        
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        
        if latitude and longitude:
            transporteur.latitude_actuelle = latitude
            transporteur.longitude_actuelle = longitude
            transporteur.derniere_maj_position = timezone.now()
            transporteur.save()
            
            return Response({'status': 'Position mise à jour'})
        
        return Response(
            {'error': 'Latitude et longitude requises'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

class CommandeViewSet(viewsets.ModelViewSet):
    """ViewSet pour les commandes"""
    serializer_class = CommandeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Commande.objects.select_related(
                'client', 'transporteur', 'adresse_enlevement', 'adresse_livraison'
            ).all()
        
        try:
            client = user.client
            return Commande.objects.filter(client=client).select_related(
                'transporteur', 'adresse_enlevement', 'adresse_livraison'
            )
        except Client.DoesNotExist:
            return Commande.objects.none()
    
    def perform_create(self, serializer):
        """Créer une commande pour le client connecté"""
        user = self.request.user
        try:
            client = user.client
            serializer.save(client=client)
        except Client.DoesNotExist:
            raise PermissionDenied("Seuls les clients peuvent créer des commandes")
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Annuler une commande"""
        commande = self.get_object()
        
        # Vérifications
        if commande.statut in ['EN_TRANSIT', 'LIVREE']:
            return Response(
                {'error': 'Cette commande ne peut plus être annulée'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        commande.statut = 'ANNULEE'
        commande.save()
        
        return Response({'status': 'Commande annulée'})

class MissionViewSet(viewsets.ModelViewSet):
    """ViewSet pour les missions"""
    serializer_class = MissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return MissionTransporteur.objects.select_related(
                'transporteur', 'commande'
            ).all()
        elif hasattr(user, 'transporteur'):
            return MissionTransporteur.objects.filter(
                transporteur=user.transporteur
            ).select_related('commande')
        else:
            return MissionTransporteur.objects.none()
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Mettre à jour le statut d'une mission"""
        mission = self.get_object()
        nouveau_statut = request.data.get('statut')
        
        if not nouveau_statut:
            return Response(
                {'error': 'Statut requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Logique de mise à jour
        mission.statut = nouveau_statut
        
        if nouveau_statut == 'EN_COURS':
            mission.date_debut = mission.date_debut or timezone.now()
            mission.commande.statut = 'EN_TRANSIT'
        elif nouveau_statut == 'TERMINEE':
            mission.date_fin = timezone.now()
            mission.commande.statut = 'LIVREE'
        
        mission.save()
        mission.commande.save()
        
        # Notification client
        from transport.services import NotificationService
        NotificationService.notify_status_change(mission, nouveau_statut)
        
        return Response({'status': 'Statut mis à jour'})

class IncidentViewSet(viewsets.ModelViewSet):
    """ViewSet pour les incidents"""
    serializer_class = IncidentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Incident.objects.select_related('mission', 'transporteur').all()
        elif hasattr(user, 'transporteur'):
            return Incident.objects.filter(transporteur=user.transporteur)
        elif hasattr(user, 'client'):
            return Incident.objects.filter(mission__commande__client=user.client)
        else:
            return Incident.objects.none()
    
    def perform_create(self, serializer):
        """Créer un incident"""
        user = self.request.user
        if not hasattr(user, 'transporteur'):
            raise PermissionDenied("Seuls les transporteurs peuvent signaler des incidents")
        
        incident = serializer.save(transporteur=user.transporteur)
        
        # Notifications
        from transport.services import NotificationService
        NotificationService.notify_incident(incident)

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les notifications"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(
            destinataire=self.request.user
        ).select_related('commande').order_by('-date_creation')
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Marquer une notification comme lue"""
        notification = self.get_object()
        notification.marquer_comme_lue()
        return Response({'status': 'Notification marquée comme lue'})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Marquer toutes les notifications comme lues"""
        Notification.objects.filter(
            destinataire=request.user,
            lu=False
        ).update(lu=True)
        return Response({'status': 'Toutes les notifications marquées comme lues'})
    
    @action(detail=False)
    def unread_count(self, request):
        """Obtenir le nombre de notifications non lues"""
        count = Notification.objects.filter(
            destinataire=request.user,
            lu=False
        ).count()
        return Response({'count': count})
