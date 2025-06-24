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

from .models import User, Commande, Vehicule, Livraison, Notification

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
        # Rediriger selon le rôle de l'utilisateur connecté
        role = request.session.get('role')
        if role == 'admin':
            return redirect('admin_dashboard')
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
    """Décorateur pour vérifier que l'utilisateur est admin"""
    def _wrapped_view(request, *args, **kwargs):
        if 'user_id' not in request.session or request.session.get('role') != 'admin':
            messages.error(request, 'Accès non autorisé.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def transporteur_required(view_func):
    """Décorateur pour vérifier que l'utilisateur est transporteur"""
    def _wrapped_view(request, *args, **kwargs):
        if 'user_id' not in request.session or request.session.get('role') != 'transporteur':
            messages.error(request, 'Accès non autorisé.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def client_required(view_func):
    """Décorateur pour vérifier que l'utilisateur est client"""
    def _wrapped_view(request, *args, **kwargs):
        if 'user_id' not in request.session or request.session.get('role') != 'client':
            messages.error(request, 'Accès non autorisé.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# ==================== VUES ADMIN ====================

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
    return render(request, 'admin/admin_dashboard.html', context)

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
    return render(request, 'admin/admin_users.html', context)

@admin_required
def admin_create_user(request):
    if request.method == 'POST':
        try:
            # Vérifier si l'utilisateur existe déjà
            username = request.POST['username']
            email = request.POST['email']
            
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Ce nom d\'utilisateur existe déjà.')
                return render(request, 'admin/admin_create_user.html')
            
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Cet email est déjà utilisé.')
                return render(request, 'admin/admin_create_user.html')
            
            # Créer l'utilisateur
            user = User.objects.create(
                username=username,
                email=email,
                password=request.POST['password'],  # Sera hashé par le modèle
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
            # Vérifier si l'email n'est pas déjà utilisé par un autre utilisateur
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
    # Statistiques rapides
    commandes_en_attente = Commande.objects.filter(statut='en_attente').count()
    commandes_en_cours = Commande.objects.filter(statut='en_cours').count()
    commandes_livrees = Commande.objects.filter(statut='livree').count()
    
    # Toutes les commandes
    commandes = Commande.objects.select_related('client', 'transporteur').order_by('-date_creation')
    
    # Pagination
    paginator = Paginator(commandes, 20)
    page_number = request.GET.get('page')
    commandes_page = paginator.get_page(page_number)
    
    context = {
        'commandes': commandes_page,
        'commandes_en_attente': commandes_en_attente,
        'commandes_en_cours': commandes_en_cours,
        'commandes_livrees': commandes_livrees,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': commandes_page
    }
    return render(request, 'admin/admin_commandes.html', context)

@admin_required
def admin_reports(request):
    # Données pour les rapports (simulées)
    from datetime import datetime, timedelta
    
    # Métriques principales
    metrics = {
        'revenus_totaux': Commande.objects.filter(statut='livree').aggregate(
            total=Sum('prix'))['total'] or 0,
        'commandes_traitees': Commande.objects.filter(statut='livree').count(),
        'taux_satisfaction': 85,  # À calculer selon votre système de notation
        'delai_moyen': 24,  # En heures
        'croissance_revenus': 12.5,
        'croissance_commandes': 8.3,
        'amelioration_delai': 2.1,
        'taux_ponctualite': 92,
        'temps_prise_charge': 2.5,
        'taux_incidents': 1.8,
        'capacite_utilisee': 78
    }
    
    # Données pour les graphiques (simulées)
    chart_labels = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin']
    chart_revenus = [12000, 15000, 13500, 18000, 20000, 22000]
    vehicules_repartition = [45, 35, 20]  # Camionnettes, Camions, Semi-remorques
    
    # Top transporteurs (simulé)
    top_transporteurs = User.objects.filter(role='transporteur')[:10]
    for transporteur in top_transporteurs:
        transporteur.total_livraisons = Livraison.objects.filter(
            commande__transporteur=transporteur, statut='livree').count()
        transporteur.total_revenus = Commande.objects.filter(
            transporteur=transporteur, statut='livree').aggregate(
            total=Sum('prix'))['total'] or 0
        transporteur.note_moyenne = 4.2  # À calculer selon votre système
    
    # Top destinations (simulé)
    top_destinations = [
        {'ville': 'Casablanca', 'total_commandes': 156, 'total_poids': 12500, 'total_revenus': 45000},
        {'ville': 'Rabat', 'total_commandes': 134, 'total_poids': 9800, 'total_revenus': 38000},
        {'ville': 'Marrakech', 'total_commandes': 98, 'total_poids': 7500, 'total_revenus': 28000},
        {'ville': 'Fès', 'total_commandes': 87, 'total_poids': 6200, 'total_revenus': 24000},
        {'ville': 'Tanger', 'total_commandes': 76, 'total_poids': 5800, 'total_revenus': 22000},
    ]
    
    context = {
        'metrics': metrics,
        'chart_labels': json.dumps(chart_labels),
        'chart_revenus': json.dumps(chart_revenus),
        'vehicules_repartition': json.dumps(vehicules_repartition),
        'top_transporteurs': top_transporteurs,
        'top_destinations': top_destinations
    }
    
    return render(request, 'admin/admin_reports.html', context)

@admin_required
def admin_system_config(request):
    if request.method == 'POST':
        # Ici vous pourriez sauvegarder les configurations dans une table Settings
        # ou dans un fichier de configuration
        messages.success(request, 'Configuration mise à jour avec succès!')
    
    return render(request, 'admin/admin_system_config.html')

@admin_required
def admin_notifications(request):
    if request.method == 'POST':
        try:
            destinataires = request.POST['destinataires']
            type_notification = request.POST['type_notification']
            titre = request.POST['titre']
            message = request.POST['message']
            
            # Déterminer les utilisateurs cibles
            users = []
            if destinataires == 'all':
                users = User.objects.filter(is_active=True)
            elif destinataires == 'clients':
                users = User.objects.filter(role='client', is_active=True)
            elif destinataires == 'transporteurs':
                users = User.objects.filter(role='transporteur', is_active=True)
            elif destinataires == 'admins':
                users = User.objects.filter(role='admin', is_active=True)
            
            # Créer les notifications
            notifications = []
            for user in users:
                notifications.append(Notification(
                    utilisateur=user,
                    type_notification=type_notification,
                    titre=titre,
                    message=message
                ))
            
            Notification.objects.bulk_create(notifications)
            
            messages.success(request, f'Notification envoyée à {len(users)} utilisateur(s)!')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de l\'envoi: {str(e)}')
    
    return render(request, 'admin/admin_notifications.html')

# ==================== VUES TRANSPORTEUR ====================

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
    
    # Compteurs pour la sidebar - CORRECTION ICI
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
        'livraisons_actives': livraisons_actives,  # VARIABLE CORRIGÉE
        'transporteur_disponible': True  # À implémenter selon votre logique
    }
    return render(request, 'transporteur/transporteur_dashboard.html', context)
# ==================== VUES CLIENT ====================

@client_required
def client_dashboard(request):
    user_id = request.session['user_id']
    
    # Statistiques du client
    stats = {
        'commandes_total': Commande.objects.filter(client_id=user_id).count(),
        'commandes_en_cours': Commande.objects.filter(
            client_id=user_id,
            statut__in=['en_attente', 'affectee', 'en_cours']
        ).count(),
        'commandes_livrees': Commande.objects.filter(
            client_id=user_id,
            statut='livree'
        ).count(),
        'depenses_totales': Commande.objects.filter(
            client_id=user_id,
            statut='livree'
        ).aggregate(total=Sum('prix'))['total'] or 0
    }
    
    # Commandes récentes
    commandes_recentes = Commande.objects.filter(
        client_id=user_id
    ).order_by('-date_creation')[:5]
    
    # Notifications récentes
    notifications = Notification.objects.filter(
        utilisateur_id=user_id
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
    date_debut = request.GET.get('date_debut', '')
    date_fin = request.GET.get('date_fin', '')
    
    commandes = Commande.objects.filter(client_id=user_id)
    
    if statut_filter:
        commandes = commandes.filter(statut=statut_filter)
    if date_debut:
        commandes = commandes.filter(date_creation__gte=date_debut)
    if date_fin:
        commandes = commandes.filter(date_creation__lte=date_fin)
    
    commandes = commandes.order_by('-date_creation')
    
    # Pagination
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
                prix=float(request.POST.get('prix', 0)) if request.POST.get('prix') else None,
                notes=request.POST.get('notes', ''),
                statut='en_attente'
            )
            
            # Créer une notification pour les transporteurs
            transporteurs = User.objects.filter(role='transporteur', is_active=True)
            for transporteur in transporteurs:
                Notification.objects.create(
                    utilisateur=transporteur,
                    type_notification='nouvelle_commande',
                    titre='Nouvelle commande disponible',
                    message=f'Nouvelle commande #{commande.id} de {commande.origine} vers {commande.destination}.'
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
    
    # Récupérer la livraison associée si elle existe
    livraison = None
    try:
        livraison = Livraison.objects.get(commande=commande)
    except Livraison.DoesNotExist:
        pass
    
    context = {
        'commande': commande,
        'livraison': livraison
    }
    return render(request, 'client/client_commande_detail.html', context)

@client_required
def client_suivi_commande(request, commande_id):
    user_id = request.session['user_id']
    commande = get_object_or_404(Commande, id=commande_id, client_id=user_id)
    
    # Récupérer la livraison et l'historique
    livraison = None
    historique = []
    
    try:
        livraison = Livraison.objects.get(commande=commande)
        # Ici, vous pourriez ajouter un modèle HistoriqueLivraison pour tracer les étapes
        historique = [
            {
                'date': commande.date_creation,
                'statut': 'Commande créée',
                'description': 'Votre commande a été enregistrée dans le système'
            }
        ]
        
        if commande.statut == 'affectee':
            historique.append({
                'date': livraison.date_debut or timezone.now(),
                'statut': 'Commande affectée',
                'description': f'Votre commande a été affectée au transporteur {commande.transporteur.first_name} {commande.transporteur.last_name}'
            })
        
        if livraison.statut == 'en_cours':
            historique.append({
                'date': livraison.date_debut or timezone.now(),
                'statut': 'Livraison en cours',
                'description': 'Votre commande est en cours de livraison'
            })
        
        if livraison.statut == 'livree':
            historique.append({
                'date': livraison.date_fin or timezone.now(),
                'statut': 'Commande livrée',
                'description': 'Votre commande a été livrée avec succès'
            })
            
    except Livraison.DoesNotExist:
        pass
    
    context = {
        'commande': commande,
        'livraison': livraison,
        'historique': historique
    }
    return render(request, 'client/client_suivi_commande.html', context)

@client_required
def client_profil(request):
    user_id = request.session['user_id']
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        try:
            user.first_name = request.POST['first_name']
            user.last_name = request.POST['last_name']
            user.email = request.POST['email']
            user.phone = request.POST.get('phone', '')
            
            # Vérifier si l'email n'est pas déjà utilisé par un autre utilisateur
            if User.objects.filter(email=user.email).exclude(id=user.id).exists():
                messages.error(request, 'Cet email est déjà utilisé par un autre utilisateur.')
            else:
                user.save()
                
                # Mettre à jour la session
                request.session['first_name'] = user.first_name
                request.session['last_name'] = user.last_name
                
                messages.success(request, 'Profil mis à jour avec succès!')
                
        except Exception as e:
            messages.error(request, f'Erreur lors de la mise à jour: {str(e)}')
    
    context = {
        'user': user
    }
    return render(request, 'client/client_profil.html', context)

@client_required
def client_factures(request):
    user_id = request.session['user_id']
    
    # Commandes facturées (livrées avec un prix)
    commandes_facturees = Commande.objects.filter(
        client_id=user_id,
        statut='livree',
        prix__isnull=False
    ).order_by('-date_creation')
    
    # Calculs
    total_factures = commandes_facturees.count()
    montant_total = commandes_facturees.aggregate(total=Sum('prix'))['total'] or 0
    
    # Pagination
    paginator = Paginator(commandes_facturees, 15)
    page_number = request.GET.get('page')
    factures_page = paginator.get_page(page_number)
    
    context = {
        'factures': factures_page,
        'total_factures': total_factures,
        'montant_total': montant_total,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': factures_page
    }
    return render(request, 'client/client_factures.html', context)

@client_required
def client_annuler_commande(request, commande_id):
    if request.method == 'POST':
        try:
            user_id = request.session['user_id']
            commande = get_object_or_404(
                Commande, 
                id=commande_id, 
                client_id=user_id,
                statut__in=['en_attente', 'affectee']  # On ne peut annuler que si pas encore en cours
            )
            
            commande.statut = 'annulee'
            commande.save()
            
            # Notifier le transporteur s'il y en a un
            if commande.transporteur:
                Notification.objects.create(
                    utilisateur=commande.transporteur,
                    type_notification='commande_affectee',
                    titre='Commande annulée',
                    message=f'La commande #{commande.id} a été annulée par le client.'
                )
            
            # Libérer le véhicule s'il y a une livraison
            try:
                livraison = Livraison.objects.get(commande=commande)
                livraison.vehicule.disponible = True
                livraison.vehicule.save()
                livraison.delete()
            except Livraison.DoesNotExist:
                pass
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False})

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

# ==================== API SUPPLÉMENTAIRES ====================

def commande_details_api(request, commande_id):
    """API pour récupérer les détails d'une commande"""
    try:
        commande = get_object_or_404(Commande, id=commande_id)
        
        # Vérifier les permissions
        user_id = request.session.get('user_id')
        role = request.session.get('role')
        
        if role == 'client' and commande.client_id != user_id:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        elif role == 'transporteur' and commande.transporteur_id != user_id:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        elif role not in ['admin', 'client', 'transporteur']:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Récupérer la livraison si elle existe
        livraison = None
        try:
            livraison = Livraison.objects.get(commande=commande)
        except Livraison.DoesNotExist:
            pass
        
        data = {
            'id': commande.id,
            'origine': commande.origine,
            'destination': commande.destination,
            'description_marchandise': commande.description_marchandise,
            'poids': float(commande.poids),
            'prix': float(commande.prix) if commande.prix else None,
            'statut': commande.statut,
            'statut_display': commande.get_statut_display(),
            'date_creation': commande.date_creation.strftime('%d/%m/%Y %H:%M'),
            'date_livraison_prevue': commande.date_livraison_prevue.strftime('%d/%m/%Y %H:%M'),
            'notes': commande.notes,
            'client': {
                'nom': f"{commande.client.first_name} {commande.client.last_name}",
                'email': commande.client.email,
                'phone': commande.client.phone
            } if commande.client else None,
            'transporteur': {
                'nom': f"{commande.transporteur.first_name} {commande.transporteur.last_name}",
                'email': commande.transporteur.email,
                'phone': commande.transporteur.phone
            } if commande.transporteur else None,
            'livraison': {
                'statut': livraison.statut,
                'statut_display': livraison.get_statut_display(),
                'position_actuelle': livraison.position_actuelle,
                'date_debut': livraison.date_debut.strftime('%d/%m/%Y %H:%M') if livraison.date_debut else None,
                'date_fin': livraison.date_fin.strftime('%d/%m/%Y %H:%M') if livraison.date_fin else None,
                'notes_livraison': livraison.notes_livraison,
                'vehicule': {
                    'immatriculation': livraison.vehicule.immatriculation,
                    'type': livraison.vehicule.get_type_vehicule_display(),
                    'capacite': float(livraison.vehicule.capacite_max)
                }
            } if livraison else None
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def vehicule_details_api(request, vehicule_id):
    """API pour récupérer les détails d'un véhicule"""
    try:
        user_id = request.session.get('user_id')
        role = request.session.get('role')
        
        if role == 'transporteur':
            vehicule = get_object_or_404(Vehicule, id=vehicule_id, transporteur_id=user_id)
        elif role == 'admin':
            vehicule = get_object_or_404(Vehicule, id=vehicule_id)
        else:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        data = {
            'id': vehicule.id,
            'immatriculation': vehicule.immatriculation,
            'type_vehicule': vehicule.type_vehicule,
            'type_vehicule_display': vehicule.get_type_vehicule_display(),
            'capacite_max': float(vehicule.capacite_max),
            'disponible': vehicule.disponible,
            'transporteur': {
                'nom': f"{vehicule.transporteur.first_name} {vehicule.transporteur.last_name}",
                'email': vehicule.transporteur.email
            }
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def vehicule_update_api(request, vehicule_id):
    """API pour mettre à jour un véhicule"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        user_id = request.session.get('user_id')
        role = request.session.get('role')
        
        if role == 'transporteur':
            vehicule = get_object_or_404(Vehicule, id=vehicule_id, transporteur_id=user_id)
        elif role == 'admin':
            vehicule = get_object_or_404(Vehicule, id=vehicule_id)
        else:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        data = json.loads(request.body)
        
        # Mise à jour des champs
        if 'immatriculation' in data:
            vehicule.immatriculation = data['immatriculation']
        if 'type_vehicule' in data:
            vehicule.type_vehicule = data['type_vehicule']
        if 'capacite_max' in data:
            vehicule.capacite_max = data['capacite_max']
        if 'disponible' in data:
            vehicule.disponible = data['disponible']
        
        vehicule.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Véhicule mis à jour avec succès'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

def vehicule_toggle_api(request, vehicule_id):
    """API pour changer la disponibilité d'un véhicule"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        user_id = request.session.get('user_id')
        role = request.session.get('role')
        
        if role == 'transporteur':
            vehicule = get_object_or_404(Vehicule, id=vehicule_id, transporteur_id=user_id)
        elif role == 'admin':
            vehicule = get_object_or_404(Vehicule, id=vehicule_id)
        else:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Vérifier si le véhicule n'est pas en cours d'utilisation
        if vehicule.disponible == True:
            # Vérifier s'il y a des livraisons en cours avec ce véhicule
            livraisons_actives = Livraison.objects.filter(
                vehicule=vehicule,
                statut__in=['en_attente', 'en_cours']
            ).exists()
            
            if livraisons_actives:
                return JsonResponse({
                    'success': False,
                    'message': 'Impossible de désactiver un véhicule en cours d\'utilisation'
                })
        
        vehicule.disponible = not vehicule.disponible
        vehicule.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Véhicule {"activé" if vehicule.disponible else "désactivé"} avec succès'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

def check_new_commandes(request):
    """API pour vérifier s'il y a de nouvelles commandes pour les transporteurs"""
    try:
        # Cette fonction pourrait utiliser un cache ou une base de données
        # pour détecter les nouvelles commandes depuis la dernière vérification
        
        # Pour la démo, on retourne toujours False
        # Dans un vrai système, vous pourriez utiliser Redis ou une table de cache
        
        return JsonResponse({'hasNew': False})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def check_livraisons_updates(request):
    """API pour vérifier s'il y a des mises à jour sur les livraisons"""
    try:
        user_id = request.session.get('user_id')
        role = request.session.get('role')
        
        if not user_id:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
        
        # Logique similaire à check_new_commandes
        # Vous pourriez vérifier les timestamps de dernière modification
        
        return JsonResponse({'hasUpdates': False})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500).objects.filter(statut='en_attente').count()
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
    return render(request, 'transporteur/transporteur_dashboard.html', context)

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
    return render(request, 'transporteur/transporteur_commandes.html', context)

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
    return render(request, 'transporteur/transporteur_livraisons.html', context)

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
    
    # Statistiques rapides
    vehicules_disponibles = vehicules.filter(disponible=True).count()
    vehicules_en_service = vehicules.filter(disponible=False).count()
    capacite_totale = vehicules.aggregate(total=Sum('capacite_max'))['total'] or 0
    
    # Compteurs pour la sidebar
    commandes_disponibles = Commande.objects.filter(statut='en_attente').count()
    livraisons_actives = Livraison.objects.filter(
        commande__transporteur_id=user_id,
        statut__in=['en_attente', 'en_cours']
    ).count()
    
    context = {
        'vehicules': vehicules,
        'vehicules_disponibles': vehicules_disponibles,
        'vehicules_en_service': vehicules_en_service,
        'capacite_totale': int(capacite_totale),
        'commandes_disponibles': commandes_disponibles,
        'livraisons_actives': livraisons_actives
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
                marque=request.POST.get('marque', ''),
                modele=request.POST.get('modele', ''),
                annee=int(request.POST.get('annee', 0)) if request.POST.get('annee') else None,
                couleur=request.POST.get('couleur', ''),
                notes=request.POST.get('notes', ''),
                disponible=True
            )
            
            messages.success(request, 'Véhicule ajouté avec succès.')
            return redirect('transporteur_vehicules')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de l\'ajout du véhicule: {str(e)}')
    
    return render(request, 'transporteur/transporteur_add_vehicule.html')

# Ajoutez cette correction à la fin de votre fichier utilisateurs/views.py
# Remplacez la fonction transporteur_itineraire incomplète par celle-ci :

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
    livraisons_actives = Livraison.objects.filter(
        commande__transporteur_id=user_id,
        statut__in=['en_attente', 'en_cours']
    ).count()
    
    context = {
        'livraisons_en_cours': livraisons_en_cours,
        'commandes_disponibles': commandes_disponibles,
        'livraisons_actives': livraisons_actives
    }
    return render(request, 'transporteur/transporteur_itineraire.html', context)

# Ajoutez aussi ces API endpoints manquants :

def check_new_commandes(request):
    """API pour vérifier s'il y a de nouvelles commandes pour les transporteurs"""
    try:
        # Cette fonction pourrait utiliser un cache ou une base de données
        # pour détecter les nouvelles commandes depuis la dernière vérification
        
        # Pour la démo, on retourne toujours False
        # Dans un vrai système, vous pourriez utiliser Redis ou une table de cache
        
        return JsonResponse({'hasNew': False})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def check_livraisons_updates(request):
    """API pour vérifier s'il y a des mises à jour sur les livraisons"""
    try:
        user_id = request.session.get('user_id')
        role = request.session.get('role')
        
        if not user_id:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
        
        # Logique similaire à check_new_commandes
        # Vous pourriez vérifier les timestamps de dernière modification
        
        return JsonResponse({'hasUpdates': False})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
# 1. Ajoutez cette vue dans utilisateurs/views.py

@transporteur_required
def transporteur_profil(request):
    user_id = request.session['user_id']
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        try:
            user.first_name = request.POST['first_name']
            user.last_name = request.POST['last_name']
            user.email = request.POST['email']
            user.phone = request.POST.get('phone', '')
            
            # Vérifier si l'email n'est pas déjà utilisé par un autre utilisateur
            if User.objects.filter(email=user.email).exclude(id=user.id).exists():
                messages.error(request, 'Cet email est déjà utilisé par un autre utilisateur.')
            else:
                user.save()
                
                # Mettre à jour la session
                request.session['first_name'] = user.first_name
                request.session['last_name'] = user.last_name
                
                messages.success(request, 'Profil mis à jour avec succès!')
                
        except Exception as e:
            messages.error(request, f'Erreur lors de la mise à jour: {str(e)}')
    
    # Statistiques du transporteur
    stats = {
        'total_livraisons': Livraison.objects.filter(
            commande__transporteur_id=user_id,
            statut='livree'
        ).count(),
        'revenus_totaux': Commande.objects.filter(
            transporteur_id=user_id,
            statut='livree'
        ).aggregate(total=Sum('prix'))['total'] or 0,
        'vehicules_actifs': Vehicule.objects.filter(
            transporteur_id=user_id,
            disponible=True
        ).count(),
        'note_moyenne': 4.2  # À calculer selon votre système de notation
    }
    
    # Véhicules du transporteur
    vehicules = Vehicule.objects.filter(transporteur_id=user_id)
    
    # Compteurs pour la sidebar
    commandes_disponibles = Commande.objects.filter(statut='en_attente').count()
    livraisons_actives = Livraison.objects.filter(
        commande__transporteur_id=user_id,
        statut__in=['en_attente', 'en_cours']
    ).count()
    
    context = {
        'user': user,
        'stats': stats,
        'vehicules': vehicules,
        'commandes_disponibles': commandes_disponibles,
        'livraisons_actives': livraisons_actives
    }
    return render(request, 'transporteur/transporteur_profil.html', context)