# utilisateurs/views_google_maps.py

from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .services.google_maps_service import GoogleMapsService
import json

def google_maps_view(request):
    """Vue pour afficher la carte Google Maps"""
    context = {
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY
    }
    return render(request, 'maps/google_maps.html', context)

def leaflet_maps_view(request):
    """Vue pour afficher la carte Leaflet (gratuite)"""
    return render(request, 'maps/leaflet_map.html')

@csrf_exempt
def optimize_route_api(request):
    """API pour optimiser une tournée"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            depot = data.get('depot')
            deliveries = data.get('deliveries', [])
            
            maps_service = GoogleMapsService()
            result = maps_service.optimize_delivery_route(depot, deliveries)
            
            if result:
                return JsonResponse({
                    'success': True,
                    'data': result
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Impossible d\'optimiser la tournée'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

@csrf_exempt
def geocode_api(request):
    """API pour géocoder une adresse"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            address = data.get('address')
            
            maps_service = GoogleMapsService()
            result = maps_service.geocode_address(address)
            
            if result:
                return JsonResponse({
                    'success': True,
                    'data': result
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Adresse non trouvée'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})