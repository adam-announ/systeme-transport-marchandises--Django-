from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.hashers import check_password
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from django.db import transaction
from .models import User, Commande, Vehicule, Livraison, Notification, Tournee, EtapeTournee
import json

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

def login_view(request):
    if 'user_id' in request.session:
        role = request.session.get('role')
        if role == 'admin':
            return redirect('admin_dashboard')
        elif role == 'planificateur':
            return redirect('planificateur_dashboard')
        elif role == 'transporteur':
            return redirect('transporteur_dashboard')
        elif role == 'client':
            return redirect('client_dashboard')
        else:
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
                
                if user.role == 'admin':
                    return redirect('admin_dashboard')
                elif user.role == 'planificateur':
                    return redirect('planificateur_dashboard')
                elif user.role == 'transporteur':
                    return redirect('transporteur_dashboard')
                elif user.role == 'client':
                    return redirect('client_dashboard')
                else:
                    return redirect('accueil')
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
    
    return render(request, 'auth/register.html')

def logout_view(request):
    if 'user_id' in request.session:
        request.session.flush()
    return redirect('accueil')

# Décorateurs
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

# Vues Admin
@admin_required
def admin_dashboard(request):
    stats = {
        'total_users': User.objects.count(),
        'commandes_mois': Commande.objects.filter(
            date_creation__gte=timezone.now().replace(day=1)
        ).count(),
        'livraisons_cours': Livraison.objects.filter(statut='en_cours').count(),
        'revenus_mois': 0
    }
    
    recent_commandes = Commande.objects.select_related('client').order_by('-date_creation')[:10]
    
    context = {
        'stats': stats,
        'recent_commandes': recent_commandes
    }
    return render(request, 'admin/admin_dashboard.html', context)

@admin_required
def admin_users(request):
    users = User.objects.all().order_by('-created_at')
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    users_page = paginator.get_page(page_number)
    
    context = {
        'users': users_page,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': users_page
    }
    return render(request, 'admin/admin_users.html', context)

@admin_required
def admin_create_user(request):
    if request.method == 'POST':
        try:
            username = request.POST['username']
            email = request.POST['email']
            
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
            
            messages.success(request, f'Utilisateur {username} créé avec succès!')
            return redirect('admin_users')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la création: {str(e)}')
    
    return render(request, 'admin/admin_create_user.html')

@admin_required
def admin_edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        try:
            email = request.POST['email']
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                messages.error(request, 'Cet email est déjà utilisé par un autre utilisateur.')
            else:
                user.first_name = request.POST.get('first_name', '')
                user.last_name = request.POST.get('last_name', '')
                user.email = email
                user.phone = request.POST.get('phone', '')
                user.role = request.POST['role']
                user.is_active = request.POST.get('is_active') == 'on'
                
                user.save()
                messages.success(request, 'Utilisateur mis à jour avec succès!')
                return redirect('admin_users')
                
        except Exception as e:
            messages.error(request, f'Erreur lors de la mise à jour: {str(e)}')
    
    return render(request, 'admin/admin_edit_user.html', {'user': user})

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
    paginator = Paginator(commandes, 20)
    page_number = request.GET.get('page')
    commandes_page = paginator.get_page(page_number)
    
    context = {
        'commandes': commandes_page,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': commandes_page
    }
    return render(request, 'admin/admin_commandes.html', context)

@admin_required
def admin_reports(request):
    context = {}
    return render(request, 'admin/admin_reports.html', context)

@admin_required
def admin_system_config(request):
    return render(request, 'admin/admin_system_config.html')

@admin_required
def admin_notifications(request):
    return render(request, 'admin/admin_notifications.html')

# Vues Transporteur
@transporteur_required
def transporteur_dashboard(request):
    user_id = request.session['user_id']
    
    stats = {
        'livraisons_completees': 0,
        'livraisons_en_cours': 0,
        'revenus_mois': 0,
        'note_moyenne': 4.2
    }
    
    context = {
        'stats': stats,
    }
    return render(request, 'transporteur/transporteur_dashboard.html', context)

@transporteur_required
def transporteur_commandes(request):
    commandes = Commande.objects.filter(statut='en_attente').select_related('client')
    paginator = Paginator(commandes, 12)
    page_number = request.GET.get('page')
    commandes_page = paginator.get_page(page_number)
    
    context = {
        'commandes': commandes_page,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': commandes_page,
    }
    return render(request, 'transporteur/transporteur_commandes.html', context)

@transporteur_required
def transporteur_accept_commande(request, commande_id):
    return JsonResponse({'success': False})

@transporteur_required
def transporteur_livraisons(request):
    user_id = request.session['user_id']
    livraisons = Livraison.objects.filter(
        commande__transporteur_id=user_id
    ).select_related('commande', 'vehicule').order_by('-commande__date_creation')
    
    paginator = Paginator(livraisons, 15)
    page_number = request.GET.get('page')
    livraisons_page = paginator.get_page(page_number)
    
    context = {
        'livraisons': livraisons_page,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': livraisons_page,
    }
    return render(request, 'transporteur/transporteur_livraisons.html', context)

@transporteur_required
def transporteur_update_livraison(request, livraison_id):
    return JsonResponse({'success': False})

@transporteur_required
def transporteur_vehicules(request):
    user_id = request.session['user_id']
    vehicules = Vehicule.objects.filter(transporteur_id=user_id).order_by('-id')
    
    context = {
        'vehicules': vehicules,
    }
    return render(request, 'transporteur/transporteur_vehicules.html', context)

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
    
    return render(request, 'transporteur/transporteur_add_vehicule.html')

@transporteur_required
def transporteur_itineraire(request):
    context = {}
    return render(request, 'transporteur/transporteur_itineraire.html', context)

@transporteur_required
def transporteur_profil(request):
    user_id = request.session['user_id']
    user = get_object_or_404(User, id=user_id)
    
    context = {
        'user': user,
    }
    return render(request, 'transporteur/transporteur_profil.html', context)

# Vues Client
@client_required
def client_dashboard(request):
    user_id = request.session['user_id']
    
    stats = {
        'commandes_total': Commande.objects.filter(client_id=user_id).count(),
        'commandes_en_cours': 0,
        'commandes_livrees': 0,
        'depenses_totales': 0
    }
    
    commandes_recentes = Commande.objects.filter(
        client_id=user_id
    ).order_by('-date_creation')[:5]
    
    context = {
        'stats': stats,
        'commandes_recentes': commandes_recentes,
    }
    return render(request, 'client/client_dashboard.html', context)

@client_required
def client_commandes(request):
    user_id = request.session['user_id']
    commandes = Commande.objects.filter(client_id=user_id).order_by('-date_creation')
    
    paginator = Paginator(commandes, 10)
    page_number = request.GET.get('page')
    commandes_page = paginator.get_page(page_number)
    
    context = {
        'commandes': commandes_page,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': commandes_page
    }
    return render(request, 'client/client_commandes.html', context)

@client_required
def client_nouvelle_commande(request):
    if request.method == 'POST':
        try:
            user_id = request.session['user_id']
            
            commande = Commande.objects.create(
                client_id=user_id,
                origine=request.POST['origine'],
                destination=request.POST['destination'],
                description_marchandise=request.POST['description_marchandise'],
                poids=float(request.POST['poids']),
                date_livraison_prevue=request.POST['date_livraison_prevue'],
                notes=request.POST.get('notes', ''),
                statut='en_attente'
            )
            
            messages.success(request, 'Commande créée avec succès!')
            return redirect('client_commandes')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la création de la commande: {str(e)}')
    
    return render(request, 'client/client_nouvelle_commande.html')

@client_required
def client_commande_detail(request, commande_id):
    user_id = request.session['user_id']
    commande = get_object_or_404(Commande, id=commande_id, client_id=user_id)
    
    context = {
        'commande': commande,
    }
    return render(request, 'client/client_commande_detail.html', context)

@client_required
def client_suivi_commande(request, commande_id):
    user_id = request.session['user_id']
    commande = get_object_or_404(Commande, id=commande_id, client_id=user_id)
    
    context = {
        'commande': commande,
    }
    return render(request, 'client/client_suivi_commande.html', context)

@client_required
def client_profil(request):
    user_id = request.session['user_id']
    user = get_object_or_404(User, id=user_id)
    
    context = {
        'user': user
    }
    return render(request, 'client/client_profil.html', context)

@client_required
def client_factures(request):
    user_id = request.session['user_id']
    commandes_facturees = Commande.objects.filter(
        client_id=user_id,
        statut='livree'
    ).order_by('-date_creation')
    
    paginator = Paginator(commandes_facturees, 15)
    page_number = request.GET.get('page')
    factures_page = paginator.get_page(page_number)
    
    context = {
        'factures': factures_page,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': factures_page
    }
    return render(request, 'client/client_factures.html', context)

@client_required
def client_annuler_commande(request, commande_id):
    return JsonResponse({'success': False})

# Vues Planificateur
@planificateur_required
def planificateur_dashboard(request):
    user_id = request.session['user_id']
    
    stats = {
        'commandes_a_planifier': Commande.objects.filter(statut='en_attente').count(),
        'tournees_planifiees': 0,
        'tournees_en_cours': 0,
        'commandes_planifiees_mois': 0,
    }
    
    context = {
        'stats': stats,
        'commandes_urgentes': [],
        'tournees_jour': [],
        'notifications': [],
        'efficacite_planification': 87.5,
        'temps_moyen_planification': 15,
    }
    return render(request, 'planificateur/planificateur_dashboard.html', context)

@planificateur_required
def planificateur_commandes(request):
    commandes = Commande.objects.select_related('client', 'transporteur').order_by('-date_creation')
    
    paginator = Paginator(commandes, 20)
    page_number = request.GET.get('page')
    commandes_page = paginator.get_page(page_number)
    
    context = {
        'commandes': commandes_page,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': commandes_page,
        'transporteurs_disponibles': 0,
        'vehicules_disponibles': 0,
    }
    return render(request, 'planificateur/planificateur_commandes.html', context)

@planificateur_required
def planificateur_tournees(request):
    user_id = request.session['user_id']
    tournees = Tournee.objects.filter(planificateur_id=user_id).select_related('transporteur', 'vehicule').order_by('-date_creation')
    
    paginator = Paginator(tournees, 15)
    page_number = request.GET.get('page')
    tournees_page = paginator.get_page(page_number)
    
    transporteurs = User.objects.filter(role='transporteur', is_active=True)
    
    context = {
        'tournees': tournees_page,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': tournees_page,
        'transporteurs': transporteurs,
    }
    return render(request, 'planificateur/planificateur_tournees.html', context)

@planificateur_required
def planificateur_create_tournee(request):
    if request.method == 'POST':
        messages.success(request, 'Tournée créée avec succès!')
        return redirect('planificateur_tournees')
    
    commandes_disponibles = Commande.objects.filter(statut='en_attente').order_by('date_livraison_prevue')
    transporteurs = User.objects.filter(role='transporteur', is_active=True)
    vehicules = Vehicule.objects.filter(disponible=True).select_related('transporteur')
    
    context = {
        'commandes_disponibles': commandes_disponibles,
        'transporteurs': transporteurs,
        'vehicules': vehicules,
    }
    return render(request, 'planificateur/planificateur_create_tournee.html', context)

# API
def assign_commande(request, commande_id):
    return JsonResponse({'success': False})

def update_livraison_status(request, livraison_id):
    return JsonResponse({'success': False})

def mark_notifications_read(request):
    return JsonResponse({'success': False})

def commande_details_api(request, commande_id):
    return JsonResponse({'error': 'Not implemented'}, status=500)

def vehicule_details_api(request, vehicule_id):
    return JsonResponse({'error': 'Not implemented'}, status=500)

def vehicule_update_api(request, vehicule_id):
    return JsonResponse({'error': 'Not implemented'}, status=500)

def vehicule_toggle_api(request, vehicule_id):
    return JsonResponse({'error': 'Not implemented'}, status=500)

def check_new_commandes(request):
    return JsonResponse({'hasNew': False})

def check_livraisons_updates(request):
    return JsonResponse({'hasUpdates': False})

def get_vehicules_transporteur(request, transporteur_id):
    return JsonResponse({'success': False})