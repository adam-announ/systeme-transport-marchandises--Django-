# Nouveau fichier: utilisateurs/services/optimisation_service.py

import math
from typing import List, Dict, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from ..models import Commande, Vehicule, EtapeTournee, Tournee

class OptimisationService:
    """Service pour l'optimisation des tournées et la planification intelligente"""
    
    @staticmethod
    def calculer_distance_haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calcule la distance entre deux points GPS en utilisant la formule de Haversine"""
        if not all([lat1, lng1, lat2, lng2]):
            return 0.0
            
        # Convertir en radians
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        
        # Différences
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        
        # Formule de Haversine
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Rayon de la Terre en km
        r = 6371