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
        from core.models import Adresse
        
        # Récupération des données du formulaire
        adresse_enlevement_str = request.POST.get('adresse_enlevement')
        adresse_livraison_str = request.POST.get('adresse_livraison')
        lat_enlevement = float(request.POST.get('lat_enlevement', 0))
        lng_enlevement = float(request.POST.get('lng_enlevement', 0))
        lat_livraison = float(request.POST.get('lat_livraison', 0))
        lng_livraison = float(request.POST.get('lng_livraison', 0))
        description = request.POST.get('description_marchandise')
        poids = float(request.POST.get('poids'))
        volume = float(request.POST.get('volume'))
        date_enlevement = request.POST.get('date_enlevement_prevue')
        
        # Créer les objets Adresse
        adresse_enl = Adresse.objects.create(
            rue=adresse_enlevement_str,
            ville='Casablanca',
            code_postal='20000',
            latitude=lat_enlevement,
            longitude=lng_enlevement
        )
        
        adresse_liv = Adresse.objects.create(
            rue=adresse_livraison_str,
            ville='Casablanca',
            code_postal='20000',
            latitude=lat_livraison,
            longitude=lng_livraison
        )
        
        # Créer le type de marchandise par défaut
        from core.models import TypeMarchandise
        type_marchandise, _ = TypeMarchandise.objects.get_or_create(
            nom='Standard',
            defaults={'tarif_base': 100.0}
        )
        
        # Création de la commande
        commande = Commande.objects.create(
            numero=f"CMD-{uuid.uuid4().hex[:8].upper()}",
            client=request.user,
            adresse_enlevement=adresse_enl,
            adresse_livraison=adresse_liv,
            type_marchandise=type_marchandise,
            description_marchandise=description,
            poids=poids,
            volume=volume,
            date_enlevement_prevue=date_enlevement,
            date_livraison_prevue=date_enlevement,
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
            'adresse_enlevement': commande.adresse_enlevement.adresse_complete if commande.adresse_enlevement else '',
            'adresse_livraison': commande.adresse_livraison.adresse_complete if commande.adresse_livraison else '',
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
                'lat': commande.adresse_enlevement.latitude,
                'lng': commande.adresse_enlevement.longitude,
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