from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from transport.models import Client, Transporteur, Adresse, Commande, MissionTransporteur, Incident, Notification
from .serializers import (ClientSerializer, TransporteurSerializer, AdresseSerializer,
                          CommandeSerializer, MissionSerializer, IncidentSerializer, NotificationSerializer)

# Permissions de base : authentification requise pour tous
class IsAuthenticated(permissions.IsAuthenticated):
    pass

class ClientViewSet(viewsets.ReadOnlyModelViewSet):
    """Permet à un admin de lister les clients, ou à un client de voir son profil."""
    queryset = Client.objects.select_related('user').all()
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Client.objects.select_related('user').all()
        # Si utilisateur normal, ne renvoyer que son propre profil client s'il en a un
        return Client.objects.filter(user=user)

class TransporteurViewSet(viewsets.ReadOnlyModelViewSet):
    """Liste des transporteurs (admins seulement) ou profil transporteur propre."""
    queryset = Transporteur.objects.select_related('user').all()
    serializer_class = TransporteurSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Transporteur.objects.select_related('user').all()
        return Transporteur.objects.filter(user=user)

class AdresseViewSet(viewsets.ModelViewSet):
    """CRUD adresses (admins seulement en écriture)."""
    queryset = Adresse.objects.all()
    serializer_class = AdresseSerializer
    permission_classes = [permissions.IsAuthenticated]
    def create(self, request, *args, **kwargs):
        # Un client authentifié peut créer une nouvelle adresse pour passer une commande
        return super().create(request, *args, **kwargs)

class CommandeViewSet(viewsets.ModelViewSet):
    """CRUD des commandes."""
    queryset = Commande.objects.select_related('client','transporteur').all()
    serializer_class = CommandeSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Commande.objects.select_related('client','transporteur','adresse_enlevement','adresse_livraison').all()
        try:
            client = user.client
        except Client.DoesNotExist:
            # Transporteurs n'ont pas accès aux commandes via cet endpoint
            return Commande.objects.none()
        return Commande.objects.filter(client=client).select_related('adresse_enlevement','adresse_livraison','transporteur')
    def perform_create(self, serializer):
        # Associer automatiquement au client connecté
        user = self.request.user
        try:
            client = user.client
        except Client.DoesNotExist:
            raise PermissionDenied("Seuls les clients peuvent créer des commandes via l'API.")
        # Il faudrait créer les objets Adresse si nécessaire (ici on suppose que l’ID d'une adresse existante est fourni 
        # ou qu'on a déjà créé via AdresseViewSet)
        serializer.save(client=client)

class MissionViewSet(viewsets.ModelViewSet):
    """Liste et mise à jour des missions de transport."""
    queryset = MissionTransporteur.objects.select_related('transporteur','commande').all()
    serializer_class = MissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return MissionTransporteur.objects.select_related('transporteur','commande').all()
        elif hasattr(user, 'transporteur'):
            # Un transporteur ne voit que ses missions
            return MissionTransporteur.objects.filter(transporteur__user=user).select_related('commande','transporteur')
        else:
            return MissionTransporteur.objects.none()
    def perform_update(self, serializer):
        # Gérer les changements de statut avec effets de bord
        instance = serializer.instance
        old_status = instance.statut
        new_status = serializer.validated_data.get('statut', old_status)
        serializer.save()
        mission = serializer.instance
        # Si statut changé, mettre à jour la commande liée et dates début/fin si nécessaire
        if new_status != old_status:
            if new_status == 'EN_COURS':
                mission.date_debut = mission.date_debut or timezone.now()
                mission.commande.statut = 'EN_TRANSIT'
            elif new_status == 'TERMINEE':
                mission.date_fin = timezone.now()
                mission.commande.statut = 'LIVREE'
            elif new_status == 'ANNULEE':
                mission.commande.statut = 'ANNULEE'
            mission.commande.save()
            mission.save()
            # notifier client du changement de statut
            Notification.objects.create(
                destinataire=mission.commande.client.user,
                type='STATUT',
                titre=f"Commande #{mission.commande.id} mise à jour",
                message=f"Nouveau statut: {mission.get_statut_display()}",
                commande=mission.commande
            )
    def perform_create(self, serializer):
        # Seul un staff (planificateur) peut créer une mission via l'API
        if not self.request.user.is_staff:
            raise PermissionDenied("Seul un administrateur/planificateur peut assigner des missions.")
        serializer.save()

class IncidentViewSet(viewsets.ModelViewSet):
    """Reporting des incidents."""
    queryset = Incident.objects.select_related('mission','transporteur').all()
    serializer_class = IncidentSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Incident.objects.select_related('mission','transporteur').all()
        elif hasattr(user, 'transporteur'):
            # Transporteur voit les incidents qu'il a signalés
            return Incident.objects.filter(transporteur__user=user)
        elif hasattr(user, 'client'):
            # Client voit les incidents liés à ses commandes
            return Incident.objects.filter(mission__commande__client__user=user)
        else:
            return Incident.objects.none()
    def perform_create(self, serializer):
        user = self.request.user
        if not hasattr(user, 'transporteur'):
            raise PermissionDenied("Seul un transporteur peut signaler un incident.")
        transporteur = user.transporteur
        incident = serializer.save(transporteur=transporteur)
        # Notifications suite à incident (même logique que dans la vue notifier_incident)
        # Notifier admin:
        for admin in User.objects.filter(is_staff=True):
            Notification.objects.create(
                destinataire=admin,
                type='INCIDENT',
                titre=f"Incident sur commande #{incident.mission.commande.id}",
                message=f"Type: {incident.get_type_display()} – {incident.description}",
                commande=incident.mission.commande,
                priorite='HAUTE'
            )
        # Notifier client:
        Notification.objects.create(
            destinataire=incident.mission.commande.client.user,
            type='INCIDENT',
            titre="Incident sur votre livraison",
            message=f"Un incident a été signalé: {incident.get_type_display()}",
            commande=incident.mission.commande
        )

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Consultation des notifications personnelles."""
    queryset = Notification.objects.select_related('commande').all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        # Chaque utilisateur ne voit que ses notifications
        return Notification.objects.filter(destinataire=self.request.user).select_related('commande')
    @action(detail=True, methods=['POST'])
    def marquer_lue(self, request, pk=None):
        """Endpoint personnalisé: marquer une notification comme lue"""
        notif = get_object_or_404(Notification, id=pk, destinataire=request.user)
        notif.lu = True
        notif.save()
        return Response({'status': 'notification marquée comme lue'})
