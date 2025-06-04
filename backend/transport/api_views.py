# 1. Créer backend/transport/api_views.py (le fichier principal des vues API)

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.db.models import Sum, Avg, Count, Q
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from datetime import datetime, timedelta
import csv
from django.http import HttpResponse
from .models import *
from .serializers import *
from .utils import calculer_prix, optimiser_itineraire, envoyer_notification, trouver_transporteur_optimal
import logging

logger = logging.getLogger(__name__)

# Vue d'authentification
class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'error': 'Username and password required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = authenticate(username=username, password=password)
        
        if user:
            login(request, user)
            
            # Créer ou récupérer le token
            from rest_framework.authtoken.models import Token
            token, created = Token.objects.get_or_create(user=user)
            
            # Récupérer l'utilisateur complet
            try:
                utilisateur = Utilisateur.objects.get(user=user)
                return Response({
                    'token': token.key,
                    'user': UtilisateurSerializer(utilisateur).data
                })
            except Utilisateur.DoesNotExist:
                return Response(
                    {'error': 'User profile not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        logout(request)
        return Response({'message': 'Successfully logged out'})

class RegisterView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        # Logique d'inscription
        pass

class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            utilisateur = Utilisateur.objects.get(user=request.user)
            return Response(UtilisateurSerializer(utilisateur).data)
        except Utilisateur.DoesNotExist:
            return Response(
                {'error': 'User profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class RefreshTokenView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        from rest_framework.authtoken.models import Token
        # Supprimer l'ancien token
        Token.objects.filter(user=request.user).delete()
        # Créer un nouveau token
        token = Token.objects.create(user=request.user)
        return Response({'token': token.key})

# ViewSets principaux
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

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]

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

class JournalViewSet(viewsets.ModelViewSet):
    queryset = Journal.objects.all()
    serializer_class = JournalSerializer
    permission_classes = [IsAuthenticated]

# Vues spécifiques pour les tableaux de bord
class ClientDashboardView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            utilisateur = Utilisateur.objects.get(user=request.user)
            client = Client.objects.get(utilisateur=utilisateur)
            
            # Statistiques
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
                ).aggregate(total=Sum('prix_final'))['total'] or 0
            }
            
            # Commandes récentes
            commandes_recentes = commandes.order_by('-date_creation')[:5]
            
            # Notifications non lues
            notifications = Notification.objects.filter(
                destinataire=request.user,
                lue=False
            )[:5]
            
            return Response({
                'utilisateur': UtilisateurSerializer(utilisateur).data,
                'statistiques': stats,
                'commandes_recentes': CommandeListSerializer(commandes_recentes, many=True).data,
                'notifications_non_lues': NotificationSerializer(notifications, many=True).data
            })
            
        except (Utilisateur.DoesNotExist, Client.DoesNotExist):
            return Response(
                {'error': 'Client profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class TransporteurDashboardView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            utilisateur = Utilisateur.objects.get(user=request.user)
            transporteur = Transporteur.objects.get(utilisateur=utilisateur)
            
            # Statistiques
            commandes = Commande.objects.filter(transporteur=transporteur)
            today = timezone.now().date()
            month_start = today.replace(day=1)
            
            stats = {
                'missions_totales': commandes.count(),
                'missions_actives': commandes.filter(
                    statut__in=['assignee', 'en_transit', 'en_cours_livraison']
                ).count(),
                'missions_terminees': commandes.filter(statut='livree').count(),
                'missions_aujourdhui': commandes.filter(
                    date_creation__date=today
                ).count(),
                'missions_ce_mois': commandes.filter(
                    date_creation__gte=month_start
                ).count(),
                'disponibilite': transporteur.disponibilite,
                'rating': transporteur.rating
            }
            
            # Missions récentes
            missions_recentes = commandes.order_by('-date_creation')[:5]
            
            # Notifications
            notifications = Notification.objects.filter(
                destinataire=request.user,
                lue=False
            )[:5]
            
            return Response({
                'utilisateur': UtilisateurSerializer(utilisateur).data,
                'transporteur': TransporteurSerializer(transporteur).data,
                'statistiques': stats,
                'missions_recentes': CommandeListSerializer(missions_recentes, many=True).data,
                'notifications_non_lues': NotificationSerializer(notifications, many=True).data
            })
            
        except (Utilisateur.DoesNotExist, Transporteur.DoesNotExist):
            return Response(
                {'error': 'Transporteur profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        # Statistiques générales
        stats = {
            'total_commandes': Commande.objects.count(),
            'commandes_en_attente': Commande.objects.filter(statut='en_attente').count(),
            'commandes_en_cours': Commande.objects.filter(
                statut__in=['assignee', 'en_transit', 'en_cours_livraison']
            ).count(),
            'commandes_livrees': Commande.objects.filter(statut='livree').count(),
            'total_transporteurs': Transporteur.objects.count(),
            'transporteurs_disponibles': Transporteur.objects.filter(disponibilite=True).count(),
            'total_clients': Client.objects.count(),
            'incidents_ouverts': Incident.objects.filter(statut='ouvert').count(),
            'chiffre_affaires_mensuel': Commande.objects.filter(
                date_creation__gte=month_start,
                prix_final__isnull=False
            ).aggregate(total=Sum('prix_final'))['total'] or 0
        }
        
        # Commandes récentes
        commandes_recentes = Commande.objects.order_by('-date_creation')[:10]
        
        # Incidents récents
        incidents_recents = Incident.objects.filter(
            statut__in=['ouvert', 'en_cours']
        ).order_by('-date_creation')[:5]
        
        # Notifications système
        notifications = Notification.objects.filter(
            destinataire=request.user,
            lue=False
        )[:5]
        
        return Response({
            'statistiques': stats,
            'commandes_recentes': CommandeListSerializer(commandes_recentes, many=True).data,
            'incidents_recents': IncidentSerializer(incidents_recents, many=True).data,
            'notifications_non_lues': NotificationSerializer(notifications, many=True).data
        })

class PlanificateurDashboardView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Similaire à AdminDashboardView mais avec focus sur la planification
        commandes_en_attente = Commande.objects.filter(statut='en_attente')
        transporteurs_disponibles = Transporteur.objects.filter(disponibilite=True, statut='disponible')
        
        stats = {
            'commandes_a_assigner': commandes_en_attente.count(),
            'transporteurs_disponibles': transporteurs_disponibles.count(),
            'assignations_aujourdhui': Commande.objects.filter(
                statut='assignee',
                updated_at__date=timezone.now().date()
            ).count()
        }
        
        return Response({
            'statistiques': stats,
            'commandes_en_attente': CommandeListSerializer(commandes_en_attente[:20], many=True).data,
            'transporteurs_disponibles': TransporteurSerializer(transporteurs_disponibles, many=True).data
        })

# Vues pour la gestion des commandes
class AssignTransporteurView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        commande = get_object_or_404(Commande, pk=pk)
        transporteur_id = request.data.get('transporteur_id')
        
        if not transporteur_id:
            return Response(
                {'error': 'Transporteur ID required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        transporteur = get_object_or_404(Transporteur, pk=transporteur_id)
        
        commande.transporteur = transporteur
        commande.statut = 'assignee'
        commande.save()
        
        # Créer tracking
        Tracking.objects.create(
            commande=commande,
            etape='transporteur_assigne',
            description=f'Transporteur {transporteur.utilisateur.full_name} assigné',
            utilisateur=request.user
        )
        
        # Notification
        Notification.objects.create(
            destinataire=transporteur.utilisateur.user,
            type_notification='assignation',
            titre='Nouvelle mission assignée',
            message=f'Mission {commande.numero} vous a été assignée',
            commande=commande
        )
        
        return Response({'message': 'Transporteur assigné avec succès'})

class ChangeStatusView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        commande = get_object_or_404(Commande, pk=pk)
        nouveau_statut = request.data.get('statut')
        
        if nouveau_statut not in dict(Commande.STATUTS):
            return Response(
                {'error': 'Statut invalide'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ancien_statut = commande.statut
        commande.statut = nouveau_statut
        commande.save()
        
        # Logging
        Journal.objects.create(
            utilisateur=request.user,
            action='changement_statut',
            modele='Commande',
            objet_id=str(commande.id),
            description=f'Statut changé de {ancien_statut} à {nouveau_statut}'
        )
        
        return Response({'message': 'Statut mis à jour'})

class TrackingListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        commande = get_object_or_404(Commande, pk=pk)
        tracking = commande.tracking.all()
        serializer = TrackingSerializer(tracking, many=True)
        return Response(serializer.data)

class BonLivraisonView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        commande = get_object_or_404(Commande, pk=pk)
        try:
            bon = commande.bon_livraison
            return Response(BonLivraisonSerializer(bon).data)
        except BonLivraison.DoesNotExist:
            return Response(
                {'error': 'Bon de livraison non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )

# Vues pour les transporteurs
class ToggleDisponibiliteView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        transporteur = get_object_or_404(Transporteur, pk=pk)
        transporteur.disponibilite = not transporteur.disponibilite
        transporteur.save()
        
        return Response({
            'disponibilite': transporteur.disponibilite
        })

class UpdatePositionView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        transporteur = get_object_or_404(Transporteur, pk=pk)
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        
        if latitude and longitude:
            transporteur.update_position(float(latitude), float(longitude))
            return Response({'message': 'Position mise à jour'})
        
        return Response(
            {'error': 'Coordonnées requises'},
            status=status.HTTP_400_BAD_REQUEST
        )

class TransporteursDisponiblesView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        transporteurs = Transporteur.objects.filter(
            disponibilite=True,
            statut='disponible'
        )
        serializer = TransporteurSerializer(transporteurs, many=True)
        return Response(serializer.data)

# Assignation automatique
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assignation_automatique(request):
    commandes_ids = request.data.get('commandes', [])
    strategie = request.data.get('strategie', 'nearest')
    
    if commandes_ids:
        commandes = Commande.objects.filter(
            id__in=commandes_ids,
            statut='en_attente'
        )
    else:
        commandes = Commande.objects.filter(statut='en_attente')
    
    assignations = []
    
    for commande in commandes:
        transporteur = trouver_transporteur_optimal(commande)
        
        if transporteur:
            commande.transporteur = transporteur
            commande.statut = 'assignee'
            commande.save()
            
            # Optimiser l'itinéraire
            itineraire_data = optimiser_itineraire(commande)
            if itineraire_data:
                Itineraire.objects.update_or_create(
                    commande=commande,
                    defaults=itineraire_data
                )
            
            assignations.append({
                'commande': commande.numero,
                'transporteur': transporteur.utilisateur.full_name
            })
    
    return Response({
        'message': f'{len(assignations)} commandes assignées',
        'assignations': assignations
    })

# Optimisation des itinéraires
class OptimiserItinerairesView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Logique d'optimisation
        return Response({'message': 'Optimisation en cours'})

# Calcul d'itinéraire
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def calculer_itineraire_api(request):
    origine = request.data.get('origine')
    destination = request.data.get('destination')
    
    if not origine or not destination:
        return Response(
            {'error': 'Origine et destination requises'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Utiliser Google Maps API (voir utils.py)
    # Pour l'instant, retourner des données simulées
    return Response({
        'distance_km': 45.2,
        'duree_minutes': 52,
        'polyline': 'encoded_polyline_string'
    })

# Géolocalisation
class GeocodingView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        address = request.data.get('address')
        # Implémenter le géocodage
        return Response({
            'latitude': 33.5731,
            'longitude': -7.5898
        })

class ReverseGeocodingView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        lat = request.data.get('latitude')
        lng = request.data.get('longitude')
        # Implémenter le géocodage inverse
        return Response({
            'address': 'Casablanca, Maroc'
        })

# Informations trafic et météo
class TrafficInfoView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Retourner les données de trafic
        return Response({'traffic': 'normal'})

class WeatherInfoView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Retourner les données météo
        return Response({
            'temperature': 22,
            'conditions': 'Ensoleillé'
        })

# Export de données
class ExportCommandesView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        format_export = request.query_params.get('format', 'csv')
        
        if format_export == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="commandes.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['Numéro', 'Client', 'Statut', 'Date création', 'Prix'])
            
            commandes = Commande.objects.all()
            for commande in commandes:
                writer.writerow([
                    commande.numero,
                    commande.client.utilisateur.full_name,
                    commande.get_statut_display(),
                    commande.date_creation.strftime('%Y-%m-%d'),
                    commande.prix_final or commande.prix_estime
                ])
            
            return response
        
        return Response({'error': 'Format non supporté'}, status=status.HTTP_400_BAD_REQUEST)

class ExportTransporteursView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Similaire à ExportCommandesView
        pass

# Rapports
class PerformanceReportView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Générer rapport de performance
        return Response({'report': 'Performance data'})

class FinancialReportView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Générer rapport financier
        return Response({'report': 'Financial data'})

# Upload de fichiers
class ImageUploadView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Gérer l'upload d'images
        return Response({'url': '/media/uploads/image.jpg'})

class DocumentUploadView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Gérer l'upload de documents
        return Response({'url': '/media/uploads/document.pdf'})

# Statistiques
class OverviewStatsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Vue d'ensemble des statistiques
        return Response({'stats': 'overview'})

class CommandeStatsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Statistiques des commandes
        return Response({'stats': 'commandes'})

class TransporteurStatsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Statistiques des transporteurs
        return Response({'stats': 'transporteurs'})

class PerformanceStatsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Statistiques de performance
        return Response({'stats': 'performance'})

# Recherche
class SearchCommandesView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        query = request.query_params.get('q', '')
        commandes = Commande.objects.filter(
            Q(numero__icontains=query) |
            Q(client__utilisateur__nom__icontains=query) |
            Q(description__icontains=query)
        )
        serializer = CommandeListSerializer(commandes[:20], many=True)
        return Response(serializer.data)

class SearchTransporteursView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Recherche de transporteurs
        return Response([])

class SearchClientsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Recherche de clients
        return Response([])

# Webhooks
class TrackingWebhookView(APIView):
    permission_classes = [AllowAny]  # Selon vos besoins de sécurité
    
    def post(self, request):
        # Traiter les mises à jour de tracking externes
        return Response({'status': 'received'})

class PaymentWebhookView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        # Traiter les confirmations de paiement
        return Response({'status': 'received'})

# Configuration
class ConfigurationView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Retourner la configuration
        return Response({'config': {}})

class ParametresView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        parametres = Parametres.objects.all()
        serializer = ParametresSerializer(parametres, many=True)
        return Response(serializer.data)

class ParametreDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, nom):
        parametre = get_object_or_404(Parametres, nom=nom)
        serializer = ParametresSerializer(parametre)
        return Response(serializer.data)
    
    def patch(self, request, nom):
        parametre = get_object_or_404(Parametres, nom=nom)
        parametre.valeur = request.data.get('valeur', parametre.valeur)
        parametre.save()
        serializer = ParametresSerializer(parametre)
        return Response(serializer.data)

# Monitoring
class HealthCheckView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        return Response({
            'status': 'healthy',
            'timestamp': timezone.now()
        })

class MetricsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            'active_users': User.objects.filter(is_active=True).count(),
            'total_commandes': Commande.objects.count(),
            'active_transporteurs': Transporteur.objects.filter(disponibilite=True).count()
        })

# Vue principale du dashboard API
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_data(request):
    """Retourne les données du dashboard selon le rôle de l'utilisateur"""
    user = request.user
    
    try:
        utilisateur = Utilisateur.objects.get(user=user)
        
        if utilisateur.role == 'client':
            return redirect('client_dashboard_api')
        elif utilisateur.role == 'transporteur':
            return redirect('transporteur_dashboard_api')
        elif utilisateur.role == 'admin':
            return redirect('admin_dashboard_api')
        elif utilisateur.role == 'planificateur':
            return redirect('planificateur_dashboard_api')
        else:
            return Response({'error': 'Role non reconnu'}, status=status.HTTP_400_BAD_REQUEST)
            
    except Utilisateur.DoesNotExist:
        return Response({'error': 'Profil utilisateur non trouvé'}, status=status.HTTP_404_NOT_FOUND)