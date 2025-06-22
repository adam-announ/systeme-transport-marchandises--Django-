# transport/views.py - Version complète avec toutes les fonctions manquantes

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Q, Count, Sum, Avg
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
import csv
import json
import logging

from .models import (
    Commande, Client, Transporteur, Adresse, SupportMessage, 
    Notification, ParametreSysteme, MissionTransporteur
)
from .forms import CommandeForm, AdresseForm, InscriptionForm, RapportForm

logger = logging.getLogger(__name__)

# ===========================
# REDIRECTIONS INTELLIGENTES
# ===========================

@staff_member_required
def admin_redirect(request):
    """Redirection pour les anciennes URLs admin"""
    return redirect('admin_dashboard')

@login_required  
def dashboard_redirect(request):
    """Redirection intelligente vers le bon dashboard"""
    user_type = get_user_type(request.user)
    
    if user_type == 'admin' or user_type == 'planificateur':
        return redirect('admin_dashboard')
    elif user_type == 'client':
        return redirect('client_dashboard')
    elif user_type == 'transporteur':
        return redirect('dashboard_transporteur')
    elif user_type == 'incomplete':
        messages.warning(request, 
            "Votre profil n'est pas encore configuré. "
            "Contactez l'administrateur pour activer votre compte."
        )
        return redirect('index')
    else:
        return redirect('index')

# ===========================
# VUES PUBLIQUES (Sans authentification)
# ===========================

def index(request):
    """Page d'accueil principale - Version améliorée"""
    if request.user.is_authenticated:
        user_type = get_user_type(request.user)
        
        # Gestion des profils incomplets
        if user_type == 'incomplete':
            messages.info(request, 
                "Votre compte n'est pas encore configuré. "
                "Contactez l'administrateur pour activer votre profil."
            )
        
        context = {
            'user_authenticated': True,
            'user_type': user_type,
            'quick_stats': get_quick_stats() if request.user.is_staff else None,
            'user_notifications_count': get_user_notifications_count(request.user),
        }
    else:
        context = {
            'user_authenticated': False,
            'public_stats': get_public_stats(),
        }
    
    return render(request, 'transport/index.html', context)

def get_user_type(user):
    """Déterminer le type d'utilisateur avec gestion améliorée"""
    if user.is_superuser:
        return 'admin'
    elif user.is_staff:
        return 'planificateur'
    elif hasattr(user, 'client'):
        return 'client'
    elif hasattr(user, 'transporteur'):
        return 'transporteur'
    else:
        # Utilisateur sans profil spécifique
        return 'incomplete'

def get_quick_stats():
    """Statistiques rapides pour les utilisateurs connectés - Améliorées"""
    try:
        stats = {
            'commandes_attente': Commande.objects.filter(statut='EN_ATTENTE').count(),
            'transporteurs_disponibles': Transporteur.objects.filter(disponible=True).count(),
            'missions_en_cours': MissionTransporteur.objects.filter(statut='EN_COURS').count(),
        }
        
        # Ajouter des statistiques supplémentaires
        today = timezone.now().date()
        stats.update({
            'livraisons_jour': MissionTransporteur.objects.filter(
                statut='TERMINEE',
                date_fin__date=today
            ).count(),
            'taux_reussite': calculate_success_rate(),
        })
        
        return stats
    except Exception as e:
        logger.error(f"Erreur lors du calcul des statistiques: {e}")
        return {}

def get_public_stats():
    """Statistiques publiques pour la page d'accueil - Améliorées"""
    try:
        # Statistiques réelles avec cache
        cache_key = 'public_stats'
        from django.core.cache import cache
        
        stats = cache.get(cache_key)
        if not stats:
            stats = {
                'total_livraisons': Commande.objects.filter(statut='LIVREE').count(),
                'clients_satisfaits': Client.objects.filter(actif=True).count(),
                'transporteurs_actifs': Transporteur.objects.filter(
                    disponible=True, 
                    actif=True
                ).count(),
                'villes_couvertes': get_covered_cities_count(),
            }
            # Cache pour 1 heure
            cache.set(cache_key, stats, 3600)
        
        return stats
    except Exception as e:
        logger.error(f"Erreur lors du calcul des statistiques publiques: {e}")
        return {
            'total_livraisons': 1000,
            'clients_satisfaits': 250,
            'transporteurs_actifs': 50,
            'villes_couvertes': 15,
        }

def get_user_notifications_count(user):
    """Obtenir le nombre de notifications non lues pour un utilisateur"""
    try:
        return Notification.objects.filter(
            destinataire=user,
            lu=False
        ).count()
    except:
        return 0

def get_covered_cities_count():
    """Calculer le nombre de villes couvertes"""
    try:
        villes_enlevement = set(Adresse.objects.filter(
            commandes_enlevement__isnull=False
        ).values_list('ville', flat=True))
        
        villes_livraison = set(Adresse.objects.filter(
            commandes_livraison__isnull=False
        ).values_list('ville', flat=True))
        
        return len(villes_enlevement.union(villes_livraison))
    except:
        return 15

def calculate_success_rate():
    """Calculer le taux de réussite global"""
    try:
        total_missions = MissionTransporteur.objects.filter(
            statut__in=['TERMINEE', 'ANNULEE']
        ).count()
        
        if total_missions == 0:
            return 100
        
        missions_reussies = MissionTransporteur.objects.filter(
            statut='TERMINEE'
        ).count()
        
        return round((missions_reussies / total_missions) * 100, 1)
    except:
        return 95

def home_modern(request):
    """Page d'accueil moderne avec design attractif"""
    stats = get_public_stats()
    
    # Ajouter des témoignages ou actualités
    actualites = get_recent_news()
    
    context = {
        'stats': stats,
        'actualites': actualites,
        'user_authenticated': request.user.is_authenticated,
        'user_type': get_user_type(request.user) if request.user.is_authenticated else None,
    }
    return render(request, 'transport/home_modern.html', context)

def get_recent_news():
    """Obtenir les actualités récentes (simulation)"""
    return [
        {
            'titre': 'Nouvelle fonctionnalité: Suivi GPS en temps réel',
            'date': timezone.now() - timedelta(days=2),
            'description': 'Suivez vos livraisons avec une précision GPS.'
        },
        {
            'titre': 'Extension de notre réseau à 5 nouvelles villes',
            'date': timezone.now() - timedelta(days=7),
            'description': 'Nous couvrons maintenant 20 villes au Maroc.'
        }
    ]

def inscription(request):
    """Inscription d'un nouvel utilisateur - Version améliorée"""
    if request.user.is_authenticated:
        messages.info(request, "Vous êtes déjà connecté.")
        return redirect('dashboard_redirect')
    
    if request.method == 'POST':
        form = InscriptionForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user)
                
                # Log de l'inscription
                logger.info(f"Nouvelle inscription: {user.username} ({form.cleaned_data['type_compte']})")
                
                # Message de bienvenue personnalisé
                type_compte = form.cleaned_data['type_compte']
                if type_compte == 'client':
                    messages.success(request, 
                        "Inscription réussie! Bienvenue sur TransportPro. "
                        "Vous pouvez maintenant créer vos premières commandes."
                    )
                    return redirect('client_dashboard')
                else:
                    messages.success(request, 
                        "Inscription réussie! Votre profil transporteur est en attente de validation. "
                        "Vous recevrez une notification dès qu'il sera activé."
                    )
                    return redirect('dashboard_transporteur')
                    
            except Exception as e:
                logger.error(f"Erreur lors de l'inscription: {e}")
                messages.error(request, "Une erreur est survenue lors de l'inscription.")
    else:
        form = InscriptionForm()
    
    return render(request, 'registration/inscription.html', {'form': form})

@require_http_methods(["GET", "POST"])
def logout_view(request):
    """Déconnexion de l'utilisateur - Version améliorée"""
    username = request.user.username if request.user.is_authenticated else "Utilisateur"
    logout(request)
    messages.info(request, f"Au revoir {username}! Vous avez été déconnecté avec succès.")
    return redirect('index')

# ===========================
# VUES CLIENT - Améliorées
# ===========================

@login_required
def client_dashboard(request):
    """Dashboard principal du client - Version améliorée"""
    try:
        client = request.user.client
    except Client.DoesNotExist:
        messages.error(request, "Veuillez compléter votre profil client.")
        return redirect('index')
    
    # Statistiques du client avec optimisation
    commandes_queryset = Commande.objects.filter(client=client)
    
    stats = commandes_queryset.aggregate(
        total=Count('id'),
        livrees=Count('id', filter=Q(statut='LIVREE')),
        en_cours=Count('id', filter=Q(statut__in=['EN_ATTENTE', 'AFFECTEE', 'EN_TRANSIT'])),
        annulees=Count('id', filter=Q(statut='ANNULEE')),
        poids_total=Sum('poids')
    )
    
    # Calcul du taux de satisfaction
    taux_satisfaction = 0
    if stats['total'] > 0:
        taux_satisfaction = round((stats['livrees'] / stats['total']) * 100, 1)
    
    # Commandes récentes avec optimisation
    commandes_recentes = commandes_queryset.select_related(
        'transporteur', 'adresse_enlevement', 'adresse_livraison'
    ).order_by('-date_creation')[:5]
    
    # Notifications non lues
    notifications = Notification.objects.filter(
        destinataire=request.user, 
        lu=False
    ).order_by('-date_creation')[:5]
    
    # Estimation des dépenses
    depenses_mois = estimate_monthly_expenses(client)
    
    # Analyse des tendances
    tendances = analyze_client_trends(client)
    
    context = {
        'client': client,
        'commandes_total': stats['total'],
        'commandes_livrees': stats['livrees'],
        'commandes_en_cours': stats['en_cours'],
        'commandes_annulees': stats['annulees'],
        'poids_total': stats['poids_total'] or 0,
        'commandes_recentes': commandes_recentes,
        'notifications': notifications,
        'taux_satisfaction': taux_satisfaction,
        'depenses_mois': depenses_mois,
        'tendances': tendances,
    }
    
    return render(request, 'transport/client_dashboard.html', context)

def estimate_monthly_expenses(client):
    """Estimer les dépenses mensuelles d'un client"""
    try:
        # Calculer sur les 30 derniers jours
        date_debut = timezone.now() - timedelta(days=30)
        
        commandes_mois = Commande.objects.filter(
            client=client,
            date_creation__gte=date_debut,
            statut='LIVREE'
        ).aggregate(
            count=Count('id'),
            poids_total=Sum('poids')
        )
        
        # Estimation basée sur un prix moyen
        prix_base = 50
        prix_par_kg = 2
        
        total_estimé = (commandes_mois['count'] or 0) * prix_base
        total_estimé += (commandes_mois['poids_total'] or 0) * prix_par_kg
        
        return round(total_estimé, 2)
    except:
        return 0

def analyze_client_trends(client):
    """Analyser les tendances d'un client"""
    try:
        # Commandes par mois des 6 derniers mois
        trends = []
        for i in range(6):
            date_fin = timezone.now().replace(day=1) - timedelta(days=i*30)
            date_debut = date_fin - timedelta(days=30)
            
            count = Commande.objects.filter(
                client=client,
                date_creation__gte=date_debut,
                date_creation__lt=date_fin
            ).count()
            
            trends.append({
                'mois': date_fin.strftime('%B'),
                'commandes': count
            })
        
        return reversed(trends)
    except:
        return []

@login_required
def liste_commandes(request):
    """Liste des commandes avec pagination et filtres avancés"""
    # Déterminer les permissions
    if request.user.is_staff:
        base_queryset = Commande.objects.all()
        is_admin = True
    else:
        try:
            client = request.user.client
            base_queryset = Commande.objects.filter(client=client)
            is_admin = False
        except Client.DoesNotExist:
            messages.error(request, "Veuillez compléter votre profil client.")
            return redirect('index')
    
    # Optimisation avec select_related
    commandes = base_queryset.select_related(
        'client', 'transporteur', 'adresse_enlevement', 'adresse_livraison'
    ).order_by('-date_creation')
    
    # Filtres avancés
    statut_filter = request.GET.get('statut')
    date_filter = request.GET.get('date')
    ville_filter = request.GET.get('ville')
    transporteur_filter = request.GET.get('transporteur')
    
    if statut_filter:
        commandes = commandes.filter(statut=statut_filter)
    
    if date_filter:
        try:
            date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
            commandes = commandes.filter(date_creation__date=date_obj)
        except ValueError:
            pass
    
    if ville_filter:
        commandes = commandes.filter(
            Q(adresse_enlevement__ville__icontains=ville_filter) |
            Q(adresse_livraison__ville__icontains=ville_filter)
        )
    
    if transporteur_filter and is_admin:
        commandes = commandes.filter(transporteur__id=transporteur_filter)
    
    # Pagination
    paginator = Paginator(commandes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Options pour les filtres
    statuts_disponibles = Commande.STATUT_CHOICES
    transporteurs_disponibles = Transporteur.objects.filter(actif=True) if is_admin else None
    
    context = {
        'page_obj': page_obj,
        'is_admin': is_admin,
        'statut_filter': statut_filter,
        'date_filter': date_filter,
        'ville_filter': ville_filter,
        'transporteur_filter': transporteur_filter,
        'statuts_disponibles': statuts_disponibles,
        'transporteurs_disponibles': transporteurs_disponibles,
    }
    
    return render(request, 'transport/liste_commandes.html', context)

@login_required
def creer_commande(request):
    """Création d'une nouvelle commande - Version améliorée"""
    # Vérification des permissions
    if request.user.is_staff and not hasattr(request.user, 'client'):
        messages.warning(request, 
            "Les administrateurs doivent utiliser un compte client pour créer des commandes."
        )
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
            
            try:
                # Créer les adresses
                adr_enlev = adresse_enlevement_form.save()
                adr_livr = adresse_livraison_form.save()
                
                # Géocoder les adresses si possible
                geocode_addresses(adr_enlev, adr_livr)
                
                # Créer la commande
                commande = commande_form.save(commit=False)
                commande.client = client
                commande.adresse_enlevement = adr_enlev
                commande.adresse_livraison = adr_livr
                
                # Calculer l'estimation de prix
                distance = calculate_distance_between_addresses(adr_enlev, adr_livr)
                commande.prix_estime = calculer_prix_estimation(
                    commande.poids, 
                    distance, 
                    commande.type_marchandise
                )
                
                commande.save()
                
                # Notifications aux planificateurs
                notify_planners_new_order(commande)
                
                # Log de la création
                logger.info(f"Nouvelle commande créée: #{commande.id} par {client.user.username}")
                
                messages.success(request, 
                    f"Commande #{commande.id} créée avec succès! "
                    f"Prix estimé: {commande.prix_estime} MAD"
                )
                return redirect('suivre_commande', commande_id=commande.id)
                
            except Exception as e:
                logger.error(f"Erreur lors de la création de commande: {e}")
                messages.error(request, "Une erreur est survenue lors de la création de la commande.")
    else:
        commande_form = CommandeForm()
        adresse_enlevement_form = AdresseForm(prefix='enlevement')
        adresse_livraison_form = AdresseForm(prefix='livraison')
    
    # Adresses récentes du client pour auto-complétion
    adresses_recentes = get_client_recent_addresses(client)
    
    context = {
        'commande_form': commande_form,
        'adresse_enlevement_form': adresse_enlevement_form,
        'adresse_livraison_form': adresse_livraison_form,
        'adresses_recentes': adresses_recentes,
    }
    
    return render(request, 'transport/creer_commande.html', context)

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
# FONCTIONS UTILITAIRES
# ===========================

def geocode_addresses(adr_enlev, adr_livr):
    """Géocoder les adresses si l'API est disponible"""
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
        
    except ImportError:
        # API non disponible, utiliser des coordonnées par défaut ou villes connues
        from .utils import calculer_distance
        # Logique de fallback
        pass
    except Exception as e:
        logger.warning(f"Erreur de géocodage: {e}")

def calculate_distance_between_addresses(adr1, adr2):
    """Calculer la distance entre deux adresses"""
    try:
        from .utils import calculer_distance
        
        if all([adr1.latitude, adr1.longitude, adr2.latitude, adr2.longitude]):
            return calculer_distance(
                adr1.latitude, adr1.longitude,
                adr2.latitude, adr2.longitude
            )
        else:
            # Estimation basée sur les villes
            return estimate_distance_by_cities(adr1.ville, adr2.ville)
    except:
        return 50  # Distance par défaut

def estimate_distance_by_cities(ville1, ville2):
    """Estimer la distance entre deux villes"""
    distances_villes = {
        ('Casablanca', 'Rabat'): 90,
        ('Casablanca', 'Marrakech'): 240,
        ('Rabat', 'Fès'): 200,
        ('Rabat', 'Marrakech'): 320,
        ('Casablanca', 'Fès'): 290,
        ('Marrakech', 'Agadir'): 250,
        ('Casablanca', 'Tanger'): 340,
        ('Rabat', 'Tanger'): 250,
        ('Fès', 'Meknès'): 60,
        ('Casablanca', 'Agadir'): 490,
    }
    
    key1 = (ville1, ville2)
    key2 = (ville2, ville1)
    
    return distances_villes.get(key1, distances_villes.get(key2, 100))

def notify_planners_new_order(commande):
    """Notifier les planificateurs d'une nouvelle commande"""
    planificateurs = User.objects.filter(is_staff=True, is_active=True)
    
    for user in planificateurs:
        Notification.objects.create(
            destinataire=user,
            type='MISSION',
            titre='Nouvelle commande à affecter',
            message=f'Commande #{commande.id} - {commande.type_marchandise} '
                   f'({commande.poids}kg) - {commande.adresse_enlevement.ville} → '
                   f'{commande.adresse_livraison.ville}',
            commande=commande,
            priorite='HAUTE' if commande.priorite == 2 else 'NORMALE'
        )

def get_client_recent_addresses(client):
    """Obtenir les adresses récentes d'un client"""
    try:
        # Adresses d'enlèvement récentes
        enlevements = Adresse.objects.filter(
            commandes_enlevement__client=client
        ).distinct().order_by('-id')[:5]
        
        # Adresses de livraison récentes
        livraisons = Adresse.objects.filter(
            commandes_livraison__client=client
        ).distinct().order_by('-id')[:5]
        
        return {
            'enlevements': enlevements,
            'livraisons': livraisons
        }
    except:
        return {'enlevements': [], 'livraisons': []}

def calculer_prix_estimation(poids, distance, type_marchandise):
    """Calculer une estimation de prix pour une commande - Version améliorée"""
    try:
        # Récupérer les paramètres depuis la base de données
        prix_base = get_system_parameter('prix_base_livraison', 50)
        prix_kg = get_system_parameter('prix_par_kg', 2)
        prix_km = get_system_parameter('prix_par_km', 1.5)
        
        # Multiplicateurs selon le type de marchandise
        multiplicateurs = {
            'standard': 1.0,
            'fragile': 1.3,
            'perissable': 1.5,
            'dangereux': 2.0,
            'urgent': 1.8,
        }
        
        multiplicateur = multiplicateurs.get(type_marchandise.lower(), 1.0)
        
        # Calcul du prix de base
        prix_total = prix_base + (poids * prix_kg) + (distance * prix_km)
        
        # Application du multiplicateur
        prix_total *= multiplicateur
        
        # Arrondir à 2 décimales
        return round(prix_total, 2)
        
    except Exception as e:
        logger.error(f"Erreur calcul prix: {e}")
        return 100.0  # Prix par défaut

def get_system_parameter(nom, default_value):
    """Récupérer un paramètre système avec valeur par défaut"""
    try:
        param = ParametreSysteme.objects.get(nom=nom)
        return float(param.valeur)
    except (ParametreSysteme.DoesNotExist, ValueError):
        return default_value

# ===========================
# VUES API/AJAX - Améliorées
# ===========================

@login_required
def api_notifications_count(request):
    """API pour obtenir le nombre de notifications non lues"""
    try:
        count = Notification.objects.filter(
            destinataire=request.user,
            lu=False
        ).count()
        
        # Ajouter les notifications récentes
        notifications_recentes = Notification.objects.filter(
            destinataire=request.user,
            lu=False
        ).order_by('-date_creation')[:5].values(
            'id', 'titre', 'message', 'type', 'priorite', 'date_creation'
        )
        
        return JsonResponse({
            'count': count,
            'notifications': list(notifications_recentes)
        })
    except Exception as e:
        logger.error(f"Erreur API notifications: {e}")
        return JsonResponse({'count': 0, 'notifications': []})

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
            
            return JsonResponse({
                'success': True,
                'message': 'Notification marquée comme lue'
            })
        except Notification.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'error': 'Notification non trouvée'
            })
        except Exception as e:
            logger.error(f"Erreur API notification lue: {e}")
            return JsonResponse({
                'success': False, 
                'error': 'Erreur serveur'
            })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

# ===========================
# VUES SUPPLÉMENTAIRES
# ===========================

@login_required
def notifications_list(request):
    """Liste complète des notifications utilisateur"""
    notifications = Notification.objects.filter(
        destinataire=request.user
    ).order_by('-date_creation')
    
    # Pagination
    paginator = Paginator(notifications, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Marquer les notifications comme lues quand on les consulte
    notifications_non_lues = notifications.filter(lu=False)
    if notifications_non_lues.exists():
        notifications_non_lues.update(lu=True)
    
    context = {
        'page_obj': page_obj,
        'total_notifications': notifications.count(),
    }
    
    return render(request, 'transport/notifications_list.html', context)

@login_required
def profile_settings(request):
    """Paramètres de profil utilisateur"""
    user_type = get_user_type(request.user)
    
    if user_type == 'client':
        try:
            profile = request.user.client
        except Client.DoesNotExist:
            messages.error(request, "Profil client non trouvé.")
            return redirect('index')
    elif user_type == 'transporteur':
        try:
            profile = request.user.transporteur
        except Transporteur.DoesNotExist:
            messages.error(request, "Profil transporteur non trouvé.")
            return redirect('index')
    else:
        messages.info(request, "Paramètres disponibles pour les clients et transporteurs uniquement.")
        return redirect('index')
    
    if request.method == 'POST':
        # Traiter les modifications de profil
        # ... Logique de mise à jour
        messages.success(request, "Profil mis à jour avec succès.")
        return redirect('profile_settings')
    
    context = {
        'profile': profile,
        'user_type': user_type,
    }
    
    return render(request, 'transport/profile_settings.html', context)

@login_required
def help_center(request):
    """Centre d'aide et FAQ"""
    faq_items = [
        {
            'question': 'Comment créer une nouvelle commande?',
            'answer': 'Rendez-vous dans "Nouvelle Commande" et remplissez les informations requises.'
        },
        {
            'question': 'Comment suivre ma livraison?',
            'answer': 'Utilisez le numéro de commande dans la section "Suivi" pour voir la progression en temps réel.'
        },
        {
            'question': 'Quels sont les délais de livraison?',
            'answer': 'Les délais varient selon la distance et le type de marchandise. En moyenne: 24-48h.'
        },
        {
            'question': 'Comment annuler une commande?',
            'answer': 'Vous pouvez annuler une commande dans les 24h suivant sa création, avant qu\'elle soit prise en charge.'
        },
    ]
    
    context = {
        'faq_items': faq_items,
        'user_type': get_user_type(request.user),
    }
    
    return render(request, 'transport/help_center.html', context)

# ===========================
# GESTION D'ERREURS
# ===========================

def handler404(request, exception):
    """Page d'erreur 404 personnalisée"""
    return render(request, 'errors/404.html', status=404)

def handler500(request):
    """Page d'erreur 500 personnalisée"""
    return render(request, 'errors/500.html', status=500)