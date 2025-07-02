"""
Vues pour l'interface client
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from core.models import Commande, User, Notification
import uuid

@login_required
def dashboard(request):
    """Tableau de bord client"""
    if request.user.role != 'client':
        return redirect('auth:login')
    
    commandes = Commande.objects.filter(client=request.user).order_by('-date_creation')[:5]
    stats = {
        'total_commandes': Commande.objects.filter(client=request.user).count(),
        'en_cours': Commande.objects.filter(client=request.user, statut='en_cours').count(),
        'livrees': Commande.objects.filter(client=request.user, statut='livree').count(),
    }
    
    return render(request, 'client/dashboard.html', {
        'commandes': commandes,
        'stats': stats
    })

@login_required
def nouvelle_commande(request):
    """Créer une nouvelle commande"""
    if request.user.role != 'client':
        return redirect('auth:login')
    
    if request.method == 'POST':
        # Récupération des données du formulaire
        adresse_enlevement = request.POST.get('adresse_enlevement')
        adresse_livraison = request.POST.get('adresse_livraison')
        lat_enlevement = float(request.POST.get('lat_enlevement'))
        lng_enlevement = float(request.POST.get('lng_enlevement'))
        lat_livraison = float(request.POST.get('lat_livraison'))
        lng_livraison = float(request.POST.get('lng_livraison'))
        description = request.POST.get('description_marchandise')
        poids = float(request.POST.get('poids'))
        volume = float(request.POST.get('volume'))
        date_enlevement = request.POST.get('date_enlevement_prevue')
        
        # Création de la commande
        commande = Commande.objects.create(
            numero=f"CMD-{uuid.uuid4().hex[:8].upper()}",
            client=request.user,
            adresse_enlevement=adresse_enlevement,
            adresse_livraison=adresse_livraison,
            latitude_enlevement=lat_enlevement,
            longitude_enlevement=lng_enlevement,
            latitude_livraison=lat_livraison,
            longitude_livraison=lng_livraison,
            description_marchandise=description,
            poids=poids,
            volume=volume,
            date_enlevement_prevue=date_enlevement,
            date_livraison_prevue=date_enlevement,  # À calculer avec l'optimisation
        )
        
        messages.success(request, f'Commande {commande.numero} créée avec succès')
        return redirect('client:commande_detail', commande_id=commande.id)
    
    return render(request, 'client/nouvelle_commande.html')

@login_required
def mes_commandes(request):
    """Liste des commandes du client"""
    if request.user.role != 'client':
        return redirect('auth:login')
    
    commandes = Commande.objects.filter(client=request.user).order_by('-date_creation')
    return render(request, 'client/mes_commandes.html', {'commandes': commandes})

@login_required
def commande_detail(request, commande_id):
    """Détail d'une commande"""
    if request.user.role != 'client':
        return redirect('auth:login')
    
    commande = get_object_or_404(Commande, id=commande_id, client=request.user)
    return render(request, 'client/commande_detail.html', {'commande': commande})

@login_required
def suivi_commande(request, commande_id):
    """Suivi en temps réel d'une commande"""
    if request.user.role != 'client':
        return redirect('auth:login')
    
    commande = get_object_or_404(Commande, id=commande_id, client=request.user)
    return render(request, 'client/suivi_commande.html', {'commande': commande})

@api_view(['GET'])
def api_commandes(request):
    """API pour récupérer les commandes du client"""
    if request.user.role != 'client':
        return Response({'error': 'Accès non autorisé'}, status=403)
    
    commandes = Commande.objects.filter(client=request.user).order_by('-date_creation')
    data = []
    
    for commande in commandes:
        data.append({
            'id': str(commande.id),
            'numero': commande.numero,
            'statut': commande.statut,
            'adresse_enlevement': commande.adresse_enlevement,
            'adresse_livraison': commande.adresse_livraison,
            'date_creation': commande.date_creation.isoformat(),
            'transporteur': commande.transporteur.username if commande.transporteur else None,
        })
    
    return Response(data)

@api_view(['GET'])
def api_suivi_commande(request, commande_id):
    """API pour le suivi d'une commande"""
    if request.user.role != 'client':
        return Response({'error': 'Accès non autorisé'}, status=403)
    
    try:
        commande = Commande.objects.get(id=commande_id, client=request.user)
        data = {
            'id': str(commande.id),
            'numero': commande.numero,
            'statut': commande.statut,
            'position_transporteur': {
                'lat': commande.latitude_enlevement,  # Position simulée
                'lng': commande.longitude_enlevement,
            } if commande.transporteur else None,
            'progression': {
                'en_attente': commande.statut in ['en_attente', 'confirmee', 'en_cours', 'livree'],
                'confirmee': commande.statut in ['confirmee', 'en_cours', 'livree'],
                'en_cours': commande.statut in ['en_cours', 'livree'],
                'livree': commande.statut == 'livree',
            }
        }
        return Response(data)
    except Commande.DoesNotExist:
        return Response({'error': 'Commande non trouvée'}, status=404)