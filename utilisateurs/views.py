from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.hashers import check_password
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from .models import (
    User, Commande, Vehicule, Livraison, Notification, 
    Tournee, EtapeTournee, HistoriqueAction
)
from .services.api_service import TransportAPIService
from .services.optimisation_service import OptimisationService
from .services.planification_service import PlanificationService

# ==================== DÉCORATEURS ====================

def admin_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if 'user_id' not in request.session or request.session.get('role') != 'admin':
            messages.error(request, 'Accès non autorisé.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def transporteur_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if 'user_id' not in request.session or request.session.get('role') != 'transporteur':
            messages.error(request, 'Accès non autorisé.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def client_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if 'user_id' not in request.session or request.session.get('role') != 'client':
            messages.error(request, 'Accès non autorisé.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def planificateur_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if 'user_id' not in request.session or request.session.get('role') != 'planificateur':
            messages.error(request, 'Accès non autorisé.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# ==================== VUES PUBLIQUES ====================

def accueil(request):
    return render(request, 'public/index.html')

def gestion_commandes(request):
    return render(request, 'public/gestion_commandes.html')

def optimisation_tournees(request):
    return render(request, 'public/optimisation_tournees.html')

def suivi_temps_reel(request):
    return render(request, 'public/suivi_temps_reel.html')

def contact(request):
    return render(request, 'public/contact.html')

# ==================== AUTHENTIFICATION ====================

def login_view(request):
    # Redirection si déjà connecté
    if 'user_id' in request.session:
        role = request.session.get('role')
        return redirect(f'{role}_dashboard')
    
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        
        try:
            user = User.objects.get(username=username, is_active=True)
            if check_password(password, user.password):
                # Création de la session
                request.session['user_id'] = user.id
                request.session['username'] = user.username
                request.session['role'] = user.role
                request.session['first_name'] = user.first_name
                request.session['last_name'] = user.last_name
                
                # Enregistrer l'action de connexion
                HistoriqueAction.objects.create(
                    utilisateur=user,
                    action='login',
                    description=f'Connexion utilisateur {user.username}',
                    table_name='users',
                    record_id=user.id,
                    adresse_ip=request.META.get('REMOTE_ADDR')
                )
                
                return redirect(f'{user.role}_dashboard')
            else:
                messages.error(request, 'Mot de passe incorrect.')
        except User.DoesNotExist:
            messages.error(request, 'Nom d\'utilisateur introuvable.')
    
    return render(request, 'auth/login.html')

def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        role = request.POST['role']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        phone = request.POST.get('phone', '')
        
        # Validation
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Ce nom d\'utilisateur existe déjà.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Cet email est déjà utilisé.')
        else:
            user = User.objects.create(
                username=username,
                email=email,
                password=password,
                role=role,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                is_active=True
            )
            
            messages.success(request, 'Compte créé avec succès ! Vous pouvez maintenant vous connecter.')
            return redirect('login')
    
    return render(request, 'auth/register.html')

def logout_view(request):
    if 'user_id' in request.session:
        # Enregistrer la déconnexion
        try:
            user = User.objects.get(id=request.session['user_id'])
            HistoriqueAction.objects.create(
                utilisateur=user,
                action='logout',
                description=f'Déconnexion utilisateur {user.username}',
                table_name='users',
                record_id=user.id,
                adresse_ip=request.META.get('REMOTE_ADDR')
            )
        except:
            pass
        
        request.session.flush()
    return redirect('accueil')

# ==================== VUES ADMIN ====================

@admin_required
def admin_dashboard(request):
    # Statistiques générales
    stats = {
        'total_users': User.objects.filter(is_active=True).count(),
        'commandes_mois': Commande.objects.filter(
            date_creation__gte=timezone.now().replace(day=1)
        ).count(),
        'livraisons_cours': Livraison.objects.filter(statut='en_cours').count(),
        'tournees_actives': Tournee.objects.filter(
            statut__in=['planifiee', 'en_cours']
        ).count(),
        'revenus_mois': Commande.objects.filter(
            date_creation__gte=timezone.now().replace(day=1),
            statut='livree'
        ).aggregate(total=Sum('prix'))['total'] or 0
    }
    
    # Commandes récentes
    recent_commandes = Commande.objects.select_related('client', 'transporteur').order_by('-date_creation')[:10]
    
    # Répartition par rôle
    users_by_role = User.objects.filter(is_active=True).values('role').annotate(count=Count('id'))
    
    # Notifications système
    notifications_system = Notification.objects.filter(
        type_notification='system'
    ).order_by('-date_creation')[:5]
    
    context = {
        'stats': stats,
        'recent_commandes': recent_commandes,
        'users_by_role': {item['role']: item['count'] for item in users_by_role},
        'notifications_system': notifications_system
    }
    return render(request, 'admin/admin_dashboard.html', context)

@admin_required
def admin_users(request):
    # Filtres
    role_filter = request.GET.get('role', '')
    search = request.GET.get('search', '')
    
    users = User.objects.all()
    
    if role_filter:
        users = users.filter(role=role_filter)
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    users = users.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    users_page = paginator.get_page(page_number)
    
    context = {
        'users': users_page,
        'role_filter': role_filter,
        'search': search,
        'roles': User.ROLE_CHOICES
    }
    return render(request, 'admin/admin_users.html', context)

@admin_required
def admin_create_user(request):
    if request.method == 'POST':
        try:
            username = request.POST['username']
            email = request.POST['email']
            
            # Validation
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Ce nom d\'utilisateur existe déjà.')
                return render(request, 'admin/admin_create_user.html')
            
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Cet email est déjà utilisé.')
                return render(request, 'admin/admin_create_user.html')
            
            user = User.objects.create(
                username=username,
                email=email,
                password=request.POST['password'],
                role=request.POST['role'],
                first_name=request.POST.get('first_name', ''),
                last_name=request.POST.get('last_name', ''),
                phone=request.POST.get('phone', ''),
                is_active=request.POST.get('is_active') == 'on'
            )
            
            # Enregistrer l'action
            HistoriqueAction.objects.create(
                utilisateur_id=request.session['user_id'],
                action='create',
                description=f'Création utilisateur {username}',
                table_name='users',
                record_id=user.id
            )
            
            messages.success(request, f'Utilisateur {username} créé avec succès!')
            return redirect('admin_users')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la création: {str(e)}')
    
    context = {
        'roles': User.ROLE_CHOICES
    }
    return render(request, 'admin/admin_create_user.html', context)

@admin_required
def admin_edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        try:
            email = request.POST['email']
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                messages.error(request, 'Cet email est déjà utilisé par un autre utilisateur.')
            else:
                # Sauvegarder les anciennes valeurs
                old_values = {
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                    'phone': user.phone,
                    'role': user.role,
                    'is_active': user.is_active
                }
                
                # Mettre à jour
                user.first_name = request.POST.get('first_name', '')
                user.last_name = request.POST.get('last_name', '')
                user.email = email
                user.phone = request.POST.get('phone', '')
                user.role = request.POST['role']
                user.is_active = request.POST.get('is_active') == 'on'
                
                user.save()
                
                # Enregistrer l'action
                HistoriqueAction.objects.create(
                    utilisateur_id=request.session['user_id'],
                    action='update',
                    description=f'Modification utilisateur {user.username}',
                    table_name='users',
                    record_id=user.id,
                    ancien_valeur=old_values,
                    nouvelle_valeur={
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'email': user.email,
                        'phone': user.phone,
                        'role': user.role,
                        'is_active': user.is_active
                    }
                )
                
                messages.success(request, 'Utilisateur mis à jour avec succès!')
                return redirect('admin_users')
                
        except Exception as e:
            messages.error(request, f'Erreur lors de la mise à jour: {str(e)}')
    
    context = {
        'user': user,
        'roles': User.ROLE_CHOICES
    }
    return render(request, 'admin/admin_edit_user.html', context)

@admin_required
@require_http_methods(["POST"])
def admin_toggle_user(request, user_id):
    try:
        user = get_object_or_404(User, id=user_id)
        user.is_active = not user.is_active
        user.save()
        
        # Enregistrer l'action
        HistoriqueAction.objects.create(
            utilisateur_id=request.session['user_id'],
            action='status_change',
            description=f'Changement statut utilisateur {user.username}: {"activé" if user.is_active else "désactivé"}',
            table_name='users',
            record_id=user.id
        )
        
        return JsonResponse({
            'success': True,
            'new_status': user.is_active,
            'message': f'Utilisateur {"activé" if user.is_active else "désactivé"} avec succès'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@admin_required
def admin_commandes(request):
    # Filtres
    statut_filter = request.GET.get('statut', '')
    transporteur_filter = request.GET.get('transporteur', '')
    date_filter = request.GET.get('date', '')
    
    commandes = Commande.objects.select_related('client', 'transporteur')
    
    if statut_filter:
        commandes = commandes.filter(statut=statut_filter)
    if transporteur_filter:
        commandes = commandes.filter(transporteur_id=transporteur_filter)
    if date_filter:
        commandes = commandes.filter(date_creation__date=date_filter)
    
    commandes = commandes.order_by('-date_creation')
    
    # Pagination
    paginator = Paginator(commandes, 20)
    page_number = request.GET.get('page')
    commandes_page = paginator.get_page(page_number)
    
    # Données pour les filtres
    transporteurs = User.objects.filter(role='transporteur', is_active=True)
    
    context = {
        'commandes': commandes_page,
        'transporteurs': transporteurs,
        'statuts': Commande.STATUS_CHOICES,
        'statut_filter': statut_filter,
        'transporteur_filter': transporteur_filter,
        'date_filter': date_filter
    }
    return render(request, 'admin/admin_commandes.html', context)

@admin_required
def admin_reports(request):
    # Période par défaut: 30 derniers jours
    date_fin = timezone.now()
    date_debut = date_fin - timedelta(days=30)
    
    # Statistiques de performance
    stats_periode = {
        'commandes_total': Commande.objects.filter(
            date_creation__range=[date_debut, date_fin]
        ).count(),
        'commandes_livrees': Commande.objects.filter(
            date_creation__range=[date_debut, date_fin],
            statut='livree'
        ).count(),
        'tournees_total': Tournee.objects.filter(
            date_creation__range=[date_debut, date_fin]
        ).count(),
        'distance_totale': Tournee.objects.filter(
            date_creation__range=[date_debut, date_fin]
        ).aggregate(total=Sum('distance_totale'))['total'] or 0
    }
    
    # Calcul du taux de réussite
    if stats_periode['commandes_total'] > 0:
        stats_periode['taux_reussite'] = round(
            (stats_periode['commandes_livrees'] / stats_periode['commandes_total']) * 100, 2
        )
    else:
        stats_periode['taux_reussite'] = 0
    
    # Performance par transporteur
    transporteurs_perf = User.objects.filter(role='transporteur', is_active=True).annotate(
        nb_livraisons=Count('commandes_transporteur', filter=Q(
            commandes_transporteur__statut='livree',
            commandes_transporteur__date_creation__range=[date_debut, date_fin]
        )),
        nb_total=Count('commandes_transporteur', filter=Q(
            commandes_transporteur__date_creation__range=[date_debut, date_fin]
        ))
    )
    
    context = {
        'stats_periode': stats_periode,
        'transporteurs_perf': transporteurs_perf,
        'date_debut': date_debut.strftime('%Y-%m-%d'),
        'date_fin': date_fin.strftime('%Y-%m-%d')
    }
    return render(request, 'admin/admin_reports.html', context)

@admin_required
def admin_system_config(request):
    if request.method == 'POST':
        # Traitement de la configuration système
        messages.success(request, 'Configuration mise à jour avec succès!')
    
    context = {}
    return render(request, 'admin/admin_system_config.html', context)

@admin_required
def admin_notifications(request):
    # Notifications système récentes
    notifications = Notification.objects.filter(
        type_notification__in=['system', 'incident']
    ).order_by('-date_creation')
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    notifications_page = paginator.get_page(page_number)
    
    context = {
        'notifications': notifications_page
    }
    return render(request, 'admin/admin_notifications.html', context)

# ==================== VUES CLIENT ====================

@client_required
def client_dashboard(request):
    user_id = request.session['user_id']
    
    # Statistiques du client
    stats = {
        'commandes_total': Commande.objects.filter(client_id=user_id).count(),
        'commandes_en_cours': Commande.objects.filter(
            client_id=user_id,
            statut__in=['en_attente', 'affectee', 'planifiee', 'en_cours']
        ).count(),
        'commandes_livrees': Commande.objects.filter(
            client_id=user_id,
            statut='livree'
        ).count(),
        'depenses_totales': Commande.objects.filter(
            client_id=user_id,
            prix__isnull=False
        ).aggregate(total=Sum('prix'))['total'] or 0
    }
    
    # Commandes récentes
    commandes_recentes = Commande.objects.filter(
        client_id=user_id
    ).select_related('transporteur').order_by('-date_creation')[:5]
    
    # Notifications non lues
    notifications = Notification.objects.filter(
        utilisateur_id=user_id,
        lu=False
    ).order_by('-date_creation')[:5]
    
    context = {
        'stats': stats,
        'commandes_recentes': commandes_recentes,
        'notifications': notifications
    }
    return render(request, 'client/client_dashboard.html', context)

@client_required
def client_commandes(request):
    user_id = request.session['user_id']
    
    # Filtres
    statut_filter = request.GET.get('statut', '')
    date_filter = request.GET.get('date', '')
    
    commandes = Commande.objects.filter(client_id=user_id).select_related('transporteur')
    
    if statut_filter:
        commandes = commandes.filter(statut=statut_filter)
    if date_filter:
        commandes = commandes.filter(date_creation__date=date_filter)
    
    commandes = commandes.order_by('-date_creation')
    
    # Pagination
    paginator = Paginator(commandes, 10)
    page_number = request.GET.get('page')
    commandes_page = paginator.get_page(page_number)
    
    context = {
        'commandes': commandes_page,
        'statuts': Commande.STATUS_CHOICES,
        'statut_filter': statut_filter,
        'date_filter': date_filter
    }
    return render(request, 'client/client_commandes.html', context)

@client_required
def client_nouvelle_commande(request):
    if request.method == 'POST':
        try:
            user_id = request.session['user_id']
            
            # Calcul automatique de la distance et durée
            origine = request.POST['origine']
            destination = request.POST['destination']
            
            transport_info = TransportAPIService.calculate_distance_duration(origine, destination)
            
            commande = Commande.objects.create(
                client_id=user_id,
                origine=origine,
                destination=destination,
                description_marchandise=request.POST['description_marchandise'],
                poids=float(request.POST['poids']),
                date_livraison_prevue=request.POST['date_livraison_prevue'],
                priorite=request.POST.get('priorite', 'normale'),
                notes=request.POST.get('notes', ''),
                distance_estimee=transport_info.get('distance_km') if transport_info else None,
                duree_estimee=timedelta(hours=transport_info.get('duration_hours')) if transport_info else None,
                statut='en_attente'
            )
            
            # Notification aux planificateurs
            planificateurs = User.objects.filter(role='planificateur', is_active=True)
            for planificateur in planificateurs:
                Notification.objects.create(
                    utilisateur=planificateur,
                    type_notification='nouvelle_commande',
                    titre='Nouvelle commande à planifier',
                    message=f'Nouvelle commande #{commande.id} de {commande.client.get_full_name()}',
                    commande=commande,
                    priority='normal' if commande.priorite == 'normale' else 'high'
                )
            
            # Enregistrer l'action
            HistoriqueAction.objects.create(
                utilisateur_id=user_id,
                action='create',
                description=f'Création commande #{commande.id}',
                table_name='commandes',
                record_id=commande.id
            )
            
            messages.success(request, f'Commande #{commande.id} créée avec succès!')
            return redirect('client_commandes')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la création de la commande: {str(e)}')
    
    context = {
        'priorites': Commande.PRIORITY_CHOICES
    }
    return render(request, 'client/client_nouvelle_commande.html', context)

@client_required
def client_commande_detail(request, commande_id):
    user_id = request.session['user_id']
    commande = get_object_or_404(Commande, id=commande_id, client_id=user_id)
    
    # Récupérer la livraison associée si elle existe
    try:
        livraison = commande.livraison
    except:
        livraison = None
    
    # Récupérer les étapes de tournée si la commande est planifiée
    etapes_tournee = []
    if commande.statut == 'planifiee' and hasattr(commande, 'etapes_tournee'):
        etapes_tournee = commande.etapes_tournee.all().order_by('ordre')
    
    context = {
        'commande': commande,
        'livraison': livraison,
        'etapes_tournee': etapes_tournee
    }
    return render(request, 'client/client_commande_detail.html', context)

@client_required
def client_suivi_commande(request, commande_id):
    user_id = request.session['user_id']
    commande = get_object_or_404(Commande, id=commande_id, client_id=user_id)
    
    # Données de suivi en temps réel
    suivi_data = {
        'commande': commande,
        'position_actuelle': None,
        'progression': 0,
        'temps_estime_restant': None
    }
    
    # Si la commande a une livraison en cours
    try:
        livraison = commande.livraison
        if livraison.statut == 'en_cours':
            suivi_data['position_actuelle'] = livraison.position_actuelle
            suivi_data['latitude'] = livraison.latitude_actuelle
            suivi_data['longitude'] = livraison.longitude_actuelle
            # Calcul de la progression (simulé)
            suivi_data['progression'] = 65  # Pourcentage
            suivi_data['temps_estime_restant'] = "45 minutes"
    except:
        pass
    
    context = suivi_data
    return render(request, 'client/client_suivi_commande.html', context)

@client_required
@require_http_methods(["POST"])
def client_annuler_commande(request, commande_id):
    try:
        user_id = request.session['user_id']
        commande = get_object_or_404(Commande, id=commande_id, client_id=user_id)
        
        if not commande.is_cancellable():
            return JsonResponse({
                'success': False,
                'message': 'Cette commande ne peut plus être annulée.'
            })
        
        commande.statut = 'annulee'
        commande.save()
        
        # Notification au transporteur si assigné
        if commande.transporteur:
            Notification.objects.create(
                utilisateur=commande.transporteur,
                type_notification='commande_annulee',
                titre='Commande annulée',
                message=f'La commande #{commande.id} a été annulée par le client.',
                commande=commande
            )
        
        # Enregistrer l'action
        HistoriqueAction.objects.create(
            utilisateur_id=user_id,
            action='status_change',
            description=f'Annulation commande #{commande.id}',
            table_name='commandes',
            record_id=commande.id
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Commande annulée avec succès.'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@client_required
def client_profil(request):
    user_id = request.session['user_id']
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        try:
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.email = request.POST['email']
            user.phone = request.POST.get('phone', '')
            user.save()
            
            messages.success(request, 'Profil mis à jour avec succès!')
            return redirect('client_profil')
        except Exception as e:
            messages.error(request, f'Erreur lors de la mise à jour: {str(e)}')
    
    context = {
        'user': user
    }
    return render(request, 'client/client_profil.html', context)

@client_required
def client_factures(request):
    user_id = request.session['user_id']
    commandes_facturees = Commande.objects.filter(
        client_id=user_id,
        statut='livree',
        prix__isnull=False
    ).order_by('-date_creation')
    
    # Pagination
    paginator = Paginator(commandes_facturees, 15)
    page_number = request.GET.get('page')
    factures_page = paginator.get_page(page_number)
    
    # Total des factures
    total_factures = commandes_facturees.aggregate(total=Sum('prix'))['total'] or 0
    
    context = {
        'factures': factures_page,
        'total_factures': total_factures
    }
    return render(request, 'client/client_factures.html', context)

# Ajouter ces vues à la fin de utilisateurs/views.py

# ==================== API VIEWS SUPPLÉMENTAIRES ====================

@require_http_methods(["GET"])
def get_notifications_count(request):
    """API pour récupérer le nombre de notifications non lues"""
    if 'user_id' not in request.session:
        return JsonResponse({'success': False, 'message': 'Non authentifié'})
    
    try:
        user_id = request.session['user_id']
        count = Notification.objects.filter(
            utilisateur_id=user_id,
            lu=False
        ).count()
        
        return JsonResponse({
            'success': True,
            'count': count
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@require_http_methods(["GET"])
def calculer_distance_api(request):
    """API pour calculer la distance entre deux points"""
    try:
        origine = request.GET.get('origine')
        destination = request.GET.get('destination')
        
        if not origine or not destination:
            return JsonResponse({
                'success': False,
                'message': 'Origine et destination requises'
            })
        
        # Utiliser le service API
        result = TransportAPIService.calculate_distance_duration(origine, destination)
        
        if result:
            return JsonResponse({
                'success': True,
                'distance_km': result['distance_km'],
                'duration_hours': result['duration_hours'],
                'duration_minutes': result['duration_minutes'],
                'source': result.get('source', 'api')
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Impossible de calculer la distance'
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@planificateur_required
@require_http_methods(["POST"])
def planification_automatique_api(request):
    """API pour lancer la planification automatique"""
    try:
        data = json.loads(request.body)
        date_cible = data.get('date_cible')
        planificateur_id = request.session['user_id']
        
        if date_cible:
            date_cible = datetime.strptime(date_cible, '%Y-%m-%d')
            date_cible = timezone.make_aware(date_cible.replace(hour=8, minute=0))
        
        # Lancer la planification automatique
        result = PlanificationService.planification_automatique_journaliere(
            date_cible, planificateur_id
        )
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur planification: {str(e)}'
        })

@planificateur_required
@require_http_methods(["GET"])
def analyser_capacite_api(request):
    """API pour analyser la capacité de planification"""
    try:
        date_str = request.GET.get('date')
        if date_str:
            date_cible = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            date_cible = timezone.now().date()
        
        result = PlanificationService.analyser_capacite_planification(date_cible)
        
        # Sérialiser la date pour JSON
        result['date_analyse'] = result['date_analyse'].isoformat()
        
        return JsonResponse({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur analyse capacité: {str(e)}'
        })

@planificateur_required
@require_http_methods(["POST"])
def optimiser_tournee_api(request, tournee_id):
    """API pour optimiser une tournée existante"""
    try:
        result = OptimisationService.optimiser_tournee_existante(tournee_id)
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur optimisation: {str(e)}'
        })

@planificateur_required
@require_http_methods(["GET"])
def suggestions_regroupements_api(request):
    """API pour obtenir des suggestions de regroupements"""
    try:
        date_str = request.GET.get('date')
        if date_str:
            date_cible = datetime.strptime(date_str, '%Y-%m-%d')
        else:
            date_cible = timezone.now()
        
        suggestions = PlanificationService.suggerer_regroupements(date_cible)
        
        # Sérialiser les données pour JSON
        suggestions_json = []
        for suggestion in suggestions:
            suggestion_data = {
                'zone': suggestion['zone'],
                'nb_commandes': len(suggestion['commandes']),
                'commandes_ids': [cmd.id for cmd in suggestion['commandes']],
                'poids_total': suggestion['poids_total'],
                'vehicule_recommande': suggestion['vehicule_recommande'],
                'economies_estimees': suggestion['economies_estimees'],
                'score_optimisation': suggestion['score_optimisation'],
                'taux_remplissage': suggestion.get('taux_remplissage', 0),
                'urgence': suggestion.get('urgence', False)
            }
            suggestions_json.append(suggestion_data)
        
        return JsonResponse({
            'success': True,
            'suggestions': suggestions_json
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur suggestions: {str(e)}'
        })

@require_http_methods(["GET"])
def weather_info_api(request, city):
    """API pour obtenir les informations météo"""
    try:
        weather_info = TransportAPIService.get_weather_info(city)
        
        if weather_info:
            return JsonResponse({
                'success': True,
                'weather': weather_info
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Informations météo non disponibles'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur météo: {str(e)}'
        })

@require_http_methods(["POST"])
def optimize_route_api(request):
    """API pour optimiser un itinéraire"""
    try:
        data = json.loads(request.body)
        points = data.get('points', [])
        
        if len(points) < 2:
            return JsonResponse({
                'success': False,
                'message': 'Au moins 2 points requis'
            })
        
        result = TransportAPIService.get_route_optimization(points)
        
        if result:
            return JsonResponse({
                'success': True,
                'optimization': result
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Impossible d\'optimiser l\'itinéraire'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur optimisation: {str(e)}'
        })

@require_http_methods(["POST"])
def estimate_price_api(request):
    """API pour estimer le prix d'un transport"""
    try:
        data = json.loads(request.body)
        distance_km = data.get('distance_km')
        poids_kg = data.get('poids_kg')
        priorite = data.get('priorite', 'normale')
        
        if not distance_km or not poids_kg:
            return JsonResponse({
                'success': False,
                'message': 'Distance et poids requis'
            })
        
        prix = TransportAPIService.calculate_estimated_price(
            float(distance_km), float(poids_kg), priorite
        )
        
        return JsonResponse({
            'success': True,
            'prix_estime': float(prix),
            'devise': 'DH'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur estimation prix: {str(e)}'
        })

@transporteur_required
@require_http_methods(["POST"])
def update_position_livraison(request, livraison_id):
    """API pour mettre à jour la position d'une livraison"""
    try:
        data = json.loads(request.body)
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        position_description = data.get('position', '')
        
        user_id = request.session['user_id']
        
        # Vérifier que la livraison appartient au transporteur
        livraison = get_object_or_404(
            Livraison, 
            id=livraison_id,
            vehicule__transporteur_id=user_id
        )
        
        # Mettre à jour la position
        livraison.latitude_actuelle = latitude
        livraison.longitude_actuelle = longitude
        livraison.position_actuelle = position_description
        livraison.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Position mise à jour'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur mise à jour position: {str(e)}'
        })

@require_http_methods(["GET"])
def get_tournee_progress(request, tournee_id):
    """API pour obtenir le progrès d'une tournée"""
    try:
        tournee = get_object_or_404(Tournee, id=tournee_id)
        
        # Vérifier les autorisations
        user_id = request.session.get('user_id')
        role = request.session.get('role')
        
        if role not in ['admin', 'planificateur', 'transporteur']:
            return JsonResponse({'success': False, 'message': 'Accès non autorisé'})
        
        if role == 'transporteur' and tournee.transporteur_id != user_id:
            return JsonResponse({'success': False, 'message': 'Accès non autorisé'})
        
        # Calculer le progrès
        etapes = tournee.etapes.all().order_by('ordre')
        etapes_terminees = etapes.filter(statut='terminee').count()
        total_etapes = etapes.count()
        
        progres_pourcentage = (etapes_terminees / total_etapes * 100) if total_etapes > 0 else 0
        
        # Prochaine étape
        prochaine_etape = etapes.filter(
            statut__in=['en_attente', 'en_cours']
        ).first()
        
        # Temps estimé restant
        temps_restant = None
        if prochaine_etape and tournee.date_fin_prevue:
            temps_restant = (tournee.date_fin_prevue - timezone.now()).total_seconds() / 3600
            temps_restant = max(0, temps_restant)  # Pas de temps négatif
        
        return JsonResponse({
            'success': True,
            'progres': {
                'pourcentage': round(progres_pourcentage, 1),
                'etapes_terminees': etapes_terminees,
                'total_etapes': total_etapes,
                'statut': tournee.statut,
                'prochaine_etape': {
                    'adresse': prochaine_etape.adresse if prochaine_etape else None,
                    'type': prochaine_etape.type_etape if prochaine_etape else None,
                    'heure_prevue': prochaine_etape.heure_prevue.isoformat() if prochaine_etape else None
                } if prochaine_etape else None,
                'temps_restant_heures': round(temps_restant, 1) if temps_restant else None
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur progrès tournée: {str(e)}'
        })

@require_http_methods(["GET"])
def performance_report_api(request):
    """API pour générer un rapport de performance"""
    try:
        date_debut_str = request.GET.get('date_debut')
        date_fin_str = request.GET.get('date_fin')
        
        if not date_debut_str or not date_fin_str:
            # Par défaut: 30 derniers jours
            date_fin = timezone.now()
            date_debut = date_fin - timedelta(days=30)
        else:
            date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d')
            date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d')
            date_debut = timezone.make_aware(date_debut)
            date_fin = timezone.make_aware(date_fin)
        
        # Statistiques générales
        tournees = Tournee.objects.filter(
            date_creation__range=[date_debut, date_fin]
        )
        
        livraisons = Livraison.objects.filter(
            commande__date_creation__range=[date_debut, date_fin]
        )
        
        stats = {
            'periode': {
                'debut': date_debut.isoformat(),
                'fin': date_fin.isoformat()
            },
            'tournees': {
                'total': tournees.count(),
                'terminees': tournees.filter(statut='terminee').count(),
                'en_cours': tournees.filter(statut='en_cours').count(),
                'distance_totale': sum([float(t.distance_totale or 0) for t in tournees])
            },
            'livraisons': {
                'total': livraisons.count(),
                'reussies': livraisons.filter(statut='livree').count(),
                'en_cours': livraisons.filter(statut='en_cours').count(),
                'incidents': livraisons.filter(statut='incident').count()
            }
        }
        
        # Calcul du taux de réussite
        if stats['livraisons']['total'] > 0:
            stats['taux_reussite'] = round(
                (stats['livraisons']['reussies'] / stats['livraisons']['total']) * 100, 2
            )
        else:
            stats['taux_reussite'] = 0
        
        return JsonResponse({
            'success': True,
            'rapport': stats
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur rapport performance: {str(e)}'
        })

@planificateur_required
@require_http_methods(["GET"])
def planification_report_api(request):
    """API pour générer un rapport de planification"""
    try:
        date_debut_str = request.GET.get('date_debut')
        date_fin_str = request.GET.get('date_fin')
        planificateur_id = request.session['user_id']
        
        if not date_debut_str or not date_fin_str:
            # Par défaut: 30 derniers jours
            date_fin = timezone.now()
            date_debut = date_fin - timedelta(days=30)
        else:
            date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d')
            date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d')
            date_debut = timezone.make_aware(date_debut)
            date_fin = timezone.make_aware(date_fin)
        
        # Générer le rapport
        rapport = PlanificationService.generer_rapport_planification(
            date_debut, date_fin, planificateur_id
        )
        
        # Sérialiser les dates pour JSON
        rapport['periode']['debut'] = rapport['periode']['debut'].isoformat()
        rapport['periode']['fin'] = rapport['periode']['fin'].isoformat()
        
        return JsonResponse({
            'success': True,
            'rapport': rapport
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur rapport planification: {str(e)}'
        })

@transporteur_required
@require_http_methods(["GET"])
def transporteur_analytics_api(request, transporteur_id):
    """API pour les analytics d'un transporteur"""
    try:
        # Vérifier que le transporteur demande ses propres analytics ou est admin
        user_id = request.session['user_id']
        role = request.session['role']
        
        if role != 'admin' and user_id != transporteur_id:
            return JsonResponse({
                'success': False,
                'message': 'Accès non autorisé'
            })
        
        # Récupérer le transporteur
        transporteur = get_object_or_404(User, id=transporteur_id, role='transporteur')
        
        # Période d'analyse (30 derniers jours par défaut)
        periode_jours = int(request.GET.get('periode', 30))
        
        # Analytics pour chaque véhicule
        vehicules = Vehicule.objects.filter(transporteur=transporteur)
        analytics_vehicules = []
        
        for vehicule in vehicules:
            performance = OptimisationService.analyser_performance_vehicule(
                vehicule, periode_jours
            )
            performance['vehicule_info'] = {
                'id': vehicule.id,
                'immatriculation': vehicule.immatriculation,
                'type_vehicule': vehicule.get_type_vehicule_display(),
                'capacite_max': float(vehicule.capacite_max)
            }
            analytics_vehicules.append(performance)
        
        # Analytics globales du transporteur
        tournees_periode = Tournee.objects.filter(
            transporteur=transporteur,
            date_creation__gte=timezone.now() - timedelta(days=periode_jours)
        )
        
        analytics_globales = {
            'nb_tournees': tournees_periode.count(),
            'nb_vehicules': vehicules.count(),
            'distance_totale': sum([float(t.distance_totale or 0) for t in tournees_periode]),
            'nb_livraisons': Livraison.objects.filter(
                vehicule__transporteur=transporteur,
                date_debut__gte=timezone.now() - timedelta(days=periode_jours)
            ).count(),
            'taux_reussite': 95.5,  # À calculer selon vos métriques
            'note_moyenne': 4.3     # À calculer selon vos métriques
        }
        
        return JsonResponse({
            'success': True,
            'analytics': {
                'transporteur': {
                    'id': transporteur.id,
                    'nom': transporteur.get_full_name(),
                    'email': transporteur.email
                },
                'periode_jours': periode_jours,
                'globales': analytics_globales,
                'vehicules': analytics_vehicules
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur analytics transporteur: {str(e)}'
        })

# ==================== VUES TRANSPORTEUR SUPPLÉMENTAIRES ====================

@transporteur_required
def transporteur_tournees(request):
    """Liste des tournées du transporteur"""
    user_id = request.session['user_id']
    
    # Filtres
    statut_filter = request.GET.get('statut', '')
    date_filter = request.GET.get('date', '')
    
    tournees = Tournee.objects.filter(transporteur_id=user_id)
    
    if statut_filter:
        tournees = tournees.filter(statut=statut_filter)
    if date_filter:
        tournees = tournees.filter(date_debut_prevue__date=date_filter)
    
    tournees = tournees.select_related('vehicule', 'planificateur').order_by('-date_creation')
    
    # Pagination
    paginator = Paginator(tournees, 10)
    page_number = request.GET.get('page')
    tournees_page = paginator.get_page(page_number)
    
    context = {
        'tournees': tournees_page,
        'statuts': Tournee.STATUS_CHOICES,
        'statut_filter': statut_filter,
        'date_filter': date_filter
    }
    return render(request, 'transporteur/transporteur_tournees.html', context)

@transporteur_required
def transporteur_tournee_detail(request, tournee_id):
    """Détail d'une tournée"""
    user_id = request.session['user_id']
    tournee = get_object_or_404(Tournee, id=tournee_id, transporteur_id=user_id)
    
    # Récupérer les étapes
    etapes = tournee.etapes.all().order_by('ordre')
    
    # Calculer les métriques
    efficacite = OptimisationService.calculer_efficacite_tournee(tournee)
    
    context = {
        'tournee': tournee,
        'etapes': etapes,
        'efficacite': efficacite
    }
    return render(request, 'transporteur/transporteur_tournee_detail.html', context)

@transporteur_required
def transporteur_edit_vehicule(request, vehicule_id):
    """Modifier un véhicule"""
    user_id = request.session['user_id']
    vehicule = get_object_or_404(Vehicule, id=vehicule_id, transporteur_id=user_id)
    
    if request.method == 'POST':
        try:
            vehicule.immatriculation = request.POST['immatriculation']
            vehicule.type_vehicule = request.POST['type_vehicule']
            vehicule.capacite_max = float(request.POST['capacite_max'])
            vehicule.marque = request.POST.get('marque', '')
            vehicule.modele = request.POST.get('modele', '')
            vehicule.annee = int(request.POST['annee']) if request.POST.get('annee') else None
            vehicule.couleur = request.POST.get('couleur', '')
            vehicule.notes = request.POST.get('notes', '')
            vehicule.disponible = request.POST.get('disponible') == 'on'
            
            vehicule.save()
            
            messages.success(request, 'Véhicule mis à jour avec succès.')
            return redirect('transporteur_vehicules')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la mise à jour: {str(e)}')
    
    context = {
        'vehicule': vehicule,
        'types_vehicules': Vehicule.TYPE_CHOICES
    }
    return render(request, 'transporteur/transporteur_edit_vehicule.html', context)

# ==================== VUES PLANIFICATEUR SUPPLÉMENTAIRES ====================

@planificateur_required
def planificateur_tournee_detail(request, tournee_id):
    """Détail d'une tournée pour le planificateur"""
    user_id = request.session['user_id']
    tournee = get_object_or_404(Tournee, id=tournee_id)
    
    # Vérifier que le planificateur peut voir cette tournée
    if tournee.planificateur_id != user_id:
        messages.error(request, 'Accès non autorisé à cette tournée.')
        return redirect('planificateur_tournees')
    
    # Récupérer les étapes avec les commandes
    etapes = tournee.etapes.all().select_related('commande').order_by('ordre')
    
    # Calculer les métriques d'efficacité
    efficacite = OptimisationService.calculer_efficacite_tournee(tournee)
    
    # Suggestions d'amélioration
    suggestions = OptimisationService.suggerer_ameliorations_tournee(tournee)
    
    context = {
        'tournee': tournee,
        'etapes': etapes,
        'efficacite': efficacite,
        'suggestions': suggestions
    }
    return render(request, 'planificateur/planificateur_tournee_detail.html', context)

@planificateur_required
def planificateur_optimiser_tournee(request, tournee_id):
    """Optimiser une tournée existante"""
    if request.method == 'POST':
        try:
            result = OptimisationService.optimiser_tournee_existante(tournee_id)
            
            if result.get('success'):
                messages.success(request, result['message'])
                return JsonResponse(result)
            else:
                messages.error(request, result['message'])
                return JsonResponse(result)
                
        except Exception as e:
            error_msg = f'Erreur lors de l\'optimisation: {str(e)}'
            messages.error(request, error_msg)
            return JsonResponse({'success': False, 'message': error_msg})
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})

@planificateur_required
def planificateur_replanifier_tournee(request, tournee_id):
    """Replanifier une tournée avec de nouvelles commandes"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            nouvelles_commandes = data.get('nouvelles_commandes', [])
            
            result = PlanificationService.replanifier_tournee(
                tournee_id, nouvelles_commandes
            )
            
            if result.get('success'):
                messages.success(request, result['message'])
            else:
                messages.error(request, result['message'])
            
            return JsonResponse(result)
            
        except Exception as e:
            error_msg = f'Erreur lors de la replanification: {str(e)}'
            messages.error(request, error_msg)
            return JsonResponse({'success': False, 'message': error_msg})
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})

@planificateur_required
def planificateur_planification_auto(request):
    """Interface pour la planification automatique"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            date_cible_str = data.get('date_cible')
            planificateur_id = request.session['user_id']
            
            if date_cible_str:
                date_cible = datetime.strptime(date_cible_str, '%Y-%m-%d')
                date_cible = timezone.make_aware(date_cible.replace(hour=8, minute=0))
            else:
                date_cible = None
            
            # Lancer la planification automatique
            result = PlanificationService.planification_automatique_journaliere(
                date_cible, planificateur_id
            )
            
            if result.get('success'):
                messages.success(request, result['message'])
            else:
                messages.error(request, result['message'])
            
            return JsonResponse(result)
            
        except Exception as e:
            error_msg = f'Erreur planification automatique: {str(e)}'
            messages.error(request, error_msg)
            return JsonResponse({'success': False, 'message': error_msg})
    
    # Affichage de la page
    # Analyse de capacité pour aujourd'hui
    capacite_analyse = PlanificationService.analyser_capacite_planification()
    
    # Commandes en attente
    commandes_attente = Commande.objects.filter(
        statut='en_attente'
    ).select_related('client').order_by('date_livraison_prevue')
    
    # Véhicules disponibles
    vehicules_disponibles = Vehicule.objects.filter(
        disponible=True,
        transporteur__is_active=True
    ).select_related('transporteur')
    
    context = {
        'capacite_analyse': capacite_analyse,
        'commandes_attente': commandes_attente,
        'vehicules_disponibles': vehicules_disponibles
    }
    return render(request, 'planificateur/planificateur_planification_auto.html', context)

@planificateur_required
def planificateur_suggestions(request):
    """Page des suggestions de regroupements"""
    date_filter = request.GET.get('date')
    if date_filter:
        date_cible = datetime.strptime(date_filter, '%Y-%m-%d')
    else:
        date_cible = timezone.now()
    
    # Obtenir les suggestions
    suggestions = PlanificationService.suggerer_regroupements(date_cible)
    
    context = {
        'suggestions': suggestions,
        'date_filter': date_filter or date_cible.strftime('%Y-%m-%d')
    }
    return render(request, 'planificateur/planificateur_suggestions.html', context)

@planificateur_required
def planificateur_analytics(request):
    """Page d'analytics pour le planificateur"""
    user_id = request.session['user_id']
    
    # Période d'analyse
    periode = request.GET.get('periode', '30')  # jours
    try:
        periode_jours = int(periode)
    except:
        periode_jours = 30
    
    date_fin = timezone.now()
    date_debut = date_fin - timedelta(days=periode_jours)
    
    # Générer le rapport de planification
    rapport = PlanificationService.generer_rapport_planification(
        date_debut, date_fin, user_id
    )
    
    # Statistiques des véhicules
    vehicules_stats = []
    vehicules = Vehicule.objects.filter(transporteur__is_active=True)
    
    for vehicule in vehicules[:10]:  # Limiter à 10 véhicules
        performance = OptimisationService.analyser_performance_vehicule(
            vehicule, periode_jours
        )
        if performance.get('nb_tournees', 0) > 0:
            vehicules_stats.append({
                'vehicule': vehicule,
                'performance': performance
            })
    
    # Trier par score de performance
    vehicules_stats.sort(
        key=lambda x: x['performance'].get('score_performance_moyen', 0), 
        reverse=True
    )
    
    context = {
        'rapport': rapport,
        'vehicules_stats': vehicules_stats[:5],  # Top 5
        'periode_jours': periode_jours,
        'date_debut': date_debut,
        'date_fin': date_fin
    }
    return render(request, 'planificateur/planificateur_analytics.html', context)

# ==================== VUES API POUR ASSIGNATION ET MISE À JOUR ====================

@require_http_methods(["POST"])
def assign_commande(request, commande_id):
    """Assigner une commande à un transporteur"""
    try:
        data = json.loads(request.body)
        transporteur_id = data.get('transporteur_id')
        vehicule_id = data.get('vehicule_id')
        
        # Vérifications
        commande = get_object_or_404(Commande, id=commande_id)
        
        if commande.statut != 'en_attente':
            return JsonResponse({
                'success': False,
                'message': 'Cette commande ne peut plus être assignée'
            })
        
        transporteur = get_object_or_404(User, id=transporteur_id, role='transporteur')
        
        if vehicule_id:
            vehicule = get_object_or_404(Vehicule, id=vehicule_id, transporteur=transporteur)
            if not vehicule.disponible:
                return JsonResponse({
                    'success': False,
                    'message': 'Ce véhicule n\'est pas disponible'
                })
        
        # Assignation
        with transaction.atomic():
            commande.transporteur = transporteur
            commande.statut = 'affectee'
            commande.save()
            
            # Créer la livraison si un véhicule est assigné
            if vehicule_id:
                Livraison.objects.get_or_create(
                    commande=commande,
                    defaults={
                        'vehicule_id': vehicule_id,
                        'statut': 'en_attente'
                    }
                )
                
                # Marquer le véhicule comme non disponible
                vehicule.disponible = False
                vehicule.save()
            
            # Notification au transporteur
            Notification.objects.create(
                utilisateur=transporteur,
                type_notification='commande_affectee',
                titre='Nouvelle commande assignée',
                message=f'La commande #{commande.id} vous a été assignée.',
                commande=commande,
                priority='high'
            )
            
            # Notification au client
            Notification.objects.create(
                utilisateur=commande.client,
                type_notification='commande_affectee',
                titre='Commande assignée',
                message=f'Votre commande #{commande.id} a été assignée à un transporteur.',
                commande=commande
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Commande assignée avec succès'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur lors de l\'assignation: {str(e)}'
        })

@require_http_methods(["POST"])
def update_livraison_status(request, livraison_id):
    """Mettre à jour le statut d'une livraison"""
    try:
        data = json.loads(request.body)
        nouveau_statut = data.get('statut')
        notes = data.get('notes', '')
        position = data.get('position', '')
        
        # Vérifications
        livraison = get_object_or_404(Livraison, id=livraison_id)
        
        if nouveau_statut not in [choice[0] for choice in Livraison.STATUS_CHOICES]:
            return JsonResponse({
                'success': False,
                'message': 'Statut invalide'
            })
        
        # Vérifier les autorisations
        user_id = request.session.get('user_id')
        role = request.session.get('role')
        
        if role == 'transporteur' and livraison.vehicule.transporteur_id != user_id:
            return JsonResponse({
                'success': False,
                'message': 'Accès non autorisé'
            })
        
        # Mise à jour
        with transaction.atomic():
            ancien_statut = livraison.statut
            livraison.statut = nouveau_statut
            livraison.notes_livraison = notes
            livraison.position_actuelle = position
            
            # Mettre à jour les dates selon le statut
            if nouveau_statut == 'en_cours' and ancien_statut != 'en_cours':
                livraison.date_debut = timezone.now()
            elif nouveau_statut == 'livree' and ancien_statut != 'livree':
                livraison.date_fin = timezone.now()
                # Mettre à jour la commande
                livraison.commande.statut = 'livree'
                livraison.commande.save()
                # Libérer le véhicule
                livraison.vehicule.disponible = True
                livraison.vehicule.save()
            
            livraison.save()
            
            # Notifications
            if nouveau_statut == 'livree':
                Notification.objects.create(
                    utilisateur=livraison.commande.client,
                    type_notification='statut_livraison',
                    titre='Livraison terminée',
                    message=f'Votre commande #{livraison.commande.id} a été livrée avec succès.',
                    commande=livraison.commande,
                    livraison=livraison,
                    priority='high'
                )
            elif nouveau_statut == 'incident':
                Notification.objects.create(
                    utilisateur=livraison.commande.client,
                    type_notification='incident',
                    titre='Incident de livraison',
                    message=f'Un incident est survenu lors de la livraison de votre commande #{livraison.commande.id}.',
                    commande=livraison.commande,
                    livraison=livraison,
                    priority='urgent'
                )
        
        return JsonResponse({
            'success': True,
            'message': 'Statut mis à jour avec succès'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur lors de la mise à jour: {str(e)}'
        })

@require_http_methods(["POST"])
def mark_notifications_read(request):
    """Marquer les notifications comme lues"""
    try:
        data = json.loads(request.body)
        notification_ids = data.get('notification_ids', [])
        
        user_id = request.session.get('user_id')
        if not user_id:
            return JsonResponse({
                'success': False,
                'message': 'Non authentifié'
            })
        
        if notification_ids:
            # Marquer les notifications spécifiées
            Notification.objects.filter(
                id__in=notification_ids,
                utilisateur_id=user_id,
                lu=False
            ).update(lu=True, date_lecture=timezone.now())
            
            count = len(notification_ids)
        else:
            # Marquer toutes les notifications non lues
            notifications = Notification.objects.filter(
                utilisateur_id=user_id,
                lu=False
            )
            count = notifications.count()
            notifications.update(lu=True, date_lecture=timezone.now())
        
        return JsonResponse({
            'success': True,
            'message': f'{count} notification(s) marquée(s) comme lue(s)'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur: {str(e)}'
        })

@require_http_methods(["GET"])
def commande_details_api(request, commande_id):
    """API pour obtenir les détails d'une commande"""
    try:
        commande = get_object_or_404(Commande, id=commande_id)
        
        # Vérifier les autorisations
        user_id = request.session.get('user_id')
        role = request.session.get('role')
        
        if role not in ['admin', 'planificateur']:
            if role == 'client' and commande.client_id != user_id:
                return JsonResponse({'success': False, 'message': 'Accès non autorisé'})
            elif role == 'transporteur' and commande.transporteur_id != user_id:
                return JsonResponse({'success': False, 'message': 'Accès non autorisé'})
        
        # Préparer les données
        data = {
            'id': commande.id,
            'client': commande.client.get_full_name(),
            'transporteur': commande.transporteur.get_full_name() if commande.transporteur else None,
            'origine': commande.origine,
            'destination': commande.destination,
            'description_marchandise': commande.description_marchandise,
            'poids': float(commande.poids),
            'date_creation': commande.date_creation.isoformat(),
            'date_livraison_prevue': commande.date_livraison_prevue.isoformat(),
            'date_livraison_planifiee': commande.date_livraison_planifiee.isoformat() if commande.date_livraison_planifiee else None,
            'statut': commande.statut,
            'statut_display': commande.get_statut_display(),
            'priorite': commande.priorite,
            'priorite_display': commande.get_priorite_display(),
            'prix': float(commande.prix) if commande.prix else None,
            'notes': commande.notes,
            'distance_estimee': float(commande.distance_estimee) if commande.distance_estimee else None,
            'duree_estimee': str(commande.duree_estimee) if commande.duree_estimee else None
        }
        
        # Ajouter les informations de livraison si elles existent
        try:
            livraison = commande.livraison
            data['livraison'] = {
                'id': livraison.id,
                'statut': livraison.statut,
                'statut_display': livraison.get_statut_display(),
                'position_actuelle': livraison.position_actuelle,
                'latitude_actuelle': float(livraison.latitude_actuelle) if livraison.latitude_actuelle else None,
                'longitude_actuelle': float(livraison.longitude_actuelle) if livraison.longitude_actuelle else None,
                'date_debut': livraison.date_debut.isoformat() if livraison.date_debut else None,
                'date_fin': livraison.date_fin.isoformat() if livraison.date_fin else None,
                'vehicule': {
                    'immatriculation': livraison.vehicule.immatriculation,
                    'type_vehicule': livraison.vehicule.get_type_vehicule_display(),
                    'capacite_max': float(livraison.vehicule.capacite_max)
                } if livraison.vehicule else None
            }
        except:
            data['livraison'] = None
        
        return JsonResponse({
            'success': True,
            'commande': data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur: {str(e)}'
        })

@require_http_methods(["GET"])
def check_new_commandes(request):
    """Vérifier s'il y a de nouvelles commandes"""
    try:
        role = request.session.get('role')
        
        if role in ['admin', 'planificateur']:
            # Pour les admins et planificateurs, vérifier les nouvelles commandes
            derniere_verification = request.session.get('derniere_verification_commandes')
            
            if derniere_verification:
                derniere_verification = datetime.fromisoformat(derniere_verification)
                nouvelles_commandes = Commande.objects.filter(
                    date_creation__gt=derniere_verification,
                    statut='en_attente'
                ).count()
            else:
                nouvelles_commandes = Commande.objects.filter(statut='en_attente').count()
            
            request.session['derniere_verification_commandes'] = timezone.now().isoformat()
            
            return JsonResponse({
                'hasNew': nouvelles_commandes > 0,
                'count': nouvelles_commandes
            })
        
        return JsonResponse({'hasNew': False, 'count': 0})
        
    except Exception as e:
        return JsonResponse({'hasNew': False, 'count': 0, 'error': str(e)})

@require_http_methods(["GET"])
def check_livraisons_updates(request):
    """Vérifier s'il y a des mises à jour de livraisons"""
    try:
        user_id = request.session.get('user_id')
        role = request.session.get('role')
        
        if not user_id:
            return JsonResponse({'hasUpdates': False})
        
        derniere_verification = request.session.get('derniere_verification_livraisons')
        
        if role == 'transporteur':
            # Pour les transporteurs, vérifier les livraisons de leurs véhicules
            if derniere_verification:
                derniere_verification = datetime.fromisoformat(derniere_verification)
                livraisons_mises_a_jour = Livraison.objects.filter(
                    vehicule__transporteur_id=user_id,
                    commande__updated_at__gt=derniere_verification
                ).count()
            else:
                livraisons_mises_a_jour = 0
        elif role == 'client':
            # Pour les clients, vérifier leurs commandes
            if derniere_verification:
                derniere_verification = datetime.fromisoformat(derniere_verification)
                livraisons_mises_a_jour = Commande.objects.filter(
                    client_id=user_id,
                    updated_at__gt=derniere_verification
                ).count()
            else:
                livraisons_mises_a_jour = 0
        else:
            livraisons_mises_a_jour = 0
        
        request.session['derniere_verification_livraisons'] = timezone.now().isoformat()
        
        return JsonResponse({
            'hasUpdates': livraisons_mises_a_jour > 0,
            'count': livraisons_mises_a_jour
        })
        
    except Exception as e:
        return JsonResponse({'hasUpdates': False, 'count': 0, 'error': str(e)})