# transport/middleware.py - Middleware optimisé et centralisé

import time
import json
import logging
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth.models import AnonymousUser
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from datetime import timedelta

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware:
    """Middleware pour ajouter des en-têtes de sécurité"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # En-têtes de sécurité
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # CSP simplifié
        if not request.path.startswith('/django-admin/'):
            response['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
            )
        
        return response

class RateLimitingMiddleware:
    """Middleware pour limiter le taux de requêtes"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limits = {
            'api': {'requests': 100, 'window': 3600},  # 100 req/heure pour l'API
            'login': {'requests': 5, 'window': 900},   # 5 tentatives/15min pour login
            'general': {'requests': 1000, 'window': 3600}  # 1000 req/heure général
        }
    
    def __call__(self, request):
        # Déterminer le type de limite
        limit_type = self.get_limit_type(request)
        
        if limit_type and not self.check_rate_limit(request, limit_type):
            return JsonResponse(
                {'error': 'Trop de requêtes. Veuillez patienter.'},
                status=429
            )
        
        return self.get_response(request)
    
    def get_limit_type(self, request):
        """Déterminer le type de limitation"""
        path = request.path
        
        if path.startswith('/api/'):
            return 'api'
        elif 'login' in path:
            return 'login'
        elif request.user.is_authenticated:
            return None  # Pas de limitation pour utilisateurs connectés
        else:
            return 'general'
    
    def check_rate_limit(self, request, limit_type):
        """Vérifier le taux de requêtes"""
        try:
            # Identifier l'utilisateur
            if request.user.is_authenticated:
                identifier = f"user_{request.user.id}"
            else:
                ip = self.get_client_ip(request)
                identifier = f"ip_{ip}"
            
            cache_key = f"rate_limit_{limit_type}_{identifier}"
            limits = self.rate_limits.get(limit_type)
            
            if not limits:
                return True
            
            current_count = cache.get(cache_key, 0)
            
            if current_count >= limits['requests']:
                return False
            
            cache.set(cache_key, current_count + 1, limits['window'])
            return True
            
        except Exception as e:
            logger.error(f"Erreur rate limiting: {e}")
            return True
    
    def get_client_ip(self, request):
        """Obtenir l'IP du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class ProfileCompletionMiddleware:
    """Middleware pour vérifier la complétion des profils"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs exemptées
        self.exempt_urls = [
            'index', 'login', 'logout', 'inscription',
            'admin_dashboard', 'django-admin'
        ]
    
    def __call__(self, request):
        # Passer les requêtes non authentifiées
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # Passer les URLs exemptées
        if self.is_exempt_url(request):
            return self.get_response(request)
        
        # Vérifier le profil
        profile_status = self.check_user_profile(request.user)
        
        if not profile_status['complete']:
            return self.handle_incomplete_profile(request, profile_status)
        
        return self.get_response(request)
    
    def is_exempt_url(self, request):
        """Vérifier si l'URL est exemptée"""
        if hasattr(request, 'resolver_match') and request.resolver_match:
            url_name = request.resolver_match.url_name
            return url_name in self.exempt_urls
        
        # Vérifier les préfixes d'URL
        path = request.path
        return (path.startswith('/django-admin/') or 
                path.startswith('/api/') or
                path in ['/', '/login/', '/logout/', '/inscription/'])
    
    def check_user_profile(self, user):
        """Vérifier la complétion du profil"""
        if user.is_staff:
            return {'complete': True, 'type': 'staff'}
        
        # Vérifier profil client
        if hasattr(user, 'client'):
            client = user.client
            if not client.telephone or not client.adresse:
                return {
                    'complete': False,
                    'type': 'client',
                    'missing': ['téléphone', 'adresse']
                }
            return {'complete': True, 'type': 'client'}
        
        # Vérifier profil transporteur
        if hasattr(user, 'transporteur'):
            transporteur = user.transporteur
            missing = []
            if not transporteur.matricule:
                missing.append('matricule')
            if not transporteur.type_vehicule:
                missing.append('type véhicule')
            if not transporteur.capacite_charge:
                missing.append('capacité charge')
            
            if missing:
                return {
                    'complete': False,
                    'type': 'transporteur',
                    'missing': missing
                }
            return {'complete': True, 'type': 'transporteur'}
        
        return {
            'complete': False,
            'type': 'none',
            'missing': ['profil utilisateur']
        }
    
    def handle_incomplete_profile(self, request, profile_status):
        """Gérer un profil incomplet"""
        # Pour les requêtes AJAX
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'error': 'Profil incomplet',
                'type': profile_status['type'],
                'missing': profile_status.get('missing', [])
            }, status=400)
        
        # Pour les requêtes normales
        if profile_status['type'] == 'none':
            messages.warning(request,
                "Votre profil n'est pas configuré. "
                "Contactez l'administrateur."
            )
            return redirect('index')
        else:
            missing = ', '.join(profile_status.get('missing', []))
            messages.warning(request,
                f"Veuillez compléter votre profil {profile_status['type']}. "
                f"Champs manquants: {missing}"
            )
            
            # Redirection selon le type
            if profile_status['type'] == 'client':
                return redirect('client_dashboard')
            else:
                return redirect('transporteur_dashboard')

class PerformanceMonitoringMiddleware:
    """Middleware pour surveiller les performances"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.slow_threshold = 2.0  # 2 secondes
    
    def __call__(self, request):
        start_time = time.time()
        
        response = self.get_response(request)
        
        duration = time.time() - start_time
        
        # Enregistrer les requêtes lentes
        if duration > self.slow_threshold:
            self.log_slow_request(request, duration)
        
        # Ajouter l'en-tête de timing
        response['X-Response-Time'] = f"{duration:.3f}s"
        
        return response
    
    def log_slow_request(self, request, duration):
        """Enregistrer les requêtes lentes"""
        logger.warning(
            f"Requête lente: {request.method} {request.path} "
            f"- {duration:.2f}s - User: {request.user}"
        )
        
        # Stocker en cache pour analyse
        cache_key = f"slow_requests_{timezone.now().strftime('%Y%m%d')}"
        slow_requests = cache.get(cache_key, [])
        slow_requests.append({
            'path': request.path,
            'method': request.method,
            'duration': duration,
            'timestamp': timezone.now().isoformat(),
            'user': str(request.user)
        })
        
        # Garder seulement les 100 dernières
        if len(slow_requests) > 100:
            slow_requests = slow_requests[-100:]
        
        cache.set(cache_key, slow_requests, 86400)  # 24h

class RequestLoggingMiddleware:
    """Middleware pour enregistrer les requêtes importantes"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Actions à enregistrer
        self.actions_to_log = [
            'creer_commande',
            'affecter_commande',
            'mettre_a_jour_statut',
            'notifier_incident',
            'login',
            'logout'
        ]
    
    def __call__(self, request):
        start_time = time.time()
        
        response = self.get_response(request)
        
        # Enregistrer si action importante
        if (hasattr(request, 'resolver_match') and 
            request.resolver_match and 
            request.resolver_match.url_name in self.actions_to_log):
            
            self.log_activity(request, response, start_time)
        
        return response
    
    def log_activity(self, request, response, start_time):
        """Enregistrer l'activité"""
        try:
            duration = time.time() - start_time
            
            if isinstance(request.user, AnonymousUser):
                return
            
            # Créer l'entrée de journal
            from .models import JournalActivite
            
            action_mapping = {
                'creer_commande': 'CREATE',
                'affecter_commande': 'ASSIGN',
                'mettre_a_jour_statut': 'UPDATE',
                'notifier_incident': 'CREATE',
                'login': 'LOGIN',
                'logout': 'LOGOUT'
            }
            
            action = action_mapping.get(request.resolver_match.url_name, 'UPDATE')
            
            JournalActivite.objects.create(
                utilisateur=request.user,
                action=action,
                objet_type=self.get_object_type(request.resolver_match.url_name),
                details=f"{request.method} {request.path} - {response.status_code} - {duration:.2f}s",
                ip_address=self.get_client_ip(request)
            )
            
        except Exception as e:
            logger.error(f"Erreur logging activité: {e}")
    
    def get_object_type(self, url_name):
        """Déterminer le type d'objet"""
        if 'commande' in url_name:
            return 'Commande'
        elif 'mission' in url_name:
            return 'Mission'
        elif 'incident' in url_name:
            return 'Incident'
        elif 'login' in url_name or 'logout' in url_name:
            return 'Authentification'
        else:
            return 'Autre'
    
    def get_client_ip(self, request):
        """Obtenir l'IP du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class MaintenanceModeMiddleware:
    """Middleware pour le mode maintenance"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Vérifier si le mode maintenance est activé
        if self.is_maintenance_mode():
            # Permettre l'accès aux admins
            if request.user.is_authenticated and request.user.is_staff:
                return self.get_response(request)
            
            # Permettre certaines URLs
            exempt_paths = ['/django-admin/', '/api/auth/']
            if any(request.path.startswith(path) for path in exempt_paths):
                return self.get_response(request)
            
            # Afficher la page de maintenance
            from django.template.response import TemplateResponse
            return TemplateResponse(
                request,
                'maintenance.html',
                {'maintenance_message': self.get_maintenance_message()},
                status=503
            )
        
        return self.get_response(request)
    
    def is_maintenance_mode(self):
        """Vérifier si le mode maintenance est activé"""
        try:
            from .models import ParametreSysteme
            param = ParametreSysteme.objects.get(nom='mode_maintenance')
            return param.valeur.lower() in ['true', '1', 'oui', 'actif']
        except:
            return False
    
    def get_maintenance_message(self):
        """Obtenir le message de maintenance"""
        try:
            from .models import ParametreSysteme
            param = ParametreSysteme.objects.get(nom='message_maintenance')
            return param.valeur
        except:
            return "Site en maintenance. Veuillez réessayer plus tard."