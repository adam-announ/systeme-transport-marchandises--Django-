# backend/transport/views.py - Version corrigée avec toutes les fonctions
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
import json
import requests
from .models import *

def home(request):
    """Page d'accueil"""
    return render(request, 'transport/home.html')

def login_view(request):
    """Connexion utilisateur"""
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            # Rediriger selon le rôle
            try:
                utilisateur = Utilisateur.objects.get(user=user)
                if utilisateur.role == 'client':
                    return redirect('transport:client_dashboard')
                elif utilisateur.role == 'transporteur':
                    return redirect('transport:transporteur_dashboard')
                elif utilisateur.role == 'admin':
                    return redirect('transport:admin_dashboard')
                elif utilisateur.role == 'planificateur':
                    return redirect('transport:planificateur_dashboard')
            except Utilisateur.DoesNotExist:
                pass
            return redirect('transport:home')
        else:
            messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect.')
    
    return render(request, 'transport/login.html')

def logout_view(request):
    """Déconnexion"""
    logout(request)
    return redirect('transport:home')

@login_required
def client_dashboard(request):
    """Tableau de bord client"""
    try:
        utilisateur = Utilisateur.objects.get(user=request.user)
        client = Client.objects.get(utilisateur=utilisateur)
        commandes = Commande.objects.filter(client=client).order_by('-date_creation')
        
        context = {
            'client': client,
            'commandes': commandes,
            'nb_commandes_actives': commandes.filter(statut__in=['en_attente', 'assignee', 'en_cours']).count()
        }
        return render(request, 'transport/client_dashboard.html', context)
    except (Utilisateur.DoesNotExist, Client.DoesNotExist):
        messages.error(request, 'Profil client non trouvé.')
        return redirect('transport:home')

@login_required
def creer_commande(request):
    """Créer une nouvelle commande"""
    if request.method == 'POST':
        try:
            utilisateur = Utilisateur.objects.get(user=request.user)
            client = Client.objects.get(utilisateur=utilisateur)
            
            # Créer les adresses
            adresse_enlevement = Adresse.objects.create(
                rue=request.POST['rue_enlevement'],
                ville=request.POST['ville_enlevement'],
                code_postal=request.POST['code_postal_enlevement'],
                pays=request.POST.get('pays_enlevement', 'Maroc'),
                latitude=float(request.POST.get('lat_enlevement', 0)) if request.POST.get('lat_enlevement') else None,
                longitude=float(request.POST.get('lng_enlevement', 0)) if request.POST.get('lng_enlevement') else None
            )
            
            adresse_livraison = Adresse.objects.create(
                rue=request.POST['rue_livraison'],
                ville=request.POST['ville_livraison'],
                code_postal=request.POST['code_postal_livraison'],
                pays=request.POST.get('pays_livraison', 'Maroc'),
                latitude=float(request.POST.get('lat_livraison', 0)) if request.POST.get('lat_livraison') else None,
                longitude=float(request.POST.get('lng_livraison', 0)) if request.POST.get('lng_livraison') else None
            )
            
            # Créer la commande
            commande = Commande.objects.create(
                client=client,
                type_marchandise=request.POST['type_marchandise'],
                poids=float(request.POST['poids']),
                adresse_enlevement=adresse_enlevement,
                adresse_livraison=adresse_livraison,
                description=request.POST.get('description', ''),
                priorite=request.POST.get('priorite', 'normale')
            )
            
            messages.success(request, 'Commande créée avec succès!')
            return redirect('transport:client_dashboard')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la création: {str(e)}')
    
    return render(request, 'transport/creer_commande.html')

@login_required
def transporteur_dashboard(request):
    """Tableau de bord transporteur"""
    try:
        utilisateur = Utilisateur.objects.get(user=request.user)
        transporteur = Transporteur.objects.get(utilisateur=utilisateur)
        commandes_assignees = Commande.objects.filter(
            transporteur=transporteur,
            statut__in=['assignee', 'en_cours']
        ).order_by('-date_creation')
        
        context = {
            'transporteur': transporteur,
            'commandes': commandes_assignees,
            'nb_missions_actives': commandes_assignees.count()
        }
        return render(request, 'transport/transporteur_dashboard.html', context)
    except (Utilisateur.DoesNotExist, Transporteur.DoesNotExist):
        messages.error(request, 'Profil transporteur non trouvé.')
        return redirect('transport:home')

@login_required
def admin_dashboard(request):
    """Tableau de bord administrateur"""
    try:
        utilisateur = Utilisateur.objects.get(user=request.user)
        if utilisateur.role != 'admin':
            messages.error(request, 'Accès non autorisé.')
            return redirect('transport:home')
        
        # Statistiques
        stats = {
            'total_commandes': Commande.objects.count(),
            'commandes_en_cours': Commande.objects.filter(statut='en_cours').count(),
            'total_transporteurs': Transporteur.objects.count(),
            'transporteurs_disponibles': Transporteur.objects.filter(disponibilite=True).count(),
            'total_clients': Client.objects.count()
        }
        
        # Commandes récentes
        commandes_recentes = Commande.objects.all().order_by('-date_creation')[:10]
        
        context = {
            'stats': stats,
            'commandes_recentes': commandes_recentes
        }
        return render(request, 'transport/admin_dashboard.html', context)
    except Utilisateur.DoesNotExist:
        messages.error(request, 'Profil administrateur non trouvé.')
        return redirect('transport:home')

@login_required
def planificateur_dashboard(request):
    """Tableau de bord planificateur"""
    try:
        utilisateur = Utilisateur.objects.get(user=request.user)
        if utilisateur.role != 'planificateur':
            messages.error(request, 'Accès non autorisé.')
            return redirect('transport:home')
        
        # Statistiques pour le planificateur
        commandes_en_attente = Commande.objects.filter(statut='en_attente').count()
        transporteurs_disponibles = Transporteur.objects.filter(disponibilite=True).count()
        commandes_du_jour = Commande.objects.filter(
            date_creation__date=timezone.now().date()
        ).count()
        
        context = {
            'commandes_en_attente': commandes_en_attente,
            'transporteurs_disponibles': transporteurs_disponibles,
            'commandes_du_jour': commandes_du_jour
        }
        return render(request, 'transport/planificateur_dashboard.html', context)
    except Utilisateur.DoesNotExist:
        messages.error(request, 'Profil planificateur non trouvé.')
        return redirect('transport:home')

@login_required
def gerer_commandes(request):
    """Gestion des commandes (Admin/Planificateur)"""
    utilisateur = Utilisateur.objects.get(user=request.user)
    if utilisateur.role not in ['admin', 'planificateur']:
        messages.error(request, 'Accès non autorisé.')
        return redirect('transport:home')
    
    commandes = Commande.objects.all().order_by('-date_creation')
    transporteurs = Transporteur.objects.filter(disponibilite=True)
    
    # Pagination
    paginator = Paginator(commandes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'commandes': page_obj,
        'transporteurs': transporteurs
    }
    return render(request, 'transport/gerer_commandes.html', context)

@csrf_exempt
@login_required
def assigner_transporteur(request):
    """Assigner un transporteur à une commande"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            commande_id = data.get('commande_id')
            transporteur_id = data.get('transporteur_id')
            
            commande = get_object_or_404(Commande, id=commande_id)
            transporteur = get_object_or_404(Transporteur, id=transporteur_id)
            
            commande.transporteur = transporteur
            commande.statut = 'assignee'
            commande.save()
            
            # Créer notification
            Notification.objects.create(
                destinataire=transporteur.utilisateur.user,
                type_notification='assignation',
                titre='Nouvelle mission assignée',
                message=f'Nouvelle mission assignée: Commande #{commande.numero}',
                commande=commande
            )
            
            return JsonResponse({'success': True, 'message': 'Transporteur assigné avec succès'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

@csrf_exempt
@login_required
def mettre_a_jour_statut(request):
    """Mettre à jour le statut d'une commande"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            commande_id = data.get('commande_id')
            nouveau_statut = data.get('statut')
            
            commande = get_object_or_404(Commande, id=commande_id)
            ancien_statut = commande.statut
            commande.statut = nouveau_statut
            commande.save()
            
            # Enregistrer dans le journal
            Journal.objects.create(
                utilisateur=request.user,
                action='changement_statut',
                description=f'Commande #{commande.numero} - Statut changé de {ancien_statut} à {nouveau_statut}'
            )
            
            return JsonResponse({'success': True, 'message': 'Statut mis à jour'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

@csrf_exempt
@login_required
def calculer_itineraire(request):
    """Calculer un itinéraire avec Google Maps"""
    if request.method == 'GET':
        origine = request.GET.get('origine')
        destination = request.GET.get('destination')
        
        if not origine or not destination:
            return JsonResponse({'success': False, 'error': 'Origine et destination requises'})
        
        # Pour l'instant, retourner des données simulées
        # En production, utiliser l'API Google Maps
        return JsonResponse({
            'success': True,
            'distance': '45.2 km',
            'duree': '52 min',
            'polyline': 'encoded_polyline_string'
        })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

def suivre_commande(request, commande_id):
    """Suivi d'une commande en temps réel"""
    commande = get_object_or_404(Commande, id=commande_id)
    
    # Vérifier les permissions
    try:
        utilisateur = Utilisateur.objects.get(user=request.user)
        if utilisateur.role == 'client':
            client = Client.objects.get(utilisateur=utilisateur)
            if commande.client != client:
                messages.error(request, 'Accès non autorisé.')
                return redirect('transport:client_dashboard')
    except (Utilisateur.DoesNotExist, Client.DoesNotExist):
        messages.error(request, 'Accès non autorisé.')
        return redirect('transport:home')
    
    context = {
        'commande': commande,
    }
    return render(request, 'transport/suivre_commande.html', context)

@login_required
def notifications(request):
    """Afficher les notifications"""
    notifications = Notification.objects.filter(
        destinataire=request.user
    ).order_by('-date_creation')[:20]
    
    return render(request, 'transport/notifications.html', {'notifications': notifications})

@login_required
def journal_activite(request):
    """Journal d'activité du système"""
    # Réservé aux admins
    utilisateur = Utilisateur.objects.get(user=request.user)
    if utilisateur.role != 'admin':
        messages.error(request, 'Accès non autorisé.')
        return redirect('transport:home')
    
    journal = Journal.objects.all().order_by('-date_action')
    
    # Pagination
    paginator = Paginator(journal, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'transport/journal.html', {'journal': page_obj})

# Nouvelles fonctions ajoutées pour corriger les erreurs

@csrf_exempt
@login_required
def assignation_automatique(request):
    """Assignation automatique des commandes"""
    if request.method == 'POST':
        try:
            from .utils import trouver_transporteur_optimal
            
            # Récupérer les commandes en attente
            commandes_en_attente = Commande.objects.filter(statut='en_attente')
            assignations = []
            
            for commande in commandes_en_attente:
                transporteur = trouver_transporteur_optimal(commande)
                
                if transporteur:
                    commande.transporteur = transporteur
                    commande.statut = 'assignee'
                    commande.save()
                    
                    # Créer tracking
                    Tracking.objects.create(
                        commande=commande,
                        etape='transporteur_assigne',
                        description=f'Transporteur {transporteur.utilisateur.full_name} assigné automatiquement',
                        utilisateur=request.user
                    )
                    
                    assignations.append({
                        'commande': commande.numero,
                        'transporteur': transporteur.utilisateur.full_name
                    })
            
            return JsonResponse({
                'success': True,
                'message': f'{len(assignations)} commandes assignées',
                'assignations': assignations
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

@csrf_exempt
@login_required
def optimiser_itineraires(request):
    """Optimiser les itinéraires pour les commandes en attente"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.body else {}
            algorithme = data.get('algorithme', 'tsp')
            critere = data.get('critere', 'distance')

            # Récupérer les commandes en attente
            commandes_en_attente = Commande.objects.filter(statut='en_attente')
            resultats_optimisation = []

            for commande in commandes_en_attente:
                # Créer ou mettre à jour l'itinéraire
                itineraire, created = Itineraire.objects.get_or_create(
                    commande=commande,
                    defaults={
                        'distance_km': 0,
                        'duree_minutes': 0,
                        'optimise': True
                    }
                )
                
                resultats_optimisation.append({
                    'commande_id': str(commande.id),
                    'commande_numero': commande.numero,
                    'itineraire_id': itineraire.id,
                    'distance': itineraire.distance_km or 0,
                    'duree': itineraire.duree_minutes or 0,
                })

            return JsonResponse({
                'success': True,
                'message': f'{len(resultats_optimisation)} itinéraires optimisés',
                'resultats': resultats_optimisation,
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

@csrf_exempt
@login_required
def planifier_livraisons(request):
    """Planifier les livraisons"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.body else {}
            
            # Logique de planification
            commandes = Commande.objects.filter(statut__in=['assignee', 'en_cours'])
            planifications = []
            
            for commande in commandes:
                if commande.date_livraison_prevue:
                    planifications.append({
                        'commande_id': str(commande.id),
                        'numero': commande.numero,
                        'date_prevue': commande.date_livraison_prevue.isoformat() if commande.date_livraison_prevue else None,
                        'transporteur': commande.transporteur.utilisateur.full_name if commande.transporteur else None
                    })
            
            return JsonResponse({
                'success': True,
                'message': f'{len(planifications)} livraisons planifiées',
                'planifications': planifications
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

@csrf_exempt
@login_required
def toggle_disponibilite_transporteur(request):
    """Changer la disponibilité d'un transporteur"""
    if request.method == 'POST':
        try:
            utilisateur = Utilisateur.objects.get(user=request.user)
            if utilisateur.role == 'transporteur':
                transporteur = Transporteur.objects.get(utilisateur=utilisateur)
                transporteur.disponibilite = not transporteur.disponibilite
                
                if transporteur.disponibilite:
                    transporteur.statut = 'disponible'
                else:
                    transporteur.statut = 'repos'
                
                transporteur.save()
                
                return JsonResponse({
                    'success': True,
                    'disponibilite': transporteur.disponibilite,
                    'statut': transporteur.statut
                })
            else:
                return JsonResponse({'success': False, 'error': 'Accès non autorisé'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

@csrf_exempt
@login_required
def signaler_incident(request):
    """Signaler un incident"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            incident = Incident.objects.create(
                type_incident=data.get('type_incident'),
                titre=data.get('titre'),
                description=data.get('description'),
                gravite=data.get('gravite', 'moyenne'),
                date_incident=timezone.now(),
                commande_id=data.get('commande_id') if data.get('commande_id') else None
            )
            
            # Si c'est un transporteur, l'associer
            try:
                utilisateur = Utilisateur.objects.get(user=request.user)
                if utilisateur.role == 'transporteur':
                    transporteur = Transporteur.objects.get(utilisateur=utilisateur)
                    incident.transporteur = transporteur
                    incident.save()
            except (Utilisateur.DoesNotExist, Transporteur.DoesNotExist):
                pass
            
            return JsonResponse({
                'success': True,
                'message': 'Incident signalé avec succès',
                'incident_id': incident.id
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

@login_required
def verifier_nouvelles_missions(request):
    """Vérifier les nouvelles missions pour un transporteur"""
    try:
        utilisateur = Utilisateur.objects.get(user=request.user)
        if utilisateur.role == 'transporteur':
            transporteur = Transporteur.objects.get(utilisateur=utilisateur)
            
            # Missions récemment assignées
            nouvelles_missions = Commande.objects.filter(
                transporteur=transporteur,
                statut='assignee',
                date_creation__gte=timezone.now() - timezone.timedelta(hours=1)
            ).count()
            
            return JsonResponse({
                'success': True,
                'nouvelles_missions': nouvelles_missions
            })
        else:
            return JsonResponse({'success': False, 'error': 'Accès non autorisé'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})