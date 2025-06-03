from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.core.paginator import Paginator
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
                    return redirect('client_dashboard')
                elif utilisateur.role == 'transporteur':
                    return redirect('transporteur_dashboard')
                elif utilisateur.role == 'admin':
                    return redirect('admin_dashboard')
                elif utilisateur.role == 'planificateur':
                    return redirect('planificateur_dashboard')
            except Utilisateur.DoesNotExist:
                pass
            return redirect('home')
        else:
            messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect.')
    
    return render(request, 'transport/login.html')

def logout_view(request):
    """Déconnexion"""
    logout(request)
    return redirect('home')

@login_required
def client_dashboard(request):
    """Tableau de bord client"""
    try:
        client = Client.objects.get(user=request.user)
        commandes = Commande.objects.filter(client=client).order_by('-date_creation')
        
        context = {
            'client': client,
            'commandes': commandes,
            'nb_commandes_actives': commandes.filter(statut__in=['en_attente', 'assignee', 'en_cours']).count()
        }
        return render(request, 'transport/client_dashboard.html', context)
    except Client.DoesNotExist:
        messages.error(request, 'Profil client non trouvé.')
        return redirect('home')

@login_required
def creer_commande(request):
    """Créer une nouvelle commande"""
    if request.method == 'POST':
        try:
            client = Client.objects.get(user=request.user)
            
            # Créer les adresses
            adresse_enlevement = Adresse.objects.create(
                rue=request.POST['rue_enlevement'],
                ville=request.POST['ville_enlevement'],
                code_postal=request.POST['code_postal_enlevement'],
                pays=request.POST.get('pays_enlevement', 'Maroc'),
                latitude=float(request.POST.get('lat_enlevement', 0)),
                longitude=float(request.POST.get('lng_enlevement', 0))
            )
            
            adresse_livraison = Adresse.objects.create(
                rue=request.POST['rue_livraison'],
                ville=request.POST['ville_livraison'],
                code_postal=request.POST['code_postal_livraison'],
                pays=request.POST.get('pays_livraison', 'Maroc'),
                latitude=float(request.POST.get('lat_livraison', 0)),
                longitude=float(request.POST.get('lng_livraison', 0))
            )
            
            # Créer la commande
            commande = Commande.objects.create(
                client=client,
                type_marchandise=request.POST['type_marchandise'],
                poids=float(request.POST['poids']),
                adresse_enlevement=adresse_enlevement,
                adresse_livraison=adresse_livraison
            )
            
            # Créer l'itinéraire
            Itineraire.objects.create(
                commande=commande,
                point_depart=adresse_enlevement,
                point_arrivee=adresse_livraison,
                distance=0,  # À calculer avec Google Maps
                temps_estime=0
            )
            
            messages.success(request, 'Commande créée avec succès!')
            return redirect('client_dashboard')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la création: {str(e)}')
    
    return render(request, 'transport/creer_commande.html')

@login_required
def transporteur_dashboard(request):
    """Tableau de bord transporteur"""
    try:
        transporteur = Transporteur.objects.get(utilisateur__user=request.user)
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
    except Transporteur.DoesNotExist:
        messages.error(request, 'Profil transporteur non trouvé.')
        return redirect('home')

@login_required
def admin_dashboard(request):
    """Tableau de bord administrateur"""
    try:
        admin = Admin.objects.get(user=request.user)
        
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
            'admin': admin,
            'stats': stats,
            'commandes_recentes': commandes_recentes
        }
        return render(request, 'transport/admin_dashboard.html', context)
    except Admin.DoesNotExist:
        messages.error(request, 'Profil administrateur non trouvé.')
        return redirect('home')

@login_required
def gerer_commandes(request):
    """Gestion des commandes (Admin/Planificateur)"""
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
                type='assignation',
                contenu=f'Nouvelle mission assignée: Commande #{commande.id}',
                destinataire=transporteur.utilisateur.email,
                transporteur=transporteur
            )
            
            return JsonResponse({'success': True, 'message': 'Transporteur assigné avec succès'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

@csrf_exempt
def mettre_a_jour_statut(request):
    """Mettre à jour le statut d'une commande"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            commande_id = data.get('commande_id')
            nouveau_statut = data.get('statut')
            
            commande = get_object_or_404(Commande, id=commande_id)
            commande.statut = nouveau_statut
            commande.save()
            
            # Enregistrer dans le journal
            Journal.objects.create(
                action=f'Statut mis à jour: {nouveau_statut}',
                utilisateur=request.user.username,
                details=f'Commande #{commande.id} - Nouveau statut: {nouveau_statut}'
            )
            
            return JsonResponse({'success': True, 'message': 'Statut mis à jour'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

def calculer_itineraire(request):
    """Calculer un itinéraire avec Google Maps"""
    if request.method == 'GET':
        origine = request.GET.get('origine')
        destination = request.GET.get('destination')
        
        # Clé API Google Maps (à remplacer par votre clé)
        API_KEY = 'VOTRE_CLE_API_GOOGLE_MAPS'
        
        url = f"https://maps.googleapis.com/maps/api/directions/json"
        params = {
            'origin': origine,
            'destination': destination,
            'key': API_KEY,
            'language': 'fr'
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if data['status'] == 'OK':
                route = data['routes'][0]
                leg = route['legs'][0]
                
                return JsonResponse({
                    'success': True,
                    'distance': leg['distance']['text'],
                    'duree': leg['duration']['text'],
                    'polyline': route['overview_polyline']['points']
                })
            else:
                return JsonResponse({'success': False, 'error': 'Itinéraire non trouvé'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

def suivre_commande(request, commande_id):
    """Suivi d'une commande en temps réel"""
    commande = get_object_or_404(Commande, id=commande_id)
    
    # Vérifier les permissions
    if hasattr(request.user, 'client') and commande.client != request.user.client:
        messages.error(request, 'Accès non autorisé.')
        return redirect('client_dashboard')
    
    context = {
        'commande': commande,
        'itineraire': getattr(commande, 'itineraire', None)
    }
    return render(request, 'transport/suivre_commande.html', context)

def notifications(request):
    """Afficher les notifications"""
    if hasattr(request.user, 'transporteur'):
        transporteur = request.user.transporteur
        notifications = Notification.objects.filter(
            transporteur=transporteur
        ).order_by('-date_creation')[:20]
    else:
        notifications = []
    
    return render(request, 'transport/notifications.html', {'notifications': notifications})

def journal_activite(request):
    """Journal d'activité du système"""
    # Réservé aux admins
    if not hasattr(request.user, 'admin'):
        messages.error(request, 'Accès non autorisé.')
        return redirect('home')
    
    journal = Journal.objects.all().order_by('-date_action')
    
    # Pagination
    paginator = Paginator(journal, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'transport/journal.html', {'journal': page_obj})

    # Ajouter ces vues au fichier views.py existant

@login_required
def planificateur_dashboard(request):
    """Tableau de bord planificateur"""
    try:
        planificateur = Planificateur.objects.get(user=request.user)
        
        # Statistiques pour le planificateur
        commandes_en_attente = Commande.objects.filter(statut='en_attente').count()
        transporteurs_disponibles = Transporteur.objects.filter(disponibilite=True).count()
        commandes_du_jour = Commande.objects.filter(
            date_creation__date=timezone.now().date()
        ).count()
        
        context = {
            'planificateur': planificateur,
            'commandes_en_attente': commandes_en_attente,
            'transporteurs_disponibles': transporteurs_disponibles,
            'commandes_du_jour': commandes_du_jour
        }
        return render(request, 'transport/planificateur_dashboard.html', context)
    except Planificateur.DoesNotExist:
        messages.error(request, 'Profil planificateur non trouvé.')
        return redirect('home')

@csrf_exempt
def optimiser_itineraires(request):
    """Optimiser les itinéraires pour les commandes en attente"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            algorithme = data.get('algorithme', 'tsp')
            critere = data.get('critere', 'distance')
            
            # Récupérer les commandes en attente
            commandes_en_attente = Commande.objects.filter(statut='en_attente')
            
            resultats_optimisation = []
            distance_economisee = 0
            temps_economise = 0
            
            for commande in commandes_en_attente:
                # Simuler l'optimisation d'itinéraire
                itineraire, created = Itineraire.objects.get_or_create(
                    commande=commande,
                    defaults={
                        'point_depart': commande.adresse_enlevement,
                        'point_arrivee': commande.adresse_liv