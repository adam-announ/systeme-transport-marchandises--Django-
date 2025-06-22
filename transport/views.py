# transport/views.py - Version complète et organisée

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Q, Count, Sum
from django.contrib.auth.models import User
import csv
import json

from .models import (
    Commande, Client, Transporteur, Adresse, SupportMessage, 
    Notification, ParametreSysteme, MissionTransporteur
)
from .forms import CommandeForm, AdresseForm, InscriptionForm, RapportForm


# ===========================
# VUES PUBLIQUES (Sans authentification)
# ===========================

def index(request):
    """Page d'accueil principale - CORRIGÉE"""
    # Ne pas faire de redirection automatique, afficher la page d'accueil
    
    # Si l'utilisateur est connecté, on peut afficher des infos personnalisées
    # mais on reste sur la page d'accueil
    if request.user.is_authenticated:
        context = {
            'user_authenticated': True,
            'user_type': get_user_type(request.user),
            'quick_stats': get_quick_stats() if request.user.is_staff else None,
        }
    else:
        context = {
            'user_authenticated': False,
            'public_stats': get_public_stats(),
        }
    
    # Toujours afficher la page d'accueil, pas de redirection automatique
    return render(request, 'transport/index.html', context)

def get_user_type(user):
    """Déterminer le type d'utilisateur"""
    if user.is_superuser:
        return 'admin'
    elif user.is_staff:
        return 'planificateur'
    elif hasattr(user, 'client'):
        return 'client'
    elif hasattr(user, 'transporteur'):
        return 'transporteur'
    else:
        return 'user'

def get_quick_stats():
    """Statistiques rapides pour les utilisateurs connectés"""
    try:
        return {
            'commandes_attente': Commande.objects.filter(statut='EN_ATTENTE').count(),
            'transporteurs_disponibles': Transporteur.objects.filter(disponible=True).count(),
            'missions_en_cours': MissionTransporteur.objects.filter(statut='EN_COURS').count(),
        }
    except:
        return {}

def get_public_stats():
    """Statistiques publiques pour la page d'accueil"""
    try:
        return {
            'total_livraisons': Commande.objects.filter(statut='LIVREE').count(),
            'clients_satisfaits': Client.objects.count(),
            'transporteurs_actifs': Transporteur.objects.filter(disponible=True).count(),
            'villes_couvertes': 15,  # Nombre fixe ou calculé
        }
    except:
        return {
            'total_livraisons': 1000,
            'clients_satisfaits': 250,
            'transporteurs_actifs': 50,
            'villes_couvertes': 15,
        }


def home_modern(request):
    """Page d'accueil moderne avec design attractif"""
    stats = get_public_stats()
    context = {
        'stats': stats,
        'user_authenticated': request.user.is_authenticated,
        'user_type': get_user_type(request.user) if request.user.is_authenticated else None,
    }
    return render(request, 'transport/home_modern.html', context)


def inscription(request):
    """Inscription d'un nouvel utilisateur (client ou transporteur)"""
    if request.user.is_authenticated:
        messages.info(request, "Vous êtes déjà connecté.")
        return redirect('index')
    
    if request.method == 'POST':
        form = InscriptionForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Inscription réussie! Bienvenue sur TransportPro.")
            
            # Redirection selon le type de compte
            if form.cleaned_data['type_compte'] == 'client':
                return redirect('client_dashboard')
            else:
                return redirect('dashboard_transporteur')
    else:
        form = InscriptionForm()
    
    return render(request, 'registration/inscription.html', {'form': form})


@require_http_methods(["GET", "POST"])
def logout_view(request):
    """Déconnexion de l'utilisateur"""
    logout(request)
    messages.info(request, "Vous avez été déconnecté avec succès.")
    return redirect('index')


# ===========================
# VUES CLIENT
# ===========================

@login_required
def client_dashboard(request):
    """Dashboard principal du client"""
    try:
        client = request.user.client
    except Client.DoesNotExist:
        messages.error(request, "Veuillez compléter votre profil client.")
        return redirect('index')
    
    # Statistiques du client
    commandes_total = Commande.objects.filter(client=client).count()
    commandes_livrees = Commande.objects.filter(client=client, statut='LIVREE').count()
    commandes_en_cours = Commande.objects.filter(
        client=client, 
        statut__in=['EN_ATTENTE', 'AFFECTEE', 'EN_TRANSIT']
    ).count()
    commandes_annulees = Commande.objects.filter(client=client, statut='ANNULEE').count()
    
    # Calcul du taux de satisfaction (basé sur les livraisons réussies)
    taux_satisfaction = 0
    if commandes_total > 0:
        taux_satisfaction = round((commandes_livrees / commandes_total) * 100, 1)
    
    # Commandes récentes
    commandes_recentes = Commande.objects.filter(client=client).order_by('-date_creation')[:5]
    
    # Notifications non lues
    notifications = Notification.objects.filter(
        destinataire=request.user, 
        lu=False
    ).order_by('-date_creation')[:5]
    
    # Dépenses totales (simulation)
    depenses_mois = commandes_livrees * 150  # Prix moyen par livraison
    
    context = {
        'client': client,
        'commandes_total': commandes_total,
        'commandes_livrees': commandes_livrees,
        'commandes_en_cours': commandes_en_cours,
        'commandes_annulees': commandes_annulees,
        'commandes_recentes': commandes_recentes,
        'notifications': notifications,
        'taux_satisfaction': taux_satisfaction,
        'depenses_mois': depenses_mois,
    }
    
    return render(request, 'transport/client_dashboard.html', context)


@login_required
def liste_commandes(request):
    """Liste des commandes - Admin voit tout, client voit les siennes"""
    if request.user.is_staff:
        # Admin voit toutes les commandes
        commandes = Commande.objects.all().select_related(
            'client', 'transporteur', 'adresse_enlevement', 'adresse_livraison'
        ).order_by('-date_creation')
        is_admin = True
    else:
        # Client voit seulement ses commandes
        try:
            client = request.user.client
            commandes = Commande.objects.filter(client=client).select_related(
                'transporteur', 'adresse_enlevement', 'adresse_livraison'
            ).order_by('-date_creation')
            is_admin = False
        except Client.DoesNotExist:
            messages.error(request, "Veuillez compléter votre profil client.")
            return redirect('index')
    
    # Filtres (si fournis dans la requête)
    statut_filter = request.GET.get('statut')
    date_filter = request.GET.get('date')
    
    if statut_filter:
        commandes = commandes.filter(statut=statut_filter)
    
    if date_filter:
        try:
            date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
            commandes = commandes.filter(date_creation__date=date_obj)
        except ValueError:
            pass
    
    context = {
        'commandes': commandes,
        'is_admin': is_admin,
        'statut_filter': statut_filter,
        'date_filter': date_filter,
    }
    
    return render(request, 'transport/liste_commandes.html', context)


@login_required
def creer_commande(request):
    """Création d'une nouvelle commande par un client"""
    # Vérifier que c'est bien un client
    if request.user.is_staff and not hasattr(request.user, 'client'):
        messages.warning(request, "Les administrateurs doivent utiliser un compte client pour créer des commandes.")
        return redirect('index')
    
    try:
        client = request.user.client
    except Client.DoesNotExist:
        messages.error(request, "Veuillez compléter votre profil client.")
        return redirect('index')
    
    if request.method == 'POST':
        commande_form = CommandeForm(request.POST)
        adresse_enlevement_form = AdresseForm(request.POST, prefix='enlevement')
        adresse_livraison_form = AdresseForm(request.POST, prefix='livraison')
        
        if (commande_form.is_valid() and 
            adresse_enlevement_form.is_valid() and 
            adresse_livraison_form.is_valid()):
            
            # Créer les adresses
            adr_enlev = adresse_enlevement_form.save()
            adr_livr = adresse_livraison_form.save()
            
            # Géocoder les adresses (si API disponible)
            try:
                from .api_integrations import geocode_service
                coords_enlev = geocode_service.geocode_address(adr_enlev)
                coords_livr = geocode_service.geocode_address(adr_livr)
                
                adr_enlev.latitude = coords_enlev.get('lat')
                adr_enlev.longitude = coords_enlev.get('lng')
                adr_enlev.save()
                
                adr_livr.latitude = coords_livr.get('lat')
                adr_livr.longitude = coords_livr.get('lng')
                adr_livr.save()
            except:
                pass  # Si géocodage échoue, continuer sans coordonnées
            
            # Créer la commande
            commande = commande_form.save(commit=False)
            commande.client = client
            commande.adresse_enlevement = adr_enlev
            commande.adresse_livraison = adr_livr
            commande.save()
            
            # Notifier les planificateurs
            for user in User.objects.filter(is_staff=True):
                Notification.objects.create(
                    destinataire=user,
                    type='MISSION',
                    titre='Nouvelle commande à affecter',
                    message=f'Commande #{commande.id} - {commande.type_marchandise} ({commande.poids}kg)',
                    commande=commande,
                    priorite='HAUTE' if commande.priorite == 2 else 'NORMALE'
                )
            
            messages.success(request, f"Commande #{commande.id} créée avec succès!")
            return redirect('suivre_commande', commande_id=commande.id)
    else:
        commande_form = CommandeForm()
        adresse_enlevement_form = AdresseForm(prefix='enlevement')
        adresse_livraison_form = AdresseForm(prefix='livraison')
    
    return render(request, 'transport/creer_commande.html', {
        'commande_form': commande_form,
        'adresse_enlevement_form': adresse_enlevement_form,
        'adresse_livraison_form': adresse_livraison_form
    })


@login_required
def suivre_commande(request, commande_id):
    """Suivi détaillé d'une commande avec carte"""
    # Vérifier les permissions
    if request.user.is_staff:
        commande = get_object_or_404(
            Commande.objects.select_related(
                'client', 'transporteur', 'adresse_enlevement', 'adresse_livraison'
            ), 
            id=commande_id
        )
    else:
        try:
            client = request.user.client
            commande = get_object_or_404(
                Commande.objects.select_related(
                    'transporteur', 'adresse_enlevement', 'adresse_livraison'
                ), 
                id=commande_id, 
                client=client
            )
        except Client.DoesNotExist:
            messages.error(request, "Accès refusé.")
            return redirect('index')
    
    # Récupérer la mission associée
    mission = None
    itineraire = None
    if commande.transporteur:
        try:
            mission = MissionTransporteur.objects.get(commande=commande)
            itineraire = mission.itineraire_optimise
        except MissionTransporteur.DoesNotExist:
            pass
    
    # Préparer les données pour la carte
    map_data = {
        'enlev_lat': commande.adresse_enlevement.latitude or 33.5731,
        'enlev_lng': commande.adresse_enlevement.longitude or -7.5898,
        'livr_lat': commande.adresse_livraison.latitude or 33.5731,
        'livr_lng': commande.adresse_livraison.longitude or -7.5898,
    }
    
    # Position actuelle du transporteur (si disponible)
    if commande.transporteur:
        map_data['transp_lat'] = commande.transporteur.latitude_actuelle
        map_data['transp_lng'] = commande.transporteur.longitude_actuelle
    
    context = {
        'commande': commande,
        'mission': mission,
        'itineraire': itineraire,
        'map_data': json.dumps(map_data),
    }
    
    return render(request, 'transport/suivre_commande.html', context)


@login_required
def supprimer_commande(request, commande_id):
    """Annulation d'une commande"""
    # Vérifier les permissions
    if request.user.is_staff:
        commande = get_object_or_404(Commande, id=commande_id)
    else:
        try:
            client = request.user.client
            commande = get_object_or_404(Commande, id=commande_id, client=client)
        except Client.DoesNotExist:
            messages.error(request, "Accès refusé.")
            return redirect('index')
    
    # Vérifier que l'annulation est possible
    delai_h = 24  # Délai par défaut
    try:
        param = ParametreSysteme.objects.get(nom='delai_annulation')
        delai_h = int(param.valeur)
    except:
        pass
    
    # Empêcher l'annulation si déjà en transit ou livrée
    if commande.statut in ['EN_TRANSIT', 'LIVREE']:
        messages.error(request, "Cette commande ne peut plus être annulée.")
        return redirect('liste_commandes')
    
    # Vérifier le délai d'annulation
    if commande.date_creation < timezone.now() - timedelta(hours=delai_h):
        messages.error(request, f"Délai d'annulation dépassé ({delai_h}h).")
        return redirect('liste_commandes')
    
    if request.method == 'POST':
        # Annuler la commande
        commande.statut = 'ANNULEE'
        commande.save()
        
        # Annuler la mission associée
        try:
            mission = MissionTransporteur.objects.get(commande=commande)
            mission.statut = 'ANNULEE'
            mission.save()
            
            # Notifier le transporteur
            Notification.objects.create(
                destinataire=mission.transporteur.user,
                type='STATUT',
                titre='Mission annulée',
                message=f'La commande #{commande.id} a été annulée.',
                commande=commande,
                priorite='HAUTE'
            )
        except MissionTransporteur.DoesNotExist:
            pass
        
        messages.success(request, f"Commande #{commande.id} annulée avec succès.")
        return redirect('liste_commandes')
    
    return render(request, 'transport/supprimer_commande.html', {'commande': commande})


@login_required
def generer_rapport(request):
    """Génération de rapport de commandes"""
    # Déterminer le profil
    is_admin = request.user.is_staff
    client = None
    
    if not is_admin:
        try:
            client = request.user.client
        except Client.DoesNotExist:
            messages.error(request, "Profil client requis pour générer un rapport.")
            return redirect('index')
    
    if request.method == 'POST':
        form = RapportForm(request.POST)
        if form.is_valid():
            date_debut = form.cleaned_data['date_debut']
            date_fin = form.cleaned_data['date_fin']
            format_export = form.cleaned_data['format_export']
            
            # Filtrer les commandes
            if is_admin:
                commandes = Commande.objects.filter(
                    date_creation__date__gte=date_debut,
                    date_creation__date__lte=date_fin
                ).select_related(
                    'client', 'transporteur', 'adresse_enlevement', 'adresse_livraison'
                ).order_by('-date_creation')
            else:
                commandes = Commande.objects.filter(
                    client=client,
                    date_creation__date__gte=date_debut,
                    date_creation__date__lte=date_fin
                ).select_related(
                    'transporteur', 'adresse_enlevement', 'adresse_livraison'
                ).order_by('-date_creation')
            
            if format_export == 'csv':
                # Export CSV
                response = HttpResponse(content_type='text/csv; charset=utf-8')
                filename = f'rapport_commandes_{date_debut}_{date_fin}.csv'
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                
                # BOM pour Excel
                response.write('\ufeff'.encode('utf8'))
                
                writer = csv.writer(response)
                # En-têtes
                headers = ['N° Commande', 'Date', 'Type Marchandise', 'Poids (kg)', 
                          'Ville Enlèvement', 'Ville Livraison', 'Statut']
                if is_admin:
                    headers.insert(1, 'Client')
                
                writer.writerow(headers)
                
                # Données
                for commande in commandes:
                    row = [
                        commande.id,
                        commande.date_creation.strftime('%d/%m/%Y %H:%M'),
                        commande.type_marchandise,
                        commande.poids,
                        commande.adresse_enlevement.ville,
                        commande.adresse_livraison.ville,
                        commande.get_statut_display()
                    ]
                    if is_admin:
                        row.insert(1, commande.client.user.username)
                    
                    writer.writerow(row)
                
                return response
            else:
                # Affichage HTML/PDF
                # Calculer les statistiques
                stats = {
                    'total_commandes': commandes.count(),
                    'commandes_livrees': commandes.filter(statut='LIVREE').count(),
                    'commandes_en_cours': commandes.filter(
                        statut__in=['EN_ATTENTE', 'AFFECTEE', 'EN_TRANSIT']
                    ).count(),
                    'commandes_annulees': commandes.filter(statut='ANNULEE').count(),
                }
                
                # Statistiques supplémentaires
                poids_total = commandes.aggregate(Sum('poids'))['poids__sum'] or 0
                
                # Taux de livraison
                taux_livraison = 0
                if stats['total_commandes'] > 0:
                    taux_livraison = round(
                        (stats['commandes_livrees'] / stats['total_commandes']) * 100, 1
                    )
                
                context = {
                    'commandes': commandes,
                    'date_debut': date_debut,
                    'date_fin': date_fin,
                    'client': client,
                    'is_admin': is_admin,
                    'stats': stats,
                    'poids_total': poids_total,
                    'taux_livraison': taux_livraison,
                }
                
                return render(request, 'transport/rapport_pdf.html', context)
    else:
        # Proposer des dates par défaut (dernier mois)
        date_fin = timezone.now().date()
        date_debut = date_fin - timedelta(days=30)
        
        form = RapportForm(initial={
            'date_debut': date_debut,
            'date_fin': date_fin,
        })
    
    return render(request, 'transport/generer_rapport.html', {
        'form': form,
        'is_admin': is_admin
    })


@login_required
def messagerie_support(request):
    """Interface de messagerie support"""
    # Les admins utilisent une interface différente
    if request.user.is_staff:
        return redirect('support_clients')
    
    # Récupérer l'historique de conversation
    messages_chain = SupportMessage.objects.filter(
        Q(sender=request.user, destinataire__is_staff=True) | 
        Q(sender__is_staff=True, destinataire=request.user)
    ).order_by('date_envoi')
    
    # Marquer comme lus
    SupportMessage.objects.filter(
        sender__is_staff=True, 
        destinataire=request.user, 
        lu=False
    ).update(lu=True)
    
    if request.method == 'POST':
        contenu = request.POST.get('contenu', '').strip()
        if contenu:
            # Trouver un admin disponible
            admin_user = User.objects.filter(is_staff=True).first()
            if admin_user:
                # Créer le message
                SupportMessage.objects.create(
                    sender=request.user, 
                    destinataire=admin_user, 
                    contenu=contenu
                )
                
                # Notifier l'admin
                Notification.objects.create(
                    destinataire=admin_user,
                    type='SYSTEME',
                    titre='Nouveau message support',
                    message=f'Message de {request.user.username}',
                    priorite='NORMALE'
                )
                
                messages.success(request, "Message envoyé au support.")
            else:
                messages.error(request, "Aucun administrateur disponible.")
            
            return redirect('messagerie_support')
    
    # Informations de contact
    contact_info = {
        'email': ParametreSysteme.objects.filter(nom='email_contact').first(),
        'telephone': '+212 600 000 000',  # À récupérer depuis les paramètres
        'horaires': 'Lundi - Vendredi: 8h00 - 18h00',
    }
    
    return render(request, 'transport/messagerie_support.html', {
        'messages': messages_chain,
        'contact_info': contact_info,
    })


# ===========================
# VUES API/AJAX
# ===========================

@login_required
def api_notifications_count(request):
    """API pour obtenir le nombre de notifications non lues"""
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
            notification.lu = True
            notification.save()
            return JsonResponse({'success': True})
        except Notification.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Notification non trouvée'})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})


# ===========================
# FONCTIONS UTILITAIRES
# ===========================

def calculer_prix_estimation(poids, distance, type_marchandise):
    """Calculer une estimation de prix pour une commande"""
    # Prix de base
    prix_base = 50
    
    # Prix par kg
    prix_kg = 2
    
    # Prix par km
    prix_km = 1.5
    
    # Multiplicateurs selon le type
    multiplicateurs = {
        'standard': 1.0,
        'fragile': 1.3,
        'perissable': 1.5,
        'dangereux': 2.0,
    }
    
    multiplicateur = multiplicateurs.get(type_marchandise.lower(), 1.0)
    
    prix_total = (prix_base + (poids * prix_kg) + (distance * prix_km)) * multiplicateur
    
    return round(prix_total, 2)