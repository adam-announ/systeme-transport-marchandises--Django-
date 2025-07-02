"""
Vues pour l'interface transporteur
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from core.models import Commande, Vehicule, BonLivraison, Notification
import uuid

@login_required
def dashboard(request):
    """Tableau de bord transporteur"""
    if request.user.role != 'transporteur':
        return redirect('auth:login')
    
    missions_actives = Commande.objects.filter(
        transporteur=request.user, 
        statut__in=['confirmee', 'en_cours']
    ).count()
    
    missions_completees = Commande.objects.filter(
        transporteur=request.user, 
        statut='livree'
    ).count()
    
    vehicules_count = Vehicule.objects.filter(transporteur=request.user).count()
    
    prochaines_missions = Commande.objects.filter(
        transporteur=request.user,
        statut='confirmee'
    ).order_by('date_enlevement_prevue')[:3]
    
    stats = {
        'missions_actives': missions_actives,
        'missions_completees': missions_completees,
        'vehicules_count': vehicules_count,
    }
    
    return render(request, 'transporteur/dashboard.html', {
        'stats': stats,
        'prochaines_missions': prochaines_missions
    })

@login_required
def mes_missions(request):
    """Liste des missions du transporteur"""
    if request.user.role != 'transporteur':
        return redirect('auth:login')
    
    missions = Commande.objects.filter(transporteur=request.user).order_by('-date_creation')
    return render(request, 'transporteur/mes_missions.html', {'missions': missions})

@login_required
def mission_detail(request, mission_id):
    """Détail d'une mission"""
    if request.user.role != 'transporteur':
        return redirect('auth:login')
    
    mission = get_object_or_404(Commande, id=mission_id, transporteur=request.user)
    return render(request, 'transporteur/mission_detail.html', {'mission': mission})

@login_required
def itineraire_mission(request, mission_id):
    """Affichage de l'itinéraire d'une mission"""
    if request.user.role != 'transporteur':
        return redirect('auth:login')
    
    mission = get_object_or_404(Commande, id=mission_id, transporteur=request.user)
    return render(request, 'transporteur/itineraire_mission.html', {'mission': mission})

@login_required
def mettre_a_jour_statut(request, mission_id):
    """Mettre à jour le statut d'une mission"""
    if request.user.role != 'transporteur':
        return redirect('auth:login')
    
    mission = get_object_or_404(Commande, id=mission_id, transporteur=request.user)
    
    if request.method == 'POST':
        nouveau_statut = request.POST.get('statut')
        commentaire = request.POST.get('commentaire', '')
        
        if nouveau_statut in ['en_cours', 'livree']:
            mission.statut = nouveau_statut
            
            if nouveau_statut == 'en_cours':
                mission.date_enlevement_reelle = timezone.now()
            elif nouveau_statut == 'livree':
                mission.date_livraison_reelle = timezone.now()
                
                # Création du bon de livraison
                bon_livraison = BonLivraison.objects.create(
                    commande=mission,
                    numero_bon=f"BL-{uuid.uuid4().hex[:8].upper()}",
                    date_livraison=timezone.now(),
                    nom_destinataire=request.POST.get('nom_destinataire', ''),
                    commentaires=commentaire
                )
            
            mission.save()
            
            # Notification au client
            Notification.objects.create(
                utilisateur=mission.client,
                titre=f"Mise à jour commande {mission.numero}",
                message=f"Votre commande est maintenant: {mission.get_statut_display()}",
                type_notification='info'
            )
            
            messages.success(request, 'Statut mis à jour avec succès')
        
        return redirect('transporteur:mission_detail', mission_id=mission.id)
    
    return render(request, 'transporteur/mettre_a_jour_statut.html', {'mission': mission})

@login_required
def signaler_incident(request, mission_id):
    """Signaler un incident"""
    if request.user.role != 'transporteur':
        return redirect('auth:login')
    
    mission = get_object_or_404(Commande, id=mission_id, transporteur=request.user)
    
    if request.method == 'POST':
        type_incident = request.POST.get('type_incident')
        description = request.POST.get('description')
        
        # Notification aux administrateurs
        from core.models import User
        admins = User.objects.filter(role='admin')
        for admin in admins:
            Notification.objects.create(
                utilisateur=admin,
                titre=f"Incident signalé - {mission.numero}",
                message=f"Type: {type_incident}\nDescription: {description}",
                type_notification='warning'
            )
        
        # Notification au client
        Notification.objects.create(
            utilisateur=mission.client,
            titre=f"Incident sur votre commande {mission.numero}",
            message=f"Un incident a été signalé: {type_incident}",
            type_notification='warning'
        )
        
        messages.success(request, 'Incident signalé avec succès')
        return redirect('transporteur:mission_detail', mission_id=mission.id)
    
    return render(request, 'transporteur/signaler_incident.html', {'mission': mission})

@login_required
def mes_vehicules(request):
    """Gestion des véhicules"""
    if request.user.role != 'transporteur':
        return redirect('auth:login')
    
    vehicules = Vehicule.objects.filter(transporteur=request.user)
    return render(request, 'transporteur/mes_vehicules.html', {'vehicules': vehicules})

@login_required
def ajouter_vehicule(request):
    """Ajouter un nouveau véhicule"""
    if request.user.role != 'transporteur':
        return redirect('auth:login')
    
    if request.method == 'POST':
        vehicule = Vehicule.objects.create(
            transporteur=request.user,
            immatriculation=request.POST.get('immatriculation'),
            type_vehicule=request.POST.get('type_vehicule'),
            capacite_poids=float(request.POST.get('capacite_poids')),
            capacite_volume=float(request.POST.get('capacite_volume'))
        )
        
        messages.success(request, 'Véhicule ajouté avec succès')
        return redirect('transporteur:mes_vehicules')
    
    return render(request, 'transporteur/ajouter_vehicule.html')

@api_view(['GET'])
def api_mes_missions(request):
    """API pour récupérer les missions du transporteur"""
    if request.user.role != 'transporteur':
        return Response({'error': 'Accès non autorisé'}, status=403)
    
    missions = Commande.objects.filter(transporteur=request.user).order_by('-date_creation')
    data = []
    
    for mission in missions:
        data.append({
            'id': str(mission.id),
            'numero': mission.numero,
            'statut': mission.statut,
            'client': mission.client.username,
            'adresse_enlevement': mission.adresse_enlevement,
            'adresse_livraison': mission.adresse_livraison,
            'date_enlevement_prevue': mission.date_enlevement_prevue.isoformat(),
            'poids': mission.poids,
            'volume': mission.volume,
        })
    
    return Response(data)

@api_view(['POST'])
def api_mettre_a_jour_position(request):
    """API pour mettre à jour la position du transporteur"""
    if request.user.role != 'transporteur':
        return Response({'error': 'Accès non autorisé'}, status=403)
    
    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')
    mission_id = request.data.get('mission_id')
    
    try:
        if mission_id:
            mission = Commande.objects.get(id=mission_id, transporteur=request.user)
        
        # Ici, vous pourriez sauvegarder la position dans une table de tracking
        # Pour la démo, on retourne juste un succès
        
        return Response({
            'success': True,
            'message': 'Position mise à jour'
        })
        
    except Commande.DoesNotExist:
        return Response({'error': 'Mission non trouvée'}, status=404)

@api_view(['POST'])
def api_confirmer_livraison(request):
    """API pour confirmer une livraison"""
    if request.user.role != 'transporteur':
        return Response({'error': 'Accès non autorisé'}, status=403)
    
    mission_id = request.data.get('mission_id')
    nom_destinataire = request.data.get('nom_destinataire')
    signature = request.data.get('signature')
    
    try:
        mission = Commande.objects.get(id=mission_id, transporteur=request.user)
        mission.statut = 'livree'
        mission.date_livraison_reelle = timezone.now()
        mission.save()
        
        # Création du bon de livraison
        bon_livraison = BonLivraison.objects.create(
            commande=mission,
            numero_bon=f"BL-{uuid.uuid4().hex[:8].upper()}",
            date_livraison=timezone.now(),
            nom_destinataire=nom_destinataire,
            signature_destinataire=signature
        )
        
        return Response({
            'success': True,
            'bon_livraison': {
                'numero': bon_livraison.numero_bon,
                'date': bon_livraison.date_livraison.isoformat()
            }
        })
        
    except Commande.DoesNotExist:
        return Response({'error': 'Mission non trouvée'}, status=404)

@api_view(['GET'])
def api_vehicules(request):
    """API pour récupérer les véhicules du transporteur"""
    if request.user.role != 'transporteur':
        return Response({'error': 'Accès non autorisé'}, status=403)
    
    vehicules = Vehicule.objects.filter(transporteur=request.user)
    data = []
    
    for vehicule in vehicules:
        data.append({
            'id': str(vehicule.id),
            'immatriculation': vehicule.immatriculation,
            'type_vehicule': vehicule.type_vehicule,
            'capacite_poids': vehicule.capacite_poids,
            'capacite_volume': vehicule.capacite_volume,
            'disponible': vehicule.disponible
        })
    
    return Response(data)

@api_view(['GET'])
def api_statut(request):
    """API pour récupérer le statut du transporteur"""
    if request.user.role != 'transporteur':
        return Response({'error': 'Accès non autorisé'}, status=403)
    
    # Calcul des km parcourus (simulation)
    missions_completees = Commande.objects.filter(
        transporteur=request.user, 
        statut='livree'
    ).count()
    
    km_parcourus = missions_completees * 50  # Simulation
    
    return Response({
        'km_parcourus': km_parcourus,
        'missions_actives': Commande.objects.filter(
            transporteur=request.user, 
            statut__in=['confirmee', 'en_cours']
        ).count(),
        'statut': 'disponible'  # ou 'en_mission', 'indisponible'
    })

@api_view(['POST'])
def api_incident(request):
    """API pour signaler un incident"""
    if request.user.role != 'transporteur':
        return Response({'error': 'Accès non autorisé'}, status=403)
    
    type_incident = request.data.get('type_incident')
    description = request.data.get('description')
    mission_id = request.data.get('mission_id')
    
    if not type_incident or not description:
        return Response({'error': 'Données manquantes'}, status=400)
    
    # Création des notifications pour les admins
    from core.models import User
    admins = User.objects.filter(role='admin')
    
    for admin in admins:
        Notification.objects.create(
            utilisateur=admin,
            titre=f'Incident signalé - {request.user.username}',
            message=f'Type: {type_incident}\nDescription: {description}',
            type_notification='warning'
        )
    
    # Si une mission est concernée, notifier le client
    if mission_id:
        try:
            mission = Commande.objects.get(id=mission_id, transporteur=request.user)
            Notification.objects.create(
                utilisateur=mission.client,
                titre=f'Incident sur votre commande {mission.numero}',
                message=f'Un incident a été signalé: {type_incident}',
                type_notification='warning'
            )
        except Commande.DoesNotExist:
            pass
    
    return Response({'success': True, 'message': 'Incident signalé avec succès'})