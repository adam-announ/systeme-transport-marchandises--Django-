# transport/middleware.py - Middleware personnalisé pour TransportPro

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

from .models import JournalActivite, ParametreSysteme

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """Middleware pour enregistrer les requêtes importantes"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Actions à enregistrer
        actions_to_log = [
            'creer_commande',
            'supprimer_commande', 
            'affecter_commande',
            'mettre_a_jour_statut',
            'notifier_incident',
            'login',
            'logout'
        ]
        
        start_time = time.time()
        
        response = self.get_response(request)
        
        # Enregistrer si c'est une action importante
        if (hasattr(request, 'resolver_match') and 
            request.resolver_match and 
            request.resolver_match.url_name in actions_to_log):
            
            self.log_activity(request, response, start_time)
        
        return response
    
    def log_activity(self, request, response, start_time):
        """Enregistrer l'activité dans le journal"""
        try:
            duration = time.time() - start_time
            
            # Ne pas enregistrer les utilisateurs anonymes pour certaines actions
            if isinstance(request.user, AnonymousUser):
                return
            
            # Déterminer le type d'action
            action_mapping = {
                'creer_commande': 'CREATE',
                'supprimer_commande': 'DELETE',
                'affecter_commande': 'ASSIGN',
                'mettre_a_jour_statut': 'UPDATE',
                'notifier_incident': 'CREATE',
                'login': 'LOGIN',
                'logout': 'LOGOUT'
            }
            
            action = action_mapping.get(request.resolver_match.url_name, 'UPDATE')
            
            # Extraire l'ID de l'objet si présent dans l'URL
            objet_id = None
            if 'pk' in request.resolver_match.kwargs:
                objet_id = request.resolver_match.kwargs['pk']
            elif 'commande_id' in request.resolver_match.kwargs:
                objet_id = request.resolver_match.kwargs['commande_id']
            elif 'mission_id' in request.resolver_match.kwargs:
                objet_id = request.resolver_match.kwargs['mission_id']
            
            # Créer l'entrée de journal
            JournalActivite.objects.create(
                utilisateur=request.user,
                action=action,
                objet_type=self.get_object_type(request.resolver_match.url_name),
                objet_id=objet_id,
                details=f"{request.method} {request.path} - {response.status_code} - {duration:.2f}s",
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement de l'activité: {e}")
    
    def get_object_type(self, url_name):
        """Déterminer le type d'objet concerné"""
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
        """Obtenir l'IP réelle du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class RateLimitingMiddleware:
    """Middleware pour limiter le nombre de requêtes"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limits = {
            'api': {'requests': 100, 'window': 3600},  # 100 req/heure pour l'API
            'login': {'requests': 5, 'window': 900},   # 5 tentatives/15min pour login
            'general': {'requests': 1000, 'window': 3600}  # 1000 req/heure général
        }
    
    def __call__(self, request):
        # Déterminer le type de limite à appliquer
        limit_type = self.get_limit_type(request)
        
        if limit_type and not self.check_rate_limit(request, limit_type):
            return JsonResponse(
                {'error': 'Trop de requêtes. Veuillez patienter.'},
                status=429
            )
        
        return self.get_response(request)
    
    def get_limit_type(self, request):
        """Déterminer le type de limitation selon l'URL"""
        path = request.path
        
        if path.startswith('/api/'):
            return 'api'
        elif 'login' in path:
            return 'login'
        elif request.user.is_authenticated:
            return None  # Pas de limitation pour les utilisateurs connectés
        else:
            return 'general'
    
    def check_rate_limit(self, request, limit_type):
        """Vérifier si la limite de taux est respectée"""
        try:
            # Identifier l'utilisateur (IP + User-Agent pour anonymes)
            if request.user.is_authenticated:
                identifier = f"user_{request.user.id}"
            else:
                ip = self.get_client_ip(request)
                user_agent_hash = hash(request.META.get('HTTP_USER_AGENT', ''))
                identifier = f"anon_{ip}_{user_agent_hash}"
            
            cache_key = f"rate_limit_{limit_type}_{identifier}"
            
            # Obtenir les paramètres de limitation
            limits = self.rate_limits.get(limit_type)
            if not limits:
                return True
            
            # Vérifier le cache
            current_count = cache.get(cache_key, 0)
            
            if current_count >= limits['requests']:
                return False
            
            # Incrémenter le compteur
            cache.set(cache_key, current_count + 1, limits['window'])
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur rate limiting: {e}")
            return True  # En cas d'erreur, autoriser la requête
    
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
        
        # URLs qui ne nécessitent pas de profil complet
        self.exempt_urls = [
            'index', 'login', 'logout', 'inscription', 'home_modern',
            'admin_dashboard', 'creer_compte', 'gestion_utilisateurs'
        ]
    
    def __call__(self, request):
        # Passer les requêtes non authentifiées
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # Passer les URLs exemptées
        if (hasattr(request, 'resolver_match') and 
            request.resolver_match and 
            request.resolver_match.url_name in self.exempt_urls):
            return self.get_response(request)
        
        # Vérifier le profil
        profile_check = self.check_user_profile(request.user)
        
        if not profile_check['complete']:
            return self.handle_incomplete_profile(request, profile_check)
        
        return self.get_response(request)
    
    def check_user_profile(self, user):
        """Vérifier si le profil utilisateur est complet"""
        if user.is_staff:
            return {'complete': True, 'type': 'staff'}
        
        # Vérifier le profil client
        if hasattr(user, 'client'):
            client = user.client
            if not client.telephone or not client.adresse:
                return {
                    'complete': False, 
                    'type': 'client',
                    'missing': ['téléphone', 'adresse']
                }
            return {'complete': True, 'type': 'client'}
        
        # Vérifier le profil transporteur
        if hasattr(user, 'transporteur'):
            transporteur = user.transporteur
            missing = []
            if not transporteur.matricule:
                missing.append('matricule')
            if not transporteur.type_vehicule:
                missing.append('type de véhicule')
            if not transporteur.capacite_charge:
                missing.append('capacité de charge')
            
            if missing:
                return {
                    'complete': False,
                    'type': 'transporteur', 
                    'missing': missing
                }
            return {'complete': True, 'type': 'transporteur'}
        
        # Utilisateur sans profil spécifique
        return {
            'complete': False,
            'type': 'none',
            'missing': ['profil utilisateur']
        }
    
    def handle_incomplete_profile(self, request, profile_check):
        """Gérer un profil incomplet"""
        # Pour les requêtes AJAX, retourner une réponse JSON
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'error': 'Profil incomplet',
                'type': profile_check['type'],
                'missing': profile_check.get('missing', [])
            }, status=400)
        
        # Pour les requêtes normales, rediriger
        if profile_check['type'] == 'none':
            messages.warning(request, 
                "Votre profil n'est pas encore configuré. "
                "Contactez l'administrateur pour activer votre compte."
            )
            return redirect('index')
        else:
            missing_fields = ', '.join(profile_check.get('missing', []))
            messages.warning(request, 
                f"Veuillez compléter votre profil {profile_check['type']}. "
                f"Champs manquants: {missing_fields}"
            )
            
            # Rediriger vers la page appropriée
            if profile_check['type'] == 'client':
                return redirect('client_dashboard')
            else:
                return redirect('dashboard_transporteur')


class SecurityHeadersMiddleware:
    """Middleware pour ajouter des en-têtes de sécurité"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Ajouter les en-têtes de sécurité
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # CSP pour les pages avec contenu dynamique
        if not request.path.startswith('/admin/'):
            response['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self';"
            )
        
        return response


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
            
            # Permettre l'accès aux URLs de maintenance
            exempt_paths = ['/admin/', '/maintenance/']
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
            param = ParametreSysteme.objects.get(nom='mode_maintenance')
            return param.valeur.lower() in ['true', '1', 'oui', 'actif']
        except ParametreSysteme.DoesNotExist:
            return False
    
    def get_maintenance_message(self):
        """Obtenir le message de maintenance"""
        try:
            param = ParametreSysteme.objects.get(nom='message_maintenance')
            return param.valeur
        except ParametreSysteme.DoesNotExist:
            return "Site en maintenance. Veuillez réessayer plus tard."


class PerformanceMonitoringMiddleware:
    """Middleware pour surveiller les performances"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        
        response = self.get_response(request)
        
        duration = time.time() - start_time
        
        # Enregistrer les requêtes lentes
        slow_threshold = 2.0  # 2 secondes
        if duration > slow_threshold:
            self.log_slow_request(request, duration)
        
        # Ajouter l'en-tête de timing
        response['X-Response-Time'] = f"{duration:.3f}s"
        
        return response
    
    def log_slow_request(self, request, duration):
        """Enregistrer les requêtes lentes"""
        logger.warning(
            f"Requête lente détectée: {request.method} {request.path} "
            f"- {duration:.2f}s - User: {request.user}"
        )
        
        # Optionnel: stocker en cache pour analyse
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