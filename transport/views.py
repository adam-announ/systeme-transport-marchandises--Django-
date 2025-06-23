# transport/views.py - Vues unifiées et optimisées

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from datetime import datetime, timedelta
import csv
import json
import logging

from .models import (
    Commande, Client, Transporteur, Adresse, 
    Notification, MissionTransporteur, Incident
)
from .forms import CommandeForm, AdresseForm, InscriptionForm, IncidentForm
from .services import StatisticsService, NotificationService, PricingService
from .utils import calculer_itineraire_optimise, calculer_distance

logger = logging.getLogger(__name__)

# ==========================================
# VUES PUBLIQUES ET AUTHENTIFICATION
# ==========================================

def index(request):
    """Page d'accueil avec redirection intelligente"""
    if request.user.is_authenticated:
        user_type = get_user_type(request.user)
        
        if user_type == 'admin':
            return redirect('admin_dashboard')
        elif user_type == 'client':
            return redirect('client_dashboard')
        elif user_type == 'transporteur':
            return redirect('transporteur_dashboard')
        else:
            messages.warning(request, "Profil incomplet. Contactez l'administrateur.")
    
    # Statistiques publiques
    stats = StatisticsService.get_public_stats()
    
    return render(request, 'transport/index.html', {
        'stats': stats,
        'user_authenticated': request.user.is_authenticated,
    })

def inscription(request):
    """Inscription utilisateur"""
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        form = InscriptionForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user)
                
                type_compte = form.cleaned_data['type_compte']
                if type_compte == 'client':
                    messages.success(request, "Inscription réussie! Bienvenue.")
                    return redirect('client_dashboard')
                else:
                    messages.success(request, "Inscription réussie! Profil en attente de validation.")
                    return redirect('transporteur_dashboard')
                    
            except Exception as e:
                logger.error(f"Erreur inscription: {e}")
                messages.error(request, "Erreur lors de l'inscription.")
    else:
        form = InscriptionForm()
    
    return render(request, 'registration/inscription.html', {'form': form})

def logout_view(request):
    """Déconnexion"""
    username = request.user.username if request.user.is_authenticated else "Utilisateur"
    logout(request)
    messages.info(request, f"Au revoir {username}!")
    return redirect('index')

# ==========================================
# VUES CLIENT
# ==========================================

@login_required
def client_dashboard(request):
    """Dashboard client"""
    try:
        client = request.user.client
    except Client.DoesNotExist:
        messages.error(request, "Veuillez compléter votre profil client.")
        return redirect('index')
    
    # Statistiques optimisées
    stats = StatisticsService.get_client_stats(client)
    
    # Commandes récentes
    commandes_recentes = Commande.objects.filter(client=client).select_related(
        'transporteur', 'adresse_enlevement', 'adresse_livraison'
    ).order_by('-date_creation')[:5]
    
    # Notifications non lues
    notifications = Notification.objects.filter(
        destinataire=request.user, lu=False
    ).order_by('-date_creation')[:5]
    
    context = {
        'client': client,
        'stats': stats,
        'commandes_recentes': commandes_recentes,
        'notifications': notifications,
    }
    
    return render(request, 'transport/client_dashboard.html', context)

@login_required
def creer_commande(request):
    """Création de commande"""
    try:
        client = request.user.client
    except Client.DoesNotExist:
        messages.error(request, "Profil client requis.")
        return redirect('index')
    
    if request.method == 'POST':
        commande_form = CommandeForm(request.POST)
        adresse_enlevement_form = AdresseForm(request.POST, prefix='enlevement')
        adresse_livraison_form = AdresseForm(request.POST, prefix='livraison')
        
        if (commande_form.is_valid() and 
            adresse_enlevement_form.is_valid() and 
            adresse_livraison_form.is_valid()):
            
            try:
                # Créer les adresses
                adr_enlev = adresse_enlevement_form.save()
                adr_livr = adresse_livraison_form.save()
                
                # Créer la commande
                commande = commande_form.save(commit=False)
                commande.client = client
                commande.adresse_enlevement = adr_enlev
                commande.adresse_livraison = adr_livr
                
                # Calculer le prix
                distance = calculer_distance(adr_enlev, adr_livr)
                commande.prix_estime = PricingService.calculate_price(
                    commande.poids, distance, commande.type_marchandise, commande.priorite
                )
                
                commande.save()
                
                # Notifications
                NotificationService.notify_new_order(commande)
                
                messages.success(request, f"Commande #{commande.id} créée avec succès!")
                return redirect('suivre_commande', commande_id=commande.id)
                
            except Exception as e:
                logger.error(f"Erreur création commande: {e}")
                messages.error(request, "Erreur lors de la création.")
    else:
        commande_form = CommandeForm()
        adresse_enlevement_form = AdresseForm(prefix='enlevement')
        adresse_livraison_form = AdresseForm(prefix='livraison')
    
    context = {
        'commande_form': commande_form,
        'adresse_enlevement_form': adresse_enlevement_form,
        'adresse_livraison_form': adresse_livraison_form,
    }
    
    return render(request, 'transport/creer_commande.html', context)

@login_required
def suivre_commande(request, commande_id):
    """Suivi de commande"""
    if request.user.is_staff:
        commande = get_object_or_404(Commande, id=commande_id)
    else:
        try:
            client = request.user.client
            commande = get_object_or_404(Commande, id=commande_id, client=client)
        except Client.DoesNotExist:
            messages.error(request, "Accès refusé.")
            return redirect('index')
    
    # Mission associée
    mission = None
    if commande.transporteur:
        try:
            mission = MissionTransporteur.objects.get(commande=commande)
        except MissionTransporteur.DoesNotExist:
            pass
    
    context = {
        'commande': commande,
        'mission': mission,
    }
    
    return render(request, 'transport/suivre_commande.html', context)

@login_required
def liste_commandes(request):
    """Liste des commandes avec filtres"""
    if request.user.is_staff:
        commandes = Commande.objects.all()
    else:
        try:
            client = request.user.client
            commandes = Commande.objects.filter(client=client)
        except Client.DoesNotExist:
            messages.error(request, "Profil client requis.")
            return redirect('index')
    
    # Optimisation des requêtes
    commandes = commandes.select_related(
        'client', 'transporteur', 'adresse_enlevement', 'adresse_livraison'
    ).order_by('-date_creation')
    
    # Filtres
    statut_filter = request.GET.get('statut')
    if statut_filter:
        commandes = commandes.filter(statut=statut_filter)
    
    # Pagination
    paginator = Paginator(commandes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'statut_filter': statut_filter,
        'statuts_disponibles': Commande.STATUT_CHOICES,
    }
    
    return render(request, 'transport/liste_commandes.html', context)

# ==========================================
# VUES TRANSPORTEUR
# ==========================================

@login_required
def transporteur_dashboard(request):
    """Dashboard transporteur"""
    try:
        transporteur = request.user.transporteur
    except Transporteur.DoesNotExist:
        messages.error(request, "Profil transporteur requis.")
        return redirect('index')
    
    # Statistiques
    stats = StatisticsService.get_transporteur_stats(transporteur)
    
    # Missions actives
    missions_actives = MissionTransporteur.objects.filter(
        transporteur=transporteur, 
        statut__in=['EN_COURS', 'ASSIGNEE']
    ).select_related('commande', 'commande__client').order_by('-date_assignation')
    
    # Notifications
    notifications = Notification.objects.filter(
        destinataire=request.user, lu=False
    ).order_by('-date_creation')[:5]
    
    context = {
        'transporteur': transporteur,
        'stats': stats,
        'missions_actives': missions_actives,
        'notifications': notifications,
    }
    
    return render(request, 'transport/transporteur_dashboard.html', context)

@login_required
def voir_mission(request, mission_id):
    """Détails d'une mission"""
    try:
        transporteur = request.user.transporteur
        mission = get_object_or_404(MissionTransporteur, id=mission_id, transporteur=transporteur)
    except Transporteur.DoesNotExist:
        messages.error(request, "Accès non autorisé.")
        return redirect('index')
    
    # Calculer l'itinéraire si nécessaire
    if not mission.itineraire_optimise:
        try:
            itineraire = calculer_itineraire_optimise(
                mission.commande.adresse_enlevement,
                mission.commande.adresse_livraison
            )
            mission.itineraire_optimise = itineraire
            mission.save()
        except Exception as e:
            logger.error(f"Erreur calcul itinéraire: {e}")
    
    context = {
        'mission': mission,
        'commande': mission.commande,
    }
    
    return render(request, 'transport/voir_mission.html', context)

@login_required
def mettre_a_jour_statut(request, mission_id):
    """Mise à jour du statut de mission"""
    try:
        transporteur = request.user.transporteur
        mission = get_object_or_404(MissionTransporteur, id=mission_id, transporteur=transporteur)
    except Transporteur.DoesNotExist:
        messages.error(request, "Accès non autorisé.")
        return redirect('index')
    
    if request.method == 'POST':
        nouveau_statut = request.POST.get('statut')
        commentaire = request.POST.get('commentaire', '')
        
        # Mettre à jour la mission
        mission.statut = nouveau_statut
        
        if nouveau_statut == 'TERMINEE':
            mission.date_fin = timezone.now()
            mission.commande.statut = 'LIVREE'
        elif nouveau_statut == 'EN_COURS':
            mission.date_debut = mission.date_debut or timezone.now()
            mission.commande.statut = 'EN_TRANSIT'
        
        mission.save()
        mission.commande.save()
        
        # Notification client
        NotificationService.notify_status_change(mission, nouveau_statut, commentaire)
        
        messages.success(request, "Statut mis à jour avec succès.")
        return redirect('voir_mission', mission_id=mission.id)
    
    return render(request, 'transport/mettre_a_jour_statut.html', {'mission': mission})

@login_required
def notifier_incident(request, mission_id):
    """Signalement d'incident"""
    try:
        transporteur = request.user.transporteur
        mission = get_object_or_404(MissionTransporteur, id=mission_id, transporteur=transporteur)
    except Transporteur.DoesNotExist:
        messages.error(request, "Accès non autorisé.")
        return redirect('index')
    
    if request.method == 'POST':
        form = IncidentForm(request.POST, request.FILES)
        if form.is_valid():
            incident = form.save(commit=False)
            incident.mission = mission
            incident.transporteur = transporteur
            incident.save()
            
            # Notifications
            NotificationService.notify_incident(incident)
            
            messages.success(request, "Incident signalé avec succès.")
            return redirect('voir_mission', mission_id=mission.id)
    else:
        form = IncidentForm()
    
    return render(request, 'transport/notifier_incident.html', {
        'mission': mission,
        'form': form
    })

# ==========================================
# VUES ADMIN/PLANIFICATEUR
# ==========================================

@staff_member_required
def admin_dashboard(request):
    """Dashboard administrateur"""
    # Statistiques globales
    stats = StatisticsService.get_admin_stats()
    
    # Commandes en attente
    commandes_attente = Commande.objects.filter(
        statut='EN_ATTENTE'
    ).select_related('client').order_by('date_creation')[:10]
    
    # Transporteurs disponibles
    transporteurs_disponibles = Transporteur.objects.filter(
        disponible=True, actif=True
    ).select_related('user')[:10]
    
    # Incidents récents
    incidents_recents = Incident.objects.filter(
        resolu=False
    ).select_related('mission', 'transporteur').order_by('-date_signalement')[:5]
    
    context = {
        'stats': stats,
        'commandes_attente': commandes_attente,
        'transporteurs_disponibles': transporteurs_disponibles,
        'incidents_recents': incidents_recents,
    }
    
    return render(request, 'transport/admin_dashboard.html', context)

@staff_member_required
def affecter_commande(request, commande_id):
    """Affectation d'une commande à un transporteur"""
    commande = get_object_or_404(Commande, id=commande_id, statut='EN_ATTENTE')
    
    if request.method == 'POST':
        transporteur_id = request.POST.get('transporteur_id')
        if transporteur_id:
            transporteur = get_object_or_404(Transporteur, id=transporteur_id, disponible=True)
            
            # Vérifications
            if transporteur.capacite_charge < commande.poids:
                messages.error(request, "Capacité insuffisante.")
                return redirect('admin_dashboard')
            
            # Créer la mission
            mission = MissionTransporteur.objects.create(
                commande=commande,
                transporteur=transporteur,
                statut='ASSIGNEE'
            )
            
            # Mettre à jour la commande
            commande.statut = 'AFFECTEE'
            commande.transporteur = transporteur
            commande.save()
            
            # Notification transporteur
            NotificationService.create_notification(
                destinataire=transporteur.user,
                type_notif='MISSION',
                titre='Nouvelle mission assignée',
                message=f'Commande #{commande.id} - {commande.type_marchandise}',
                commande=commande,
                priorite='HAUTE'
            )
            
            messages.success(request, f'Commande affectée à {transporteur.user.username}')
            return redirect('admin_dashboard')
    
    # Transporteurs disponibles
    transporteurs = Transporteur.objects.filter(
        disponible=True,
        capacite_charge__gte=commande.poids
    ).select_related('user')
    
    context = {
        'commande': commande,
        'transporteurs': transporteurs,
    }
    
    return render(request, 'transport/affecter_commande.html', context)

@staff_member_required
def gestion_utilisateurs(request):
    """Gestion des utilisateurs"""
    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        
        if user_id:
            user = get_object_or_404(User, id=user_id)
            
            if action == 'toggle_active':
                user.is_active = not user.is_active
                user.save()
                status = "activé" if user.is_active else "désactivé"
                messages.success(request, f"Utilisateur {user.username} {status}")
    
    # Liste des utilisateurs avec filtres
    users = User.objects.all().order_by('-date_joined')
    
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    
    return render(request, 'transport/gestion_utilisateurs.html', context)

# ==========================================
# RAPPORTS ET EXPORTS
# ==========================================

@login_required
def generer_rapport(request):
    """Génération de rapports"""
    if request.method == 'POST':
        date_debut = datetime.strptime(request.POST['date_debut'], '%Y-%m-%d').date()
        date_fin = datetime.strptime(request.POST['date_fin'], '%Y-%m-%d').date()
        format_export = request.POST.get('format_export', 'csv')
        
        # Filtrer les commandes selon les permissions
        if request.user.is_staff:
            commandes = Commande.objects.filter(
                date_creation__date__gte=date_debut,
                date_creation__date__lte=date_fin
            ).select_related('client', 'transporteur')
        else:
            try:
                client = request.user.client
                commandes = Commande.objects.filter(
                    client=client,
                    date_creation__date__gte=date_debut,
                    date_creation__date__lte=date_fin
                )
            except Client.DoesNotExist:
                messages.error(request, "Profil client requis.")
                return redirect('index')
        
        if format_export == 'csv':
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="rapport_{date_debut}_{date_fin}.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['N° Commande', 'Date', 'Client', 'Type', 'Poids', 'Statut'])
            
            for commande in commandes:
                writer.writerow([
                    commande.id,
                    commande.date_creation.strftime('%d/%m/%Y'),
                    commande.client.user.username,
                    commande.type_marchandise,
                    commande.poids,
                    commande.get_statut_display()
                ])
            
            return response
    
    return render(request, 'transport/generer_rapport.html')

# ==========================================
# API ET UTILITAIRES
# ==========================================

@login_required
def api_notifications_count(request):
    """API pour le nombre de notifications"""
    count = Notification.objects.filter(
        destinataire=request.user,
        lu=False
    ).count()
    
    return JsonResponse({'count': count})

@login_required
def api_marquer_notification_lue(request, notification_id):
    """API pour marquer une notification comme lue"""
    if request.method == 'POST':
        try:
            notification = Notification.objects.get(
                id=notification_id,
                destinataire=request.user
            )
            notification.marquer_comme_lue()
            return JsonResponse({'success': True})
        except Notification.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Non trouvée'})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

# ==========================================
# FONCTIONS UTILITAIRES
# ==========================================

def get_user_type(user):
    """Déterminer le type d'utilisateur"""
    if user.is_superuser:
        return 'admin'
    elif user.is_staff:
        return 'admin'
    elif hasattr(user, 'client'):
        return 'client'
    elif hasattr(user, 'transporteur'):
        return 'transporteur'
    else:
        return 'incomplete'