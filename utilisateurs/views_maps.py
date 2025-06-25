# utilisateurs/views_maps.py

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging

from .services.maps_service import maps_service, MapProviderError, GeocodingError, RouteOptimizationError
from .models import Commande, Vehicule, Tournee, EtapeTournee

logger = logging.getLogger(__name__)

class MapsAPIView(View):
    """Vue de base pour les APIs cartographiques"""
    
    @method_decorator(login_required)
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def get_json_data(self, request):
        """Extraire les données JSON de la requête"""
        try:
            if request.content_type == 'application/json':
                return json.loads(request.body.decode('utf-8'))
            return {}
        except json.JSONDecodeError:
            return {}

@method_decorator(csrf_exempt, name='dispatch')
class GeocodeView(MapsAPIView):
    """API pour le géocodage d'adresses"""
    
    def post(self, request):
        try:
            data = self.get_json_data(request)
            address = data.get('address', '').strip()
            provider = data.get('provider', None)
            
            if not address:
                return JsonResponse({
                    'success': False,
                    'error': 'Adresse requise'
                }, status=400)
            
            result = maps_service.geocode_address(address, provider)
            
            if result:
                return JsonResponse({
                    'success': True,
                    'data': result
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Impossible de géocoder cette adresse'
                }, status=404)
                
        except GeocodingError as e:
            return JsonResponse({
                'success': False,
                'error': f'Erreur de géocodage: {str(e)}'
            }, status=500)
        except Exception as e:
            logger.error(f"Erreur inattendue dans GeocodeView: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Erreur interne du serveur'
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class OptimizeRouteView(MapsAPIView):
    """API pour l'optimisation d'itinéraires"""
    
    def post(self, request):
        try:
            data = self.get_json_data(request)
            waypoints_data = data.get('waypoints', [])
            provider = data.get('provider', None)
            
            if len(waypoints_data) < 2:
                return JsonResponse({
                    'success': False,
                    'error': 'Au moins 2 points requis'
                }, status=400)
            
            # Valider et formater les waypoints
            waypoints = []
            for i, wp in enumerate(waypoints_data):
                if 'lat' not in wp or 'lng' not in wp:
                    return JsonResponse({
                        'success': False,
                        'error': f'Coordonnées manquantes pour le point {i+1}'
                    }, status=400)
                
                waypoints.append({
                    'lat': float(wp['lat']),
                    'lng': float(wp['lng']),
                    'id': wp.get('id', i),
                    'name': wp.get('name', f'Point {i+1}'),
                    'address': wp.get('address', ''),
                    'type': wp.get('type', 'waypoint')
                })
            
            # Optimiser l'itinéraire
            result = maps_service.optimize_route(waypoints, provider)
            
            if result:
                return JsonResponse({
                    'success': True,
                    'data': result
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Impossible d\'optimiser cet itinéraire'
                }, status=500)
                
        except RouteOptimizationError as e:
            return JsonResponse({
                'success': False,
                'error': f'Erreur d\'optimisation: {str(e)}'
            }, status=500)
        except Exception as e:
            logger.error(f"Erreur inattendue dans OptimizeRouteView: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Erreur interne du serveur'
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class DistanceMatrixView(MapsAPIView):
    """API pour calculer une matrice de distances"""
    
    def post(self, request):
        try:
            data = self.get_json_data(request)
            origins = data.get('origins', [])
            destinations = data.get('destinations', [])
            provider = data.get('provider', None)
            
            if not origins or not destinations:
                return JsonResponse({
                    'success': False,
                    'error': 'Origines et destinations requises'
                }, status=400)
            
            # Valider les coordonnées
            for points, name in [(origins, 'origins'), (destinations, 'destinations')]:
                for i, point in enumerate(points):
                    if 'lat' not in point or 'lng' not in point:
                        return JsonResponse({
                            'success': False,
                            'error': f'Coordonnées manquantes dans {name}[{i}]'
                        }, status=400)
            
            result = maps_service.calculate_route_matrix(origins, destinations, provider)
            
            if result:
                return JsonResponse({
                    'success': True,
                    'data': result
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Impossible de calculer la matrice de distances'
                }, status=500)
                
        except Exception as e:
            logger.error(f"Erreur dans DistanceMatrixView: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Erreur interne du serveur'
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class TravelTimeView(MapsAPIView):
    """API pour estimer les temps de trajet"""
    
    def post(self, request):
        try:
            data = self.get_json_data(request)
            origin = data.get('origin', {})
            destination = data.get('destination', {})
            departure_time = data.get('departure_time', None)
            
            if not all([origin.get('lat'), origin.get('lng'), 
                       destination.get('lat'), destination.get('lng')]):
                return JsonResponse({
                    'success': False,
                    'error': 'Coordonnées origine et destination requises'
                }, status=400)
            
            result = maps_service.estimate_travel_time(origin, destination, departure_time)
            
            return JsonResponse({
                'success': True,
                'data': result
            })
                
        except Exception as e:
            logger.error(f"Erreur dans TravelTimeView: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Erreur interne du serveur'
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class CommandesGeocodeView(MapsAPIView):
    """API pour géocoder les adresses des commandes"""
    
    def post(self, request):
        try:
            data = self.get_json_data(request)
            commande_ids = data.get('commande_ids', [])
            provider = data.get('provider', None)
            
            if not commande_ids:
                return JsonResponse({
                    'success': False,
                    'error': 'IDs de commandes requis'
                }, status=400)
            
            # Récupérer les commandes
            commandes = Commande.objects.filter(id__in=commande_ids)
            
            results = []
            errors = []
            
            for commande in commandes:
                try:
                    # Géocoder origine
                    origine_coords = maps_service.geocode_address(commande.origine, provider)
                    
                    # Géocoder destination
                    destination_coords = maps_service.geocode_address(commande.destination, provider)
                    
                    if origine_coords and destination_coords:
                        results.append({
                            'commande_id': commande.id,
                            'origine': {
                                'address': commande.origine,
                                'coords': origine_coords
                            },
                            'destination': {
                                'address': commande.destination,
                                'coords': destination_coords
                            }
                        })
                    else:
                        errors.append({
                            'commande_id': commande.id,
                            'error': 'Impossible de géocoder les adresses'
                        })
                        
                except Exception as e:
                    errors.append({
                        'commande_id': commande.id,
                        'error': str(e)
                    })
            
            return JsonResponse({
                'success': True,
                'data': {
                    'geocoded': results,
                    'errors': errors,
                    'total_processed': len(commandes),
                    'success_count': len(results),
                    'error_count': len(errors)
                }
            })
            
        except Exception as e:
            logger.error(f"Erreur dans CommandesGeocodeView: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Erreur interne du serveur'
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class OptimizeTourneeView(MapsAPIView):
    """API pour optimiser une tournée complète"""
    
    def post(self, request):
        try:
            data = self.get_json_data(request)
            commande_ids = data.get('commande_ids', [])
            depot_coords = data.get('depot', {'lat': 33.5731, 'lng': -7.5898})  # Casablanca par défaut
            provider = data.get('provider', None)
            options = data.get('options', {})
            
            if not commande_ids:
                return JsonResponse({
                    'success': False,
                    'error': 'IDs de commandes requis'
                }, status=400)
            
            # Récupérer les commandes
            commandes = Commande.objects.filter(id__in=commande_ids).select_related('client')
            
            if not commandes.exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Aucune commande trouvée'
                }, status=404)
            
            # Préparer les waypoints
            waypoints = []
            geocoding_errors = []
            
            # Ajouter le dépôt
            waypoints.append({
                'lat': depot_coords['lat'],
                'lng': depot_coords['lng'],
                'id': 'depot',
                'name': 'Dépôt Central',
                'type': 'depot'
            })
            
            # Géocoder et ajouter chaque destination
            for commande in commandes:
                try:
                    destination_coords = maps_service.geocode_address(commande.destination, provider)
                    
                    if destination_coords:
                        waypoints.append({
                            'lat': destination_coords['lat'],
                            'lng': destination_coords['lng'],
                            'id': commande.id,
                            'name': f"Commande #{commande.id}",
                            'address': commande.destination,
                            'client': commande.client.get_full_name(),
                            'poids': float(commande.poids),
                            'priorite': commande.priorite,
                            'type': 'delivery'
                        })
                    else:
                        geocoding_errors.append({
                            'commande_id': commande.id,
                            'address': commande.destination,
                            'error': 'Géocodage échoué'
                        })
                        
                except Exception as e:
                    geocoding_errors.append({
                        'commande_id': commande.id,
                        'address': commande.destination,
                        'error': str(e)
                    })
            
            if len(waypoints) < 2:  # Juste le dépôt
                return JsonResponse({
                    'success': False,
                    'error': 'Aucune destination valide trouvée',
                    'geocoding_errors': geocoding_errors
                }, status=400)
            
            # Optimiser l'itinéraire
            optimization_result = maps_service.optimize_route(waypoints, provider)
            
            if not optimization_result:
                return JsonResponse({
                    'success': False,
                    'error': 'Échec de l\'optimisation'
                }, status=500)
            
            # Traiter les résultats
            optimized_waypoints = optimization_result.get('waypoints', [])
            
            # Créer la séquence d'étapes
            etapes = []
            for i, waypoint in enumerate(optimized_waypoints):
                if waypoint.get('type') == 'depot':
                    etapes.append({
                        'ordre': i + 1,
                        'type': 'depot' if i == 0 or i == len(optimized_waypoints) - 1 else 'retour',
                        'nom': waypoint['name'],
                        'coordonnees': {
                            'lat': waypoint['lat'],
                            'lng': waypoint['lng']
                        },
                        'duree_estimee': 0,  # Pas de temps de service au dépôt
                        'heure_estimee': self._calculate_estimated_time(i, options.get('heure_depart', '08:00'))
                    })
                else:
                    # Trouver la commande correspondante
                    commande = next((c for c in commandes if c.id == waypoint['id']), None)
                    if commande:
                        etapes.append({
                            'ordre': i + 1,
                            'type': 'livraison',
                            'commande_id': commande.id,
                            'nom': f"Livraison #{commande.id}",
                            'client': waypoint.get('client', ''),
                            'adresse': waypoint.get('address', ''),
                            'coordonnees': {
                                'lat': waypoint['lat'],
                                'lng': waypoint['lng']
                            },
                            'poids': waypoint.get('poids', 0),
                            'priorite': waypoint.get('priorite', 'normale'),
                            'duree_estimee': options.get('temps_service', 15),  # minutes
                            'heure_estimee': self._calculate_estimated_time(i, options.get('heure_depart', '08:00'), options.get('temps_service', 15))
                        })
            
            # Calculer les statistiques
            distance_totale = optimization_result.get('distance_km', 0)
            duree_totale = optimization_result.get('duration_minutes', 0)
            nb_livraisons = len([e for e in etapes if e['type'] == 'livraison'])
            
            # Estimer les économies par rapport à un itinéraire non optimisé
            estimated_savings = min(30, max(10, nb_livraisons * 3))  # Entre 10% et 30%
            
            result = {
                'success': True,
                'optimization': {
                    'provider': optimization_result.get('provider', 'fallback'),
                    'algorithm': 'TSP' if provider in ['google', 'openroute'] else 'nearest_neighbor'
                },
                'itineraire': {
                    'etapes': etapes,
                    'nb_etapes': len(etapes),
                    'nb_livraisons': nb_livraisons
                },
                'statistiques': {
                    'distance_totale_km': distance_totale,
                    'duree_totale_minutes': duree_totale,
                    'duree_totale_heures': round(duree_totale / 60, 2),
                    'heure_debut': options.get('heure_depart', '08:00'),
                    'heure_fin_estimee': self._calculate_end_time(options.get('heure_depart', '08:00'), duree_totale),
                    'economies_estimees_pct': estimated_savings,
                    'distance_economisee_km': round(distance_totale * estimated_savings / 100, 2)
                },
                'commandes_traitees': {
                    'total': len(commandes),
                    'geocodees': len(waypoints) - 1,  # Exclure le dépôt
                    'erreurs': len(geocoding_errors)
                }
            }
            
            # Ajouter les erreurs de géocodage s'il y en a
            if geocoding_errors:
                result['geocoding_errors'] = geocoding_errors
            
            # Ajouter les données de polyline/géométrie si disponibles
            if 'polyline' in optimization_result:
                result['geometry'] = {
                    'polyline': optimization_result['polyline']
                }
            elif 'geometry' in optimization_result:
                result['geometry'] = optimization_result['geometry']
            
            return JsonResponse(result)
            
        except Exception as e:
            logger.error(f"Erreur dans OptimizeTourneeView: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Erreur interne du serveur'
            }, status=500)
    
    def _calculate_estimated_time(self, step_index: int, start_time: str, service_time: int = 15) -> str:
        """Calculer l'heure estimée pour une étape"""
        try:
            from datetime import datetime, timedelta
            
            # Parser l'heure de début
            hour, minute = map(int, start_time.split(':'))
            base_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # Ajouter le temps de déplacement et de service pour chaque étape précédente
            total_minutes = step_index * (10 + service_time)  # 10 min de trajet + temps de service
            
            estimated_time = base_time + timedelta(minutes=total_minutes)
            return estimated_time.strftime('%H:%M')
            
        except:
            return start_time
    
    def _calculate_end_time(self, start_time: str, duration_minutes: int) -> str:
        """Calculer l'heure de fin estimée"""
        try:
            from datetime import datetime, timedelta
            
            hour, minute = map(int, start_time.split(':'))
            base_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            end_time = base_time + timedelta(minutes=duration_minutes)
            return end_time.strftime('%H:%M')
            
        except:
            return start_time

@method_decorator(csrf_exempt, name='dispatch')
class MapProvidersStatusView(MapsAPIView):
    """API pour obtenir le statut des providers cartographiques"""
    
    def get(self, request):
        try:
            status = maps_service.get_provider_status()
            
            return JsonResponse({
                'success': True,
                'data': status
            })
            
        except Exception as e:
            logger.error(f"Erreur dans MapProvidersStatusView: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Erreur interne du serveur'
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class SaveApiKeyView(MapsAPIView):
    """API pour sauvegarder une clé API (côté client seulement)"""
    
    def post(self, request):
        """
        Cette vue retourne juste un succès car la clé API
        est gérée côté client pour des raisons de sécurité
        """
        return JsonResponse({
            'success': True,
            'message': 'Clé API sauvegardée côté client'
        })

# Fonctions utilitaires pour les templates
def get_maps_config(request):
    """Obtenir la configuration des cartes pour les templates"""
    return {
        'providers_status': maps_service.get_provider_status(),
        'default_center': {'lat': 33.5731, 'lng': -7.5898},  # Casablanca
        'default_zoom': 11
    }

def planificateur_required(view_func):
    """Décorateur pour vérifier que l'utilisateur est un planificateur"""
    def _wrapped_view(request, *args, **kwargs):
        if 'user_id' not in request.session or request.session.get('role') != 'planificateur':
            return JsonResponse({
                'success': False,
                'error': 'Accès non autorisé'
            }, status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# Vues spécifiques pour les fonctionnalités avancées
@planificateur_required
@csrf_exempt
def bulk_optimize_commandes(request):
    """Optimisation en lot de plusieurs groupes de commandes"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'}, status=405)
    
    try:
        data = json.loads(request.body.decode('utf-8'))
        groupes = data.get('groupes', [])
        provider = data.get('provider', None)
        
        if not groupes:
            return JsonResponse({
                'success': False,
                'error': 'Aucun groupe de commandes fourni'
            }, status=400)
        
        resultats = []
        erreurs = []
        
        for i, groupe in enumerate(groupes):
            try:
                commande_ids = groupe.get('commande_ids', [])
                vehicule_id = groupe.get('vehicule_id')
                
                if not commande_ids:
                    erreurs.append({
                        'groupe_index': i,
                        'error': 'Aucune commande dans ce groupe'
                    })
                    continue
                
                # Simuler l'optimisation pour chaque groupe
                # (Ici on pourrait utiliser OptimizeTourneeView en interne)
                commandes = Commande.objects.filter(id__in=commande_ids)
                
                if commandes.exists():
                    resultats.append({
                        'groupe_index': i,
                        'vehicule_id': vehicule_id,
                        'commandes_count': len(commande_ids),
                        'distance_estimee': len(commande_ids) * 15 + 20,  # Estimation simple
                        'duree_estimee': len(commande_ids) * 25 + 30,
                        'economies_estimees': 15 + len(commande_ids) * 2
                    })
                else:
                    erreurs.append({
                        'groupe_index': i,
                        'error': 'Aucune commande valide trouvée'
                    })
                    
            except Exception as e:
                erreurs.append({
                    'groupe_index': i,
                    'error': str(e)
                })
        
        return JsonResponse({
            'success': True,
            'data': {
                'optimisations': resultats,
                'erreurs': erreurs,
                'total_groupes': len(groupes),
                'groupes_traites': len(resultats),
                'groupes_erreurs': len(erreurs)
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur dans bulk_optimize_commandes: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Erreur interne du serveur'
        }, status=500)

@planificateur_required
@csrf_exempt
def analyze_delivery_zones(request):
    """Analyser les zones de livraison pour optimiser la planification"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'}, status=405)
    
    try:
        data = json.loads(request.body.decode('utf-8'))
        date_debut = data.get('date_debut')
        date_fin = data.get('date_fin')
        
        # Récupérer les commandes de la période
        commandes = Commande.objects.filter(
            date_creation__range=[date_debut, date_fin],
            statut__in=['en_attente', 'planifiee']
        )
        
        # Analyser par zones
        zones_analysis = {}
        total_commandes = 0
        
        for commande in commandes:
            try:
                # Simplifier : détecter la zone par l'adresse
                destination_lower = commande.destination.lower()
                zone = 'autres'
                
                if 'casablanca' in destination_lower or 'casa' in destination_lower:
                    zone = 'casablanca'
                elif 'rabat' in destination_lower:
                    zone = 'rabat'
                elif 'marrakech' in destination_lower:
                    zone = 'marrakech'
                elif 'fes' in destination_lower or 'fez' in destination_lower:
                    zone = 'fes'
                elif 'tanger' in destination_lower:
                    zone = 'tanger'
                
                if zone not in zones_analysis:
                    zones_analysis[zone] = {
                        'commandes': [],
                        'total_poids': 0,
                        'urgentes': 0
                    }
                
                zones_analysis[zone]['commandes'].append({
                    'id': commande.id,
                    'poids': float(commande.poids),
                    'priorite': commande.priorite
                })
                zones_analysis[zone]['total_poids'] += float(commande.poids)
                
                if commande.priorite == 'urgente':
                    zones_analysis[zone]['urgentes'] += 1
                
                total_commandes += 1
                
            except Exception as e:
                logger.warning(f"Erreur analyse commande {commande.id}: {e}")
                continue
        
        # Calculer les métriques par zone
        zones_metrics = {}
        for zone, data in zones_analysis.items():
            nb_commandes = len(data['commandes'])
            zones_metrics[zone] = {
                'nom': zone.title(),
                'nb_commandes': nb_commandes,
                'pourcentage': round((nb_commandes / total_commandes) * 100, 1) if total_commandes > 0 else 0,
                'poids_total': round(data['total_poids'], 1),
                'poids_moyen': round(data['total_poids'] / nb_commandes, 1) if nb_commandes > 0 else 0,
                'urgentes': data['urgentes'],
                'vehicules_recommandes': max(1, nb_commandes // 6),  # 6 commandes par véhicule max
                'economies_potentielles': round(nb_commandes * 1.5, 1) if nb_commandes > 3 else 0
            }
        
        # Suggestions d'optimisation
        suggestions = []
        for zone, metrics in zones_metrics.items():
            if metrics['nb_commandes'] >= 5:
                suggestions.append(f"Zone {metrics['nom']}: {metrics['nb_commandes']} commandes - Groupement recommandé")
            if metrics['urgentes'] >= 2:
                suggestions.append(f"Zone {metrics['nom']}: {metrics['urgentes']} commandes urgentes - Priorité haute")
        
        return JsonResponse({
            'success': True,
            'data': {
                'periode': {
                    'debut': date_debut,
                    'fin': date_fin,
                    'total_commandes': total_commandes
                },
                'zones': zones_metrics,
                'suggestions': suggestions,
                'resume': {
                    'zone_principale': max(zones_metrics.keys(), key=lambda z: zones_metrics[z]['nb_commandes']) if zones_metrics else None,
                    'economies_totales_estimees': sum(m['economies_potentielles'] for m in zones_metrics.values()),
                    'vehicules_optimaux': sum(m['vehicules_recommandes'] for m in zones_metrics.values())
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur dans analyze_delivery_zones: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Erreur interne du serveur'
        }, status=500)