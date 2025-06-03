from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
import googlemaps
from .models import *
from .serializers import *
from .utils import calculer_prix, optimiser_itineraire, envoyer_notification

class CommandeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        try:
            utilisateur = Utilisateur.objects.get(user=user)
            
            if utilisateur.role == 'client':
                client = Client.objects.get(utilisateur=utilisateur)
                return Commande.objects.filter(client=client)
            elif utilisateur.role == 'transporteur':
                transporteur = Transporteur.objects.get(utilisateur=utilisateur)
                return Commande.objects.filter(transporteur=transporteur)
            elif utilisateur.role in ['admin', 'planificateur']:
                return Commande.objects.all()
            
        except (Utilisateur.DoesNotExist, Client.DoesNotExist, Transporteur.DoesNotExist):
            return Commande.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CommandeCreateSerializer
        elif self.action in ['retrieve', 'update', 'partial_update']:
            return CommandeDetailSerializer
        return CommandeListSerializer
    
    def perform_create(self, serializer):
        user = self.request.user
        try:
            utilisateur = Utilisateur.objects.get(user=user)
            client = Client.objects.get(utilisateur=utilisateur)
            
            commande = serializer.save(client=client)
            
            # Calculer le prix estimé
            prix_estime = calculer_prix(commande)
            commande.prix_estime = prix_estime
            commande.save()
            
            # Créer l'entrée de tracking
            Tracking.objects.create(
                commande=commande,
                etape='commande_creee',
                description='Commande créée par le client',
                utilisateur=user
            )
            
            # Notifier les planificateurs
            planificateurs = Utilisateur.objects.filter(role='planificateur')
            for planificateur in planificateurs:
                Notification.objects.create(
                    destinataire=planificateur.user,
                    type_notification='commande',
                    titre='Nouvelle commande à traiter',
                    message=f'Nouvelle commande {commande.numero} créée',
                    commande=commande
                )
            
        except (Utilisateur.DoesNotExist, Client.DoesNotExist):
            raise serializers.ValidationError("Client non trouvé")
    
    @action(detail=True, methods=['post'])
    def assigner_transporteur(self, request, pk=None):
        commande = self.get_object()
        transporteur_id = request.data.get('transporteur_id')
        
        if not transporteur_id:
            return Response(
                {'error': 'ID transporteur requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            transporteur = Transporteur.objects.get(id=transporteur_id, disponibilite=True)
            
            commande.transporteur = transporteur
            commande.statut = 'assignee'
            commande.save()
            
            # Créer l'itinéraire optimisé
            itineraire_data = optimiser_itineraire(commande)
            if itineraire_data:
                Itineraire.objects.update_or_create(
                    commande=commande,
                    defaults=itineraire_data
                )
            
            # Tracking
            Tracking.objects.create(
                commande=commande,
                etape='transporteur_assigne',
                description=f'Transporteur {transporteur.utilisateur.full_name} assigné',
                utilisateur=request.user
            )
            
            # Notification au transporteur
            Notification.objects.create(
                destinataire=transporteur.utilisateur.user,
                type_notification='assignation',
                titre='Nouvelle mission assignée',
                message=f'Mission {commande.numero} vous a été assignée',
                commande=commande
            )
            
            return Response({'message': 'Transporteur assigné avec succès'})
            
        except Transporteur.DoesNotExist:
            return Response(
                {'error': 'Transporteur non trouvé ou indisponible'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def changer_statut(self, request, pk=None):
        commande = self.get_object()
        nouveau_statut = request.data.get('statut')
        commentaire = request.data.get('commentaire', '')
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        
        if nouveau_statut not in dict(Commande.STATUTS):
            return Response(
                {'error': 'Statut invalide'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ancien_statut = commande.statut
        commande.statut = nouveau_statut
        
        # Mettre à jour les dates selon le statut
        now = timezone.now()
        if nouveau_statut == 'en_cours_enlevement':
            commande.date_enlevement_effective = now
        elif nouveau_statut == 'livree':
            commande.date_livraison_effective = now
        
        commande.save()
        
        # Mapping des statuts vers les étapes de tracking
        etapes_mapping = {
            'en_cours_enlevement': 'enlevement_en_cours',
            'en_transit': 'en_transit',
            'en_cours_livraison': 'livraison_en_cours',
            'livree': 'livree'
        }
        
        etape = etapes_mapping.get(nouveau_statut, 'statut_change')
        
        # Créer le tracking
        Tracking.objects.create(
            commande=commande,
            etape=etape,
            description=commentaire or f'Statut changé de {ancien_statut} à {nouveau_statut}',
            latitude=latitude,
            longitude=longitude,
            utilisateur=request.user
        )
        
        # Notification au client
        Notification.objects.create(
            destinataire=commande.client.utilisateur.user,
            type_notification='statut',
            titre='Mise à jour de votre commande',
            message=f'Votre commande {commande.numero} est maintenant {commande.get_statut_display()}',
            commande=commande
        )
        
        return Response({'message': 'Statut mis à jour avec succès'})
    
    @action(detail=True, methods=['get'])
    def tracking(self, request, pk=None):
        commande = self.get_object()
        tracking_data = commande.tracking.all()
        serializer = TrackingSerializer(tracking_data, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistiques(self, request):
        user = self.request.user
        queryset = self.get_queryset()
        
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        stats = {
            'total': queryset.count(),
            'en_attente': queryset.filter(statut='en_attente').count(),
            'en_cours': queryset.filter(
                statut__in=['assignee', 'en_transit', 'en_cours_livraison']
            ).count(),
            'livrees': queryset.filter(statut='livree').count(),
            'ce_mois': queryset.filter(date_creation__gte=month_start).count(),
            'chiffre_affaires_mensuel': queryset.filter(
                date_creation__gte=month_start,
                prix_final__isnull=False
            ).aggregate(total=Sum('prix_final'))['total'] or 0
        }
        
        return Response(stats)

class TransporteurViewSet(viewsets.ModelViewSet):
    queryset = Transporteur.objects.all()
    serializer_class = TransporteurSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['post'])
    def toggle_disponibilite(self, request, pk=None):
        transporteur = self.get_object()
        transporteur.disponibilite = not transporteur.disponibilite
        
        if transporteur.disponibilite:
            transporteur.statut = 'disponible'
        else:
            transporteur.statut = 'repos'
        
        transporteur.save()
        
        return Response({
            'disponibilite': transporteur.disponibilite,
            'statut': transporteur.statut
        })
    
    @action(detail=True, methods=['post'])
    def update_position(self, request, pk=None):
        transporteur = self.get_object()
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        
        if latitude and longitude:
            transporteur.update_position(float(latitude), float(longitude))
            return Response({'message': 'Position mise à jour'})
        
        return Response(
            {'error': 'Coordonnées requises'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=False, methods=['get'])
    def disponibles(self, request):
        transporteurs = self.queryset.filter(disponibilite=True, statut='disponible')
        serializer = self.get_serializer(transporteurs, many=True)
        return Response(serializer.data)

class IncidentViewSet(viewsets.ModelViewSet):
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        try:
            utilisateur = Utilisateur.objects.get(user=user)
            
            if utilisateur.role == 'transporteur':
                transporteur = Transporteur.objects.get(utilisateur=utilisateur)
                return Incident.objects.filter(transporteur=transporteur)
            elif utilisateur.role == 'client':
                client = Client.objects.get(utilisateur=utilisateur)
                return Incident.objects.filter(commande__client=client)
            elif utilisateur.role in ['admin', 'planificateur']:
                return Incident.objects.all()
                
        except (Utilisateur.DoesNotExist, Transporteur.DoesNotExist, Client.DoesNotExist):
            return Incident.objects.none()
    
    def perform_create(self, serializer):
        user = self.request.user
        
        # Déterminer le transporteur
        transporteur = None
        try:
            utilisateur = Utilisateur.objects.get(user=user)
            if utilisateur.role == 'transporteur':
                transporteur = Transporteur.objects.get(utilisateur=utilisateur)
        except (Utilisateur.DoesNotExist, Transporteur.DoesNotExist):
            pass
        
        incident = serializer.save(transporteur=transporteur)
        
        # Créer le tracking si lié à une commande
        if incident.commande:
            Tracking.objects.create(
                commande=incident.commande,
                etape='incident',
                description=f'Incident signalé: {incident.titre}',
                latitude=incident.latitude,
                longitude=incident.longitude,
                utilisateur=user
            )
        
        # Notifier les administrateurs
        admins = Utilisateur.objects.filter(role='admin')
        for admin in admins:
            Notification.objects.create(
                destinataire=admin.user,
                type_notification='incident',
                titre='Nouvel incident signalé',
                message=f'Incident {incident.type_incident}: {incident.titre}',
                commande=incident.commande
            )

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(destinataire=self.request.user)
    
    @action(detail=True, methods=['post'])
    def marquer_lue(self, request, pk=None):
        notification = self.get_object()
        notification.marquer_comme_lue()
        return Response({'message': 'Notification marquée comme lue'})
    
    @action(detail=False, methods=['post'])
    def marquer_toutes_lues(self, request):
        notifications = self.get_queryset().filter(lue=False)
        for notification in notifications:
            notification.marquer_comme_lue()
        return Response({'message': f'{notifications.count()} notifications marquées comme lues'})
    
    @action(detail=False, methods=['get'])
    def non_lues(self, request):
        notifications = self.get_queryset().filter(lue=False)
        serializer = self.get_serializer(notifications, many=True)
        return Response({
            'count': notifications.count(),
            'notifications': serializer.data
        })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_data(request):
    """Données du tableau de bord selon le rôle utilisateur"""
    user = request.user
    
    try:
        utilisateur = Utilisateur.objects.get(user=user)
        
        # Statistiques générales
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        if utilisateur.role == 'client':
            client = Client.objects.get(utilisateur=utilisateur)
            commandes = Commande.objects.filter(client=client)
            
            stats = {
                'total_commandes': commandes.count(),
                'commandes_en_attente': commandes.filter(statut='en_attente').count(),
                'commandes_en_cours': commandes.filter(
                    statut__in=['assignee', 'en_transit', 'en_cours_livraison']
                ).count(),
                'commandes_livrees': commandes.filter(statut='livree').count(),
                'montant_total': commandes.filter(
                    prix_final__isnull=False
                ).aggregate(total=Sum('prix_final'))['total'] or 0,
                'ce_mois': commandes.filter(date_creation__gte=month_start).count()
            }
            
            commandes_recentes = commandes.order_by('-date_creation')[:5]
            
        elif utilisateur.role == 'transporteur':
            transporteur = Transporteur.objects.get(utilisateur=utilisateur)
            commandes = Commande.objects.filter(transporteur=transporteur)
            
            stats = {
                'missions_totales': commandes.count(),
                'missions_actives': commandes.filter(
                    statut__in=['assignee', 'en_transit', 'en_cours_livraison']
                ).count(),
                'missions_terminees': commandes.filter(statut='livree').count(),
                'disponibilite': transporteur.disponibilite,
                'rating': transporteur.rating,
                'ce_mois': commandes.filter(date_creation__gte=month_start).count()
            }
            
            commandes_recentes = commandes.order_by('-date_creation')[:5]
            
        elif utilisateur.role in ['admin', 'planificateur']:
            commandes = Commande.objects.all()
            transporteurs = Transporteur.objects.all()
            clients = Client.objects.all()
            incidents = Incident.objects.all()
            
            stats = {
                'total_commandes': commandes.count(),
                'commandes_en_attente': commandes.filter(statut='en_attente').count(),
                'commandes_en_cours': commandes.filter(
                    statut__in=['assignee', 'en_transit', 'en_cours_livraison']
                ).count(),
                'commandes_livrees': commandes.filter(statut='livree').count(),
                'total_transporteurs': transporteurs.count(),
                'transporteurs_disponibles': transporteurs.filter(disponibilite=True).count(),
                'total_clients': clients.count(),
                'incidents_ouverts': incidents.filter(statut='ouvert').count(),
                'chiffre_affaires_mensuel': commandes.filter(
                    date_creation__gte=month_start,
                    prix_final__isnull=False
                ).aggregate(total=Sum('prix_final'))['total'] or 0
            }
            
            commandes_recentes = commandes.order_by('-date_creation')[:10]
        
        # Notifications non lues
        notifications_non_lues = Notification.objects.filter(
            destinataire=user, 
            lue=False
        )[:5]
        
        # Incidents récents (si admin/planificateur)
        incidents_recents = []
        if utilisateur.role in ['admin', 'planificateur']:
            incidents_recents = Incident.objects.filter(
                statut__in=['ouvert', 'en_cours']
            ).order_by('-date_creation')[:5]
        
        response_data = {
            'utilisateur': UtilisateurSerializer(utilisateur).data,
            'statistiques': stats,
            'commandes_recentes': CommandeListSerializer(commandes_recentes, many=True).data,
            'notifications_non_lues': NotificationSerializer(notifications_non_lues, many=True).data,
            'incidents_recents': IncidentSerializer(incidents_recents, many=True).data
        }
        
        return Response(response_data)
        
    except (Utilisateur.DoesNotExist, Client.DoesNotExist, Transporteur.DoesNotExist):
        return Response(
            {'error': 'Profil utilisateur non trouvé'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assignation_automatique(request):
    """Assignation automatique des transporteurs"""
    strategie = request.data.get('strategie', 'nearest')  # nearest, capacity, balanced
    distance_max = request.data.get('distance_max', 50)  # km
    commandes_ids = request.data.get('commandes', [])
    
    if commandes_ids:
        commandes = Commande.objects.filter(
            id__in=commandes_ids,
            statut='en_attente'
        )
    else:
        commandes = Commande.objects.filter(statut='en_attente')
    
    transporteurs_disponibles = Transporteur.objects.filter(
        disponibilite=True,
        statut='disponible'
    )
    
    assignations = []
    
    for commande in commandes:
        # Algorithme d'assignation selon la stratégie
        if strategie == 'nearest':
            # Trouver le transporteur le plus proche
            # (Simplification - en réalité, utiliser l'API Google Maps)
            transporteur = transporteurs_disponibles.first()
        elif strategie == 'capacity':
            # Trouver le transporteur avec la meilleure capacité
            transporteur = transporteurs_disponibles.filter(
                capacite_charge__gte=commande.poids
            ).order_by('capacite_charge').first()
        elif strategie == 'balanced':
            # Équilibrer la charge de travail
            transporteur = transporteurs_disponibles.annotate(
                nb_missions=Count('commandes', filter=Q(
                    commandes__statut__in=['assignee', 'en_transit', 'en_cours_livraison']
                ))
            ).order_by('nb_missions').first()
        
        if transporteur:
            commande.transporteur = transporteur
            commande.statut = 'assignee'
            commande.save()
            
            # Créer l'itinéraire
            itineraire_data = optimiser_itineraire(commande)
            if itineraire_data:
                Itineraire.objects.update_or_create(
                    commande=commande,
                    defaults=itineraire_data
                )
            
            # Tracking
            Tracking.objects.create(
                commande=commande,
                etape='transporteur_assigne',
                description=f'Assigné automatiquement à {transporteur.utilisateur.full_name}',
                utilisateur=request.user
            )
            
            # Notification
            Notification.objects.create(
                destinataire=transporteur.utilisateur.user,
                type_notification='assignation',
                titre='Nouvelle mission assignée automatiquement',
                message=f'Mission {commande.numero} vous a été assignée',
                commande=commande
            )
            
            assignations.append({
                'commande': commande.numero,
                'transporteur': transporteur.utilisateur.full_name,
                'distance_estimee': itineraire_data.get('distance_km') if itineraire_data else None
            })
    
    return Response({
        'message': f'{len(assignations)} commandes assignées',
        'assignations': assignations
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def calculer_itineraire_api(request):
    """Calculer un itinéraire avec Google Maps"""
    origine = request.data.get('origine')
    destination = request.data.get('destination')
    points_intermediaires = request.data.get('waypoints', [])
    
    if not origine or not destination:
        return Response(
            {'error': 'Origine et destination requises'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Utiliser Google Maps API
        gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
        
        # Calculer les directions
        directions = gmaps.directions(
            origin=origine,
            destination=destination,
            waypoints=points_intermediaires,
            optimize_waypoints=True,
            language='fr'
        )
        
        if directions:
            route = directions[0]
            leg = route['legs'][0]
            
            return Response({
                'distance_km': leg['distance']['value'] / 1000,
                'duree_minutes': leg['duration']['value'] / 60,
                'distance_text': leg['distance']['text'],
                'duree_text': leg['duration']['text'],
                'polyline': route['overview_polyline']['points'],
                'instructions': [step['html_instructions'] for step in leg['steps']]
            })
        else:
            return Response(
                {'error': 'Itinéraire non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
            
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )