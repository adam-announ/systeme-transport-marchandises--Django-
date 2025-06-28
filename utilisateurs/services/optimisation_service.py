import math
import requests
from django.conf import settings
from typing import List, Dict, Tuple
from ..models import Commande, Vehicule, EtapeTournee

class OptimisationService:
    def __init__(self):
        self.google_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    
    def optimiser_tournee(self, commandes: List[Commande], vehicule: Vehicule, depot: Dict[str, float]) -> Dict:
        """Optimise l'ordre des livraisons pour minimiser la distance"""
        if not commandes:
            return {'success': False, 'message': 'Aucune commande à optimiser'}
        
        # Vérifier la capacité du véhicule
        poids_total = sum(float(cmd.poids) for cmd in commandes)
        if poids_total > float(vehicule.capacite_max):
            return {
                'success': False, 
                'message': f'Poids total ({poids_total}kg) dépasse la capacité ({vehicule.capacite_max}kg)'
            }
        
        # Créer la liste des points
        points = [depot]  # Point de départ
        for cmd in commandes:
            points.append({
                'lat': self._geocode_address(cmd.destination)['lat'],
                'lng': self._geocode_address(cmd.destination)['lng'],
                'commande_id': cmd.id,
                'address': cmd.destination
            })
        
        # Algorithme d'optimisation simple (plus proche voisin)
        ordre_optimise = self._algorithme_plus_proche_voisin(points)
        
        # Calculer les distances et temps
        distance_totale, duree_totale = self._calculer_metriques(ordre_optimise)
        
        return {
            'success': True,
            'ordre_optimise': ordre_optimise[1:],  # Exclure le dépôt
            'distance_totale': distance_totale,
            'duree_totale': duree_totale,
            'economies': self._calculer_economies(points, ordre_optimise)
        }
    
    def _algorithme_plus_proche_voisin(self, points: List[Dict]) -> List[Dict]:
        """Algorithme du plus proche voisin pour optimiser l'ordre"""
        if len(points) <= 2:
            return points
        
        non_visites = points[1:].copy()  # Exclure le dépôt
        parcours = [points[0]]  # Commencer par le dépôt
        
        while non_visites:
            point_actuel = parcours[-1]
            plus_proche = min(non_visites, key=lambda p: self._distance_euclidienne(point_actuel, p))
            parcours.append(plus_proche)
            non_visites.remove(plus_proche)
        
        return parcours
    
    def _distance_euclidienne(self, point1: Dict, point2: Dict) -> float:
        """Calcule la distance euclidienne entre deux points"""
        lat1, lng1 = point1['lat'], point1['lng']
        lat2, lng2 = point2['lat'], point2['lng']
        
        # Conversion en radians
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        
        # Formule de Haversine
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # Rayon de la Terre en km
        
        return c * r
    
    def _geocode_address(self, address: str) -> Dict[str, float]:
        """Géocode une adresse (version simplifiée)"""
        # Coordonnées par défaut pour Casablanca
        default_coords = {'lat': 33.5731, 'lng': -7.5898}
        
        if not self.google_api_key:
            return default_coords
        
        try:
            url = f"https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                'address': address,
                'key': self.google_api_key,
                'region': 'ma'
            }
            
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                location = data['results'][0]['geometry']['location']
                return {'lat': location['lat'], 'lng': location['lng']}
        
        except Exception:
            pass
        
        return default_coords
    
    def _calculer_metriques(self, points: List[Dict]) -> Tuple[float, float]:
        """Calcule la distance totale et la durée estimée"""
        distance_totale = 0
        
        for i in range(len(points) - 1):
            distance_totale += self._distance_euclidienne(points[i], points[i + 1])
        
        # Durée estimée (vitesse moyenne 50 km/h + temps d'arrêt)
        duree_totale = (distance_totale / 50) + (len(points) * 0.25)  # 15 min par arrêt
        
        return round(distance_totale, 2), round(duree_totale, 2)
    
    def _calculer_economies(self, points_originaux: List[Dict], points_optimises: List[Dict]) -> Dict:
        """Calcule les économies réalisées par l'optimisation"""
        # Distance sans optimisation (ordre original)
        distance_originale, _ = self._calculer_metriques(points_originaux)
        
        # Distance avec optimisation
        distance_optimisee, _ = self._calculer_metriques(points_optimises)
        
        economie_km = distance_originale - distance_optimisee
        economie_pourcentage = (economie_km / distance_originale) * 100 if distance_originale > 0 else 0
        
        return {
            'distance_economisee': round(economie_km, 2),
            'pourcentage_economie': round(economie_pourcentage, 1),
            'temps_economise': round(economie_km / 50, 2)  # heures
        }
    
    def creer_tournee_optimisee(self, commandes: List[Commande], transporteur, vehicule, planificateur) -> Dict:
        """Crée une tournée optimisée"""
        from ..models import Tournee, EtapeTournee
        from django.utils import timezone
        from datetime import timedelta
        
        depot = {'lat': 33.5731, 'lng': -7.5898, 'address': 'Dépôt Principal'}
        
        # Optimiser l'ordre
        resultat = self.optimiser_tournee(commandes, vehicule, depot)
        
        if not resultat['success']:
            return resultat
        
        try:
            # Créer la tournée
            tournee = Tournee.objects.create(
                nom=f"Tournée {timezone.now().strftime('%Y%m%d_%H%M')}",
                planificateur=planificateur,
                transporteur=transporteur,
                vehicule=vehicule,
                date_debut_prevue=timezone.now() + timedelta(hours=1),
                date_fin_prevue=timezone.now() + timedelta(hours=1 + resultat['duree_totale']),
                distance_totale=resultat['distance_totale'],
                duree_prevue=timedelta(hours=resultat['duree_totale']),
                optimisee=True
            )
            
            # Créer les étapes
            heure_actuelle = tournee.date_debut_prevue
            
            # Étape dépôt (départ)
            EtapeTournee.objects.create(
                tournee=tournee,
                ordre=0,
                type_etape='depot',
                adresse=depot['address'],
                latitude=depot['lat'],
                longitude=depot['lng'],
                heure_prevue=heure_actuelle,
                duree_prevue=timedelta(minutes=15)
            )
            
            # Étapes de livraison
            for i, point in enumerate(resultat['ordre_optimise'], 1):
                heure_actuelle += timedelta(minutes=30)  # Temps de trajet estimé
                
                commande = next(cmd for cmd in commandes if cmd.id == point['commande_id'])
                
                EtapeTournee.objects.create(
                    tournee=tournee,
                    commande=commande,
                    ordre=i,
                    type_etape='livraison',
                    adresse=point['address'],
                    latitude=point['lat'],
                    longitude=point['lng'],
                    heure_prevue=heure_actuelle,
                    duree_prevue=timedelta(minutes=15)
                )
                
                # Mettre à jour le statut de la commande
                commande.statut = 'planifiee'
                commande.planificateur = planificateur
                commande.date_livraison_planifiee = heure_actuelle
                commande.save()
            
            return {
                'success': True,
                'tournee_id': tournee.id,
                'message': f'Tournée créée avec {len(commandes)} commandes',
                'economies': resultat['economies']
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Erreur lors de la création: {str(e)}'
            }