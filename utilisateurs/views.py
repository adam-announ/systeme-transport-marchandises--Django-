from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import User, Commande, Vehicule, Livraison, Notification


def accueil(request):
    return render(request, 'utilisateurs/index.html')

def gestion_commandes(request):
    return render(request, 'utilisateurs/gestion_commandes.html')

def optimisation_tournees(request):
    return render(request, 'utilisateurs/optimisation_tournees.html')

def suivi_temps_reel(request):
    return render(request, 'utilisateurs/suivi_temps_reel.html')

def contact(request):
    return render(request, 'utilisateurs/contact.html')

def login_view(request):
    if 'user_id' in request.session:
        return redirect('accueil')
    
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        
        try:
            user = User.objects.get(username=username, is_active=True)
            if check_password(password, user.password):
                request.session['user_id'] = user.id
                request.session['username'] = user.username
                request.session['role'] = user.role
                request.session['first_name'] = user.first_name
                request.session['last_name'] = user.last_name
                
                # Redirection selon le rôle
                if user.role == 'admin':
                    return redirect('admin_dashboard')
                elif user.role == 'transporteur':
                    return redirect('transporteur_dashboard')
                else:
                    return redirect('accueil')
            else:
                messages.error(request, 'Mot de passe incorrect.')
        except User.DoesNotExist:
            messages.error(request, 'Nom d\'utilisateur introuvable.')
    
    return render(request, 'utilisateurs/login.html')

def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        role = request.POST['role']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        phone = request.POST.get('phone', '')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Ce nom d\'utilisateur existe déjà.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Cet email est déjà utilisé.')
        else:
            user = User(
                username=username,
                email=email,
                password=password,  
                role=role,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                is_active=True
            )
            user.save()
            messages.success(request, 'Compte créé avec succès ! Vous pouvez maintenant vous connecter.')
            return redirect('login')
    
    return render(request, 'utilisateurs/register.html')

def logout_view(request):
    if 'user_id' in request.session:
        request.session.flush()
    return redirect('accueil')

# ==================== VUES ADMIN ====================

def admin_required(view_func):
    """Décorateur pour vérifier que l'utilisateur est admin"""
    def _wrapped_view(request, *args, **kwargs):
        if 'user_id' not in request.session or request.session.get('role') != 'admin':
            messages.error(request, 'Accès non autorisé.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@admin_required
def admin_dashboard(request):
    # Statistiques pour le dashboard
    stats = {
        'total_users': User.objects.count(),
        'commandes_mois': Commande.objects.filter(
            date_creation__gte=timezone.now().replace(day=1)
        ).count(),
        'livraisons_cours': Livraison.objects.filter(statut='en_cours').count(),
        'revenus_mois': Commande.objects.filter(
            date_creation__gte=timezone.now().replace(day=1),
            statut='livree'
        ).aggregate(total=Sum('prix'))['total'] or 0,
        'nouveaux_users': User.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()
    }
    
    # Commandes récentes
    recent_commandes = Commande.objects.select_related('client').order_by('-date_creation')[:10]
    
    context = {
        'stats': stats,
        'recent_commandes': recent_commandes
    }
    return render(request, 'utilisateurs/admin_dashboard.html', context)

@admin_required
def admin_users(request):
    # Filtres
    search = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    
    users = User.objects.all()
    
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    if role_filter:
        users = users.filter(role=role_filter)
    
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    users = users.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    users_page = paginator.get_page(page_number)
    
    context = {
        'users': users_page,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': users_page
    }
    return render(request, 'utilisateurs/admin_users.html', context)

@admin_required
def admin_create_user(request):
    if request.method == 'POST':
        # Logique de création d'utilisateur
        pass
    return render(request, 'utilisateurs/admin_create_user.html')

@admin_required
def admin_edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        # Logique de modification d'utilisateur
        pass
    return render(request, 'utilisateurs/admin_edit_user.html', {'user': user})

@admin_required
def admin_toggle_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        user.is_active = not user.is_active
        user.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

@admin_required
def admin_commandes(request):
    commandes = Commande.objects.select_related('client', 'transporteur').order_by('-date_creation')
    
    # Pagination
    paginator = Paginator(commandes, 20)
    page_number = request.GET.get('page')
    commandes_page = paginator.get_page(page_number)
    
    context = {
        'commandes': commandes_page,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': commandes_page
    }
    return render(request, 'utilisateurs/admin_commandes.html', context)

@admin_required
def admin_reports(request):
    return render(request, 'utilisateurs/admin_reports.html')

@admin_required
def admin_system_config(request):
    return render(request, 'utilisateurs/admin_system_config.html')

@admin_required
def admin_notifications(request):
    return render(request, 'utilisateurs/admin_notifications.html')

# ==================== VUES TRANSPORTEUR ====================

def transporteur_required(view_func):
    """Décorateur pour vérifier que l'utilisateur est transporteur"""
    def _wrapped_view(request, *args, **kwargs):
        if 'user_id' not in request.session or request.session.get('role') != 'transporteur':
            messages.error(request, 'Accès non autorisé.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@transporteur_required
def transporteur_dashboard(request):
    user_id = request.session['user_id']
    
    # Statistiques
    stats = {
        'livraisons_completees': Livraison.objects.filter(
            commande__transporteur_id=user_id,
            statut='livree'
        ).count(),
        'livraisons_en_cours': Livraison.objects.filter(
            commande__transporteur_id=user_id,
            statut='en_cours'
        ).count(),
        'revenus_mois': Commande.objects.filter(
            transporteur_id=user_id,
            date_creation__gte=timezone.now().replace(day=1),
            statut='livree'
        ).aggregate(total=Sum('prix'))['total'] or 0,
        'note_moyenne': 4.2  # À calculer selon votre système de notation
    }
    
    # Livraisons du jour
    aujourd_hui = timezone.now().date()
    livraisons_jour = Livraison.objects.filter(
        commande__transporteur_id=user_id,
        commande__date_livraison_prevue__date=aujourd_hui
    ).select_related('commande')
    
    # Notifications récentes
    notifications = Notification.objects.filter(
        utilisateur_id=user_id
    ).order_by('-date_creation')[:5]
    
    # Compteurs pour la sidebar
    commandes_disponibles = Commande.objects.filter(statut='en_attente').count()
    livraisons_actives = Livraison.objects.filter(
        commande__transporteur_id=user_id,
        statut__in=['en_attente', 'en_cours']
    ).count()
    
    context = {
        'stats': stats,
        'livraisons_jour': livraisons_jour,
        'notifications': notifications,
        'commandes_disponibles': commandes_disponibles,
        'livraisons_actives': livraisons_actives,
        'transporteur_disponible': True  # À implémenter selon votre logique
    }
    return render(request, 'utilisateurs/transporteur_dashboard.html', context)

@transporteur_required
def transporteur_commandes(request):
    user_id = request.session['user_id']
    
    # Filtres
    ville_depart = request.GET.get('ville_depart', '')
    ville_arrivee = request.GET.get('ville_arrivee', '')
    poids_max = request.GET.get('poids_max', '')
    
    # Commandes disponibles (non affectées)
    commandes = Commande.objects.filter(
        statut='en_attente',
        transporteur__isnull=True
    ).select_related('client')
    
    # Application des filtres
    if ville_depart:
        commandes = commandes.filter(origine__icontains=ville_depart)
    if ville_arrivee:
        commandes = commandes.filter(destination__icontains=ville_arrivee)
    if poids_max:
        commandes = commandes.filter(poids__lte=float(poids_max))
    
    commandes = commandes.order_by('-date_creation')
    
    # Pagination
    paginator = Paginator(commandes, 12)
    page_number = request.GET.get('page')
    commandes_page = paginator.get_page(page_number)
    
    # Véhicules du transporteur pour le modal d'acceptation
    mes_vehicules = Vehicule.objects.filter(transporteur_id=user_id, disponible=True)
    
    # Compteurs pour la sidebar
    commandes_disponibles = Commande.objects.filter(statut='en_attente').count()
    livraisons_actives = Livraison.objects.filter(
        commande__transporteur_id=user_id,
        statut__in=['en_attente', 'en_cours']
    ).count()
    
    context = {
        'commandes': commandes_page,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': commandes_page,
        'mes_vehicules': mes_vehicules,
        'commandes_disponibles': commandes_disponibles,
        'livraisons_actives': livraisons_actives
    }
    return render(request, 'utilisateurs/transporteur_commandes.html', context)

@transporteur_required
def transporteur_accept_commande(request, commande_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = request.session['user_id']
            
            commande = get_object_or_404(Commande, id=commande_id, statut='en_attente')
            vehicule = get_object_or_404(Vehicule, id=data['vehicule_id'], transporteur_id=user_id)
            
            # Vérifier la capacité
            if commande.poids > vehicule.capacite_max:
                return JsonResponse({
                    'success': False,
                    'message': 'Le poids de la commande dépasse la capacité du véhicule'
                })
            
            # Affecter la commande au transporteur
            commande.transporteur_id = user_id
            commande.statut = 'affectee'
            commande.save()
            
            # Créer la livraison
            livraison = Livraison.objects.create(
                commande=commande,
                vehicule=vehicule,
                statut='en_attente',
                notes_livraison=data.get('notes', '')
            )
            
            # Créer une notification pour le client
            Notification.objects.create(
                utilisateur=commande.client,
                type_notification='commande_affectee',
                titre='Commande acceptée',
                message=f'Votre commande #{commande.id} a été acceptée par un transporteur.'
            )
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False})

@transporteur_required
def transporteur_livraisons(request):
    user_id = request.session['user_id']
    
    # Livraisons du transporteur
    livraisons = Livraison.objects.filter(
        commande__transporteur_id=user_id
    ).select_related('commande', 'vehicule').order_by('-commande__date_creation')
    
    # Pagination
    paginator = Paginator(livraisons, 15)
    page_number = request.GET.get('page')
    livraisons_page = paginator.get_page(page_number)
    
    # Compteurs pour la sidebar
    commandes_disponibles = Commande.objects.filter(statut='en_attente').count()
    livraisons_actives = Livraison.objects.filter(
        commande__transporteur_id=user_id,
        statut__in=['en_attente', 'en_cours']
    ).count()
    
    context = {
        'livraisons': livraisons_page,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': livraisons_page,
        'commandes_disponibles': commandes_disponibles,
        'livraisons_actives': livraisons_actives
    }
    return render(request, 'utilisateurs/transporteur_livraisons.html', context)

@transporteur_required
def transporteur_update_livraison(request, livraison_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = request.session['user_id']
            
            livraison = get_object_or_404(
                Livraison, 
                id=livraison_id, 
                commande__transporteur_id=user_id
            )
            
            # Mettre à jour le statut
            livraison.statut = data.get('statut', livraison.statut)
            livraison.position_actuelle = data.get('position_actuelle', livraison.position_actuelle)
            livraison.notes_livraison = data.get('notes_livraison', livraison.notes_livraison)
            
            if data.get('statut') == 'en_cours' and not livraison.date_debut:
                livraison.date_debut = timezone.now()
            elif data.get('statut') == 'livree':
                livraison.date_fin = timezone.now()
                livraison.commande.statut = 'livree'
                livraison.commande.save()
            
            livraison.save()
            
            # Créer une notification pour le client
            statut_messages = {
                'en_cours': 'Votre commande est en cours de livraison',
                'livree': 'Votre commande a été livrée avec succès',
                'incident': 'Un incident est survenu sur votre commande'
            }
            
            if data.get('statut') in statut_messages:
                Notification.objects.create(
                    utilisateur=livraison.commande.client,
                    type_notification='statut_livraison',
                    titre='Mise à jour de votre commande',
                    message=statut_messages[data.get('statut')]
                )
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False})

@transporteur_required
def transporteur_vehicules(request):
    user_id = request.session['user_id']
    
    # Véhicules du transporteur
    vehicules = Vehicule.objects.filter(transporteur_id=user_id).order_by('-id')
    
    # Compteurs pour la sidebar
    commandes_disponibles = Commande.objects.filter(statut='en_attente').count()
    livraisons_actives = Livraison.objects.filter(
        commande__transporteur_id=user_id,
        statut__in=['en_attente', 'en_cours']
    ).count()
    
    context = {
        'vehicules': vehicules,
        'commandes_disponibles': commandes_disponibles,
        'livraisons_actives': livraisons_actives
    }
    return render(request, 'utilisateurs/transporteur_vehicules.html', context)

@transporteur_required
def transporteur_add_vehicule(request):
    if request.method == 'POST':
        try:
            user_id = request.session['user_id']
            
            vehicule = Vehicule.objects.create(
                transporteur_id=user_id,
                immatriculation=request.POST['immatriculation'],
                type_vehicule=request.POST['type_vehicule'],
                capacite_max=float(request.POST['capacite_max']),
                disponible=True
            )
            
            messages.success(request, 'Véhicule ajouté avec succès.')
            return redirect('transporteur_vehicules')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de l\'ajout du véhicule: {str(e)}')
    
    return render(request, 'utilisateurs/transporteur_add_vehicule.html')

@transporteur_required
def transporteur_itineraire(request):
    user_id = request.session['user_id']
    
    # Livraisons en cours pour optimisation d'itinéraire
    livraisons_en_cours = Livraison.objects.filter(
        commande__transporteur_id=user_id,
        statut__in=['en_attente', 'en_cours']
    ).select_related('commande')
    
    # Compteurs pour la sidebar
    commandes_disponibles = Commande.objects.filter(statut='en_attente').count()
    livraisons_actives = len(livraisons_en_cours)
    
    context = {
        'livraisons_en_cours': livraisons_en_cours,
        'commandes_disponibles': commandes_disponibles,
        'livraisons_actives': livraisons_actives
    }
    return render(request, 'utilisateurs/transporteur_itineraire.html', context)

# ==================== API ENDPOINTS ====================

def assign_commande(request, commande_id):
    """Assigner une commande à un transporteur (Admin)"""
    if request.method == 'POST' and request.session.get('role') == 'admin':
        try:
            data = json.loads(request.body)
            commande = get_object_or_404(Commande, id=commande_id)
            transporteur = get_object_or_404(User, id=data['transporteur_id'], role='transporteur')
            
            commande.transporteur = transporteur
            commande.statut = 'affectee'
            commande.save()
            
            # Créer une notification
            Notification.objects.create(
                utilisateur=transporteur,
                type_notification='commande_affectee',
                titre='Nouvelle commande affectée',
                message=f'La commande #{commande.id} vous a été affectée.'
            )
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False})

def update_livraison_status(request, livraison_id):
    """Mettre à jour le statut d'une livraison"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = request.session['user_id']
            
            # Vérifier les permissions selon le rôle
            if request.session.get('role') == 'admin':
                livraison = get_object_or_404(Livraison, id=livraison_id)
            elif request.session.get('role') == 'transporteur':
                livraison = get_object_or_404(
                    Livraison, 
                    id=livraison_id, 
                    commande__transporteur_id=user_id
                )
            else:
                return JsonResponse({'success': False, 'message': 'Non autorisé'})
            
            livraison.statut = data.get('statut', livraison.statut)
            livraison.position_actuelle = data.get('position_actuelle', livraison.position_actuelle)
            livraison.notes_livraison = data.get('notes_livraison', livraison.notes_livraison)
            
            if data.get('statut') == 'en_cours' and not livraison.date_debut:
                livraison.date_debut = timezone.now()
            elif data.get('statut') == 'livree':
                livraison.date_fin = timezone.now()
                livraison.commande.statut = 'livree'
                livraison.commande.save()
            
            livraison.save()
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False})

def mark_notifications_read(request):
    """Marquer les notifications comme lues"""
    if request.method == 'POST' and 'user_id' in request.session:
        try:
            user_id = request.session['user_id']
            Notification.objects.filter(
                utilisateur_id=user_id,
                lu=False
            ).update(lu=True)
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False})