"""
Vues pour l'interface planificateur
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from core.models import Commande, User, Itineraire, Vehicule
from .services import OptimisationService, MeteoService

@login_required
def dashboard(request):
    """Tableau de bord planificateur"""
    if request.user.role != 'planificateur':
        return redirect('auth:login')
    
    commandes_en_attente = Commande.objects.filter(statut='en_attente').count()
    commandes_confirmees = Commande.objects.filter(statut='confirmee').count()
    transporteurs_disponibles = User.objects.filter(role='transporteur', actif=True).count()
    
    stats = {
        'commandes_en_attente': commandes_en_attente,
        'commandes_confirmees': commandes_confirmees,
        'transporteurs_disponibles': transporteurs_disponibles,
    }
    
    return render(request, 'planificateur/dashboard.html', {'stats': stats})

@login_required
def gestion_commandes(request):
    """Gestion des commandes à planifier"""
    if request.user.role != 'planificateur':
        return redirect('auth:login')
    
    commandes = Commande.objects.filter(statut__in=['en_attente', 'confirmee']).order_by('-date_creation')
    transporteurs = User.objects.filter(role='transporteur', actif=True)
    
    return render(request, 'planificateur/gestion_commandes.html', {
        'commandes': commandes,
        'transporteurs': transporteurs
    })

@login_required
def optimiser_itineraire(request, commande_id):
    """Optimiser l'itinéraire d'une commande"""
    if request.user.role != 'planificateur':
        return redirect('auth:login')
    
    from django.conf import settings
    commande = get_object_or_404(Commande, id=commande_id)
    
    if request.method == 'POST':
        commande.statut = 'confirmee'
        commande.save()
        messages.success(request, 'Itinéraire validé avec succès')
        return redirect('planificateur:gestion_commandes')
    
    return render(request, 'planificateur/optimiser_itineraire.html', {
        'commande': commande,
        'OPENROUTE_API_KEY': settings.OPENROUTE_API_KEY
    })

@login_required
def affecter_transporteur(request, commande_id):
    """Affecter un transporteur à une commande"""
    if request.user.role != 'planificateur':
        return redirect('auth:login')
    
    commande = get_object_or_404(Commande, id=commande_id)
    
    if request.method == 'POST':
        transporteur_id = request.POST.get('transporteur_id')
        transporteur = get_object_or_404(User, id=transporteur_id, role='transporteur')
        
        commande.transporteur = transporteur
        commande.statut = 'confirmee'
        commande.save()
        
        messages.success(request, f'Commande affectée à {transporteur.username}')
        return redirect('planificateur:gestion_commandes')
    
    transporteurs = User.objects.filter(role='transporteur', actif=True)
    return render(request, 'planificateur/affecter_transporteur.html', {
        'commande': commande,
        'transporteurs': transporteurs
    })

@api_view(['POST'])
def api_optimiser_itineraire(request):
    """API pour optimiser un itinéraire"""
    if request.user.role != 'planificateur':
        return Response({'error': 'Accès non autorisé'}, status=403)
    
    commande_id = request.data.get('commande_id')
    try:
        commande = Commande.objects.get(id=commande_id)
        service = OptimisationService()
        
        # Récupération des données météo
        meteo_service = MeteoService()
        meteo = meteo_service.get_weather(
            commande.latitude_enlevement,
            commande.longitude_enlevement
        )
        
        # Optimisation de l'itinéraire
        itineraire_data = service.optimiser_itineraire(
            lat_depart=commande.latitude_enlevement,
            lng_depart=commande.longitude_enlevement,
            lat_arrivee=commande.latitude_livraison,
            lng_arrivee=commande.longitude_livraison,
            conditions_meteo=meteo
        )
        
        return Response({
            'success': True,
            'itineraire': itineraire_data,
            'meteo': meteo
        })
        
    except Commande.DoesNotExist:
        return Response({'error': 'Commande non trouvée'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
def api_transporteurs_disponibles(request):
    """API pour récupérer les transporteurs disponibles"""
    if request.user.role != 'planificateur':
        return Response({'error': 'Accès non autorisé'}, status=403)
    
    transporteurs = User.objects.filter(role='transporteur', actif=True)
    data = []
    
    for transporteur in transporteurs:
        vehicules = Vehicule.objects.filter(transporteur=transporteur, disponible=True)
        data.append({
            'id': str(transporteur.id),
            'username': transporteur.username,
            'email': transporteur.email,
            'vehicules': [
                {
                    'id': str(v.id),
                    'immatriculation': v.immatriculation,
                    'type': v.type_vehicule,
                    'capacite_poids': v.capacite_poids,
                    'capacite_volume': v.capacite_volume
                } for v in vehicules
            ]
        })
    
    return Response(data)

@api_view(['GET'])
def api_commandes_en_attente(request):
    """API pour récupérer les commandes en attente"""
    if request.user.role != 'planificateur':
        return Response({'error': 'Accès non autorisé'}, status=403)
    
    commandes = Commande.objects.filter(statut='en_attente').order_by('-date_creation')[:10]
    data = []
    
    for commande in commandes:
        data.append({
            'id': str(commande.id),
            'numero': commande.numero,
            'client': commande.client.username,
            'adresse_enlevement': commande.adresse_enlevement,
            'adresse_livraison': commande.adresse_livraison,
            'poids': commande.poids,
            'volume': commande.volume,
            'date_creation': commande.date_creation.isoformat(),
            'distance': getattr(commande, 'itineraire', None) and commande.itineraire.distance_km or None
        })
    
    return Response(data)