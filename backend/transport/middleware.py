# transport/middleware.py
import json
import logging
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import User
from .models import Journal

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(MiddlewareMixin):
    """Middleware pour enregistrer les actions utilisateur"""
    
    def process_request(self, request):
        # Enregistrer l'adresse IP et user agent
        request.client_ip = self.get_client_ip(request)
        request.user_agent = request.META.get('HTTP_USER_AGENT', '')
        return None
    
    def process_response(self, request, response):
        # Logger les actions importantes
        if hasattr(request, 'user') and request.user.is_authenticated:
            if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                self.log_user_action(request, response)
        return response
    
    def get_client_ip(self, request):
        """Obtenir l'adresse IP réelle du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def log_user_action(self, request, response):
        """Enregistrer l'action dans le journal"""
        try:
            action_map = {
                'POST': 'creation',
                'PUT': 'modification',
                'PATCH': 'modification',
                'DELETE': 'suppression'
            }
            
            action = action_map.get(request.method, 'action')
            
            Journal.objects.create(
                utilisateur=request.user,
                action=action,
                modele=self.extract_model_from_path(request.path),
                description=f"{action} via {request.method} {request.path}",
                adresse_ip=request.client_ip,
                user_agent=request.user_agent[:500]  # Limiter la taille
            )
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement du journal: {e}")
    
    def extract_model_from_path(self, path):
        """Extraire le nom du modèle depuis le chemin"""
        parts = path.strip('/').split('/')
        if len(parts) >= 2 and parts[0] == 'api':
            return parts[1]
        return 'inconnu'