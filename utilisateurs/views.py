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
from .services.api_service import TransportAPIService
import json
from datetime import datetime, timedelta
from django.db import transaction
from .models import User, Commande, Vehicule, Livraison, Notification, Tournee, EtapeTournee
import math
# === IMPORT DES VUES ADMIN ===
from .views_complete import (
    admin_dashboard,
    admin_users,
    admin_create_user,
    admin_edit_user,
    admin_toggle_user,
    admin_commandes,
    admin_reports,
    admin_system_config,
    admin_notifications
)

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
                
                # Redirection selon le rôle
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

# ==================== VUES PLANIFICATEUR ====================

@planificateur_required
def planificateur_dashboard(request):
    user_id = request.session['user_id']
    
    # Statistiques du planificateur
    stats = {
        'commandes_a_planifier': Commande.objects.filter(
            statut='en_attente'
        ).count(),
        'tournees_planifiees': Tournee.objects.filter(
            planificateur_id=user_id,
            statut='planifiee'
        ).count(),
        'tournees_en_cours': Tournee.objects.filter(
            planificateur_id=user_id,
            statut='en_cours'
        ).count(),
        'commandes_planifiees_mois': Commande.objects.filter(
            planificateur_id=user_id,
            date_creation__gte=timezone.now().replace(day=1),
            statut__in=['planifiee', 'en_cours', 'livree']
        ).count(),
    }
    
    # Commandes urgentes à planifier
    commandes_urgentes = Commande.objects.filter(
        statut='en_attente',
        priorite='urgente'
    ).order_by('date_livraison_prevue')[:5]
    
    # Tournées du jour
    aujourd_hui = timezone.now().date()
    tournees_jour = Tournee.objects.filter(
        planificateur_id=user_id,
        date_debut_prevue__date=aujourd_hui
    ).select_related('transporteur', 'vehicule')
    
    # Notifications récentes
    notifications = Notification.objects.filter(
        utilisateur_id=user_id
    ).order_by('-date_creation')[:5]
    
    # Métriques de performance
    efficacite_planification = 87.5  # Pourcentage de réussite
    temps_moyen_planification = 15   # Minutes
    
    context = {
        'stats': stats,
        'commandes_urgentes': commandes_urgentes,
        'tournees_jour': tournees_jour,
        'notifications': notifications,
        'efficacite_planification': efficacite_planification,
        'temps_moyen_planification': temps_moyen_planification,
    }
    return render(request, 'planificateur/planificateur_dashboard.html', context)

@planificateur_required
def planificateur_commandes(request):
    user_id = request.session['user_id']
    
    # Filtres
    statut_filter = request.GET.get('statut', 'en_attente')
    priorite_filter = request.GET.get('priorite', '')
    ville_filter = request.GET.get('ville', '')
    date_filter = request.GET.get('date', '')
    
    # Requête de base
    commandes = Commande.objects.select_related('client', 'transporteur')
    
    if statut_filter:
        commandes = commandes.filter(statut=statut_filter)
    if priorite_filter:
        commandes = commandes.filter(priorite=priorite_filter)
    if ville_filter:
        commandes = commandes.filter(
            Q(origine__icontains=ville_filter) | 
            Q(destination__icontains=ville_filter)
        )
    if date_filter:
        commandes = commandes.filter(date_livraison_prevue__date=date_filter)
    
    commandes = commandes.order_by('-priorite', 'date_livraison_prevue')
    
    # Pagination
    paginator = Paginator(commandes, 20)
    page_number = request.GET.get('page')
    commandes_page = paginator.get_page(page_number)
    
    # Transporteurs et véhicules disponibles
    transporteurs_disponibles = User.objects.filter(
        role='transporteur',
        is_active=True
    ).count()
    
    vehicules_disponibles = Vehicule.objects.filter(
        disponible=True
    ).count()
    
    context = {
        'commandes': commandes_page,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': commandes_page,
        'transporteurs_disponibles': transporteurs_disponibles,
        'vehicules_disponibles': vehicules_disponibles,
        'statut_filter': statut_filter,
        'priorite_filter': priorite_filter,
        'ville_filter': ville_filter,
        'date_filter': date_filter,
    }
    return render(request, 'planificateur/planificateur_commandes.html', context)

@planificateur_required
def planificateur_tournees(request):
    user_id = request.session['user_id']
    
    # Filtres
    statut_filter = request.GET.get('statut', '')
    transporteur_filter = request.GET.get('transporteur', '')
    date_filter = request.GET.get('date', '')
    
    # Requête de base
    tournees = Tournee.objects.filter(planificateur_id=user_id)
    
    if statut_filter:
        tournees = tournees.filter(statut=statut_filter)
    if transporteur_filter:
        tournees = tournees.filter(transporteur_id=transporteur_filter)
    if date_filter:
        tournees = tournees.filter(date_debut_prevue__date=date_filter)
    
    tournees = tournees.select_related('transporteur', 'vehicule').order_by('-date_creation')
    
    # Pagination
    paginator = Paginator(tournees, 15)
    page_number = request.GET.get('page')
    tournees_page = paginator.get_page(page_number)
    
    # Transporteurs pour le filtre
    transporteurs = User.objects.filter(role='transporteur', is_active=True)
    
    context = {
        'tournees': tournees_page,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': tournees_page,
        'transporteurs': transporteurs,
        'statut_filter': statut_filter,
        'transporteur_filter': transporteur_filter,
        'date_filter': date_filter,
    }
    return render(request, 'planificateur/planificateur_tournees.html', context)

@planificateur_required
def planificateur_create_tournee(request):
    if request.method == 'POST':
        try:
            user_id = request.session['user_id']
            
            with transaction.atomic():
                # Créer la tournée
                tournee = Tournee.objects.create(
                    nom=request.POST['nom'],
                    planificateur_id=user_id,
                    transporteur_id=request.POST['transporteur_id'],
                    vehicule_id=request.POST['vehicule_id'],
                    date_debut_prevue=request.POST['date_debut_prevue'],
                    date_fin_prevue=request.POST['date_fin_prevue'],
                    notes=request.POST.get('notes', '')
                )
                
                # Ajouter les commandes sélectionnées
                commandes_ids = request.POST.getlist('commandes[]')
                ordre = 1
                
                # Étape de départ (dépôt)
                EtapeTournee.objects.create(
                    tournee=tournee,
                    ordre=ordre,
                    type_etape='depot',
                    adresse='Dépôt - Point de départ',
                    heure_prevue=tournee.date_debut_prevue,
                    duree_prevue=timedelta(minutes=30)
                )
                ordre += 1
                
                for commande_id in commandes_ids:
                    commande = Commande.objects.get(id=commande_id)
                    
                    # Étape de collecte
                    EtapeTournee.objects.create(
                        tournee=tournee,
                        commande=commande,
                        ordre=ordre,
                        type_etape='collecte',
                        adresse=commande.origine,
                        heure_prevue=tournee.date_debut_prevue + timedelta(hours=ordre),
                        duree_prevue=timedelta(minutes=45)
                    )
                    ordre += 1
                    
                    # Étape de livraison
                    EtapeTournee.objects.create(
                        tournee=tournee,
                        commande=commande,
                        ordre=ordre,
                        type_etape='livraison',
                        adresse=commande.destination,
                        heure_prevue=tournee.date_debut_prevue + timedelta(hours=ordre),
                        duree_prevue=timedelta(minutes=30)
                    )
                    ordre += 1
                    
                    # Mettre à jour la commande
                    commande.statut = 'planifiee'
                    commande.planificateur_id = user_id
                    commande.date_livraison_planifiee = tournee.date_debut_prevue + timedelta(hours=ordre-1)
                    commande.save()
                    
                    # Créer la livraison
                    Livraison.objects.create(
                        commande=commande,
                        vehicule=tournee.vehicule,
                        tournee=tournee,
                        statut='en_attente'
                    )
                
                # Étape de retour (dépôt)
                EtapeTournee.objects.create(
                    tournee=tournee,
                    ordre=ordre,
                    type_etape='depot',
                    adresse='Dépôt - Point de retour',
                    heure_prevue=tournee.date_fin_prevue,
                    duree_prevue=timedelta(minutes=15)
                )
                
                # Notifications
                Notification.objects.create(
                    utilisateur=tournee.transporteur,
                    type_notification='tournee_creee',
                    titre='Nouvelle tournée assignée',
                    message=f'Une nouvelle tournée "{tournee.nom}" vous a été assignée.',
                    tournee=tournee
                )
                
                for commande_id in commandes_ids:
                    commande = Commande.objects.get(id=commande_id)
                    Notification.objects.create(
                        utilisateur=commande.client,
                        type_notification='commande_planifiee',
                        titre='Commande planifiée',
                        message=f'Votre commande #{commande.id} a été planifiée dans une tournée.',
                        commande=commande,
                        tournee=tournee
                    )
                
                messages.success(request, f'Tournée "{tournee.nom}" créée avec succès!')
                return redirect('planificateur_tournees')
                
        except Exception as e:
            messages.error(request, f'Erreur lors de la création de la tournée: {str(e)}')
    
    # Données pour le formulaire
    commandes_disponibles = Commande.objects.filter(statut='en_attente').order_by('date_livraison_prevue')
    transporteurs = User.objects.filter(role='transporteur', is_active=True)
    vehicules = Vehicule.objects.filter(disponible=True).select_related('transporteur')
    
    context = {
        'commandes_disponibles': commandes_disponibles,
        'transporteurs': transporteurs,
        'vehicules': vehicules,
    }
    return render(request, 'planificateur/planificateur_create_tournee.html', context)

@planificateur_required
def planificateur_tournee_detail(request, tournee_id):
    # À compléter selon les besoins
    return render(request, 'planificateur/planificateur_tournee_detail.html', {'tournee_id': tournee_id})

@planificateur_required
def planificateur_optimiser_tournee(request, tournee_id):
    # À compléter selon les besoins
    return render(request, 'planificateur/planificateur_optimiser_tournee.html', {'tournee_id': tournee_id})

@planificateur_required
def planificateur_affecter_commande(request):
    # À compléter selon les besoins
    return render(request, 'planificateur/planificateur_affecter_commande.html')

@planificateur_required
def planificateur_analytics(request):
    # À compléter selon les besoins
    return render(request, 'planificateur/planificateur_analytics.html')

@planificateur_required
def planificateur_profil(request):
    # À compléter selon les besoins
    return render(request, 'planificateur/planificateur_profil.html')

# API pour obtenir les véhicules d'un transporteur
def get_vehicules_transporteur(request, transporteur_id):
    if request.method == 'GET':
        try:
            vehicules = Vehicule.objects.filter(
                transporteur_id=transporteur_id,
                disponible=True
            ).values('id', 'immatriculation', 'type_vehicule', 'capacite_max')
            
            return JsonResponse({
                'success': True,
                'vehicules': list(vehicules)
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False})

def transporteur_profil(request):
    # À compléter selon les besoins
    return render(request, 'transporteur/transporteur_profil.html')