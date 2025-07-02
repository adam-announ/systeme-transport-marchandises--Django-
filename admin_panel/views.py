"""
Vues pour l'interface administrateur
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
from rest_framework.decorators import api_view
from rest_framework.response import Response
from core.models import User, Commande, JournalActivite, ConfigurationSysteme, Notification

@login_required
def dashboard(request):
    """Tableau de bord administrateur"""
    if request.user.role != 'admin':
        return redirect('auth:login')
    
    # Statistiques générales
    stats = {
        'total_utilisateurs': User.objects.count(),
        'total_commandes': Commande.objects.count(),
        'commandes_en_cours': Commande.objects.filter(statut='en_cours').count(),
        'commandes_livrees': Commande.objects.filter(statut='livree').count(),
        'clients_actifs': User.objects.filter(role='client', actif=True).count(),
        'transporteurs_actifs': User.objects.filter(role='transporteur', actif=True).count(),
    }
    
    # Activités récentes
    activites_recentes = JournalActivite.objects.all()[:10]
    
    # Commandes récentes
    commandes_recentes = Commande.objects.all().order_by('-date_creation')[:5]
    
    return render(request, 'admin/dashboard.html', {
        'stats': stats,
        'activites_recentes': activites_recentes,
        'commandes_recentes': commandes_recentes
    })

@login_required
def gestion_utilisateurs(request):
    """Gestion des utilisateurs"""
    if request.user.role != 'admin':
        return redirect('auth:login')
    
    utilisateurs = User.objects.all().order_by('-date_creation')
    return render(request, 'admin/gestion_utilisateurs.html', {'utilisateurs': utilisateurs})

@login_required
def creer_utilisateur(request):
    """Créer un nouvel utilisateur"""
    if request.user.role != 'admin':
        return redirect('auth:login')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Ce nom d\'utilisateur existe déjà')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Cet email est déjà utilisé')
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role=role,
                first_name=request.POST.get('first_name', ''),
                last_name=request.POST.get('last_name', ''),
                telephone=request.POST.get('telephone', ''),
                adresse=request.POST.get('adresse', '')
            )
            
            # Journal d'activité
            JournalActivite.objects.create(
                utilisateur=request.user,
                action=f"Création utilisateur {username}",
                details={'role': role, 'email': email},
                adresse_ip=request.META.get('REMOTE_ADDR', '')
            )
            
            messages.success(request, f'Utilisateur {username} créé avec succès')
            return redirect('admin_panel:gestion_utilisateurs')
    
    return render(request, 'admin/creer_utilisateur.html')

@login_required
def modifier_utilisateur(request, user_id):
    """Modifier un utilisateur"""
    if request.user.role != 'admin':
        return redirect('auth:login')
    
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email')
        user.role = request.POST.get('role')
        user.telephone = request.POST.get('telephone', '')
        user.adresse = request.POST.get('adresse', '')
        user.actif = request.POST.get('actif') == 'on'
        user.save()
        
        # Journal d'activité
        JournalActivite.objects.create(
            utilisateur=request.user,
            action=f"Modification utilisateur {user.username}",
            details={'role': user.role, 'actif': user.actif},
            adresse_ip=request.META.get('REMOTE_ADDR', '')
        )
        
        messages.success(request, f'Utilisateur {user.username} modifié avec succès')
        return redirect('admin_panel:gestion_utilisateurs')
    
    return render(request, 'admin/modifier_utilisateur.html', {'user_obj': user})

@login_required
def gestion_commandes(request):
    """Gestion des commandes"""
    if request.user.role != 'admin':
        return redirect('auth:login')
    
    commandes = Commande.objects.all().order_by('-date_creation')
    return render(request, 'admin/gestion_commandes.html', {'commandes': commandes})

@login_required
def journal_activite(request):
    """Journal d'activité du système"""
    if request.user.role != 'admin':
        return redirect('auth:login')
    
    activites = JournalActivite.objects.all().order_by('-date_action')
    return render(request, 'admin/journal_activite.html', {'activites': activites})

@login_required
def configuration_systeme(request):
    """Configuration du système"""
    if request.user.role != 'admin':
        return redirect('auth:login')
    
    if request.method == 'POST':
        for key, value in request.POST.items():
            if key != 'csrfmiddlewaretoken':
                config, created = ConfigurationSysteme.objects.get_or_create(
                    cle=key,
                    defaults={'valeur': value}
                )
                if not created:
                    config.valeur = value
                    config.save()
        
        messages.success(request, 'Configuration mise à jour avec succès')
    
    configurations = ConfigurationSysteme.objects.all()
    return render(request, 'admin/configuration_systeme.html', {'configurations': configurations})

@login_required
def envoyer_notification(request):
    """Envoyer une notification"""
    if request.user.role != 'admin':
        return redirect('auth:login')
    
    if request.method == 'POST':
        destinataires = request.POST.getlist('destinataires')
        titre = request.POST.get('titre')
        message = request.POST.get('message')
        type_notification = request.POST.get('type_notification', 'info')
        
        if 'tous' in destinataires:
            users = User.objects.filter(actif=True)
        else:
            users = User.objects.filter(id__in=destinataires)
        
        for user in users:
            Notification.objects.create(
                utilisateur=user,
                titre=titre,
                message=message,
                type_notification=type_notification
            )
        
        messages.success(request, f'Notification envoyée à {users.count()} utilisateur(s)')
        return redirect('admin_panel:dashboard')
    
    utilisateurs = User.objects.filter(actif=True)
    return render(request, 'admin/envoyer_notification.html', {'utilisateurs': utilisateurs})

@login_required
def rapports(request):
    """Génération de rapports"""
    if request.user.role != 'admin':
        return redirect('auth:login')
    
    # Statistiques par période
    from django.utils import timezone
    from datetime import timedelta
    
    aujourd_hui = timezone.now().date()
    il_y_a_7_jours = aujourd_hui - timedelta(days=7)
    il_y_a_30_jours = aujourd_hui - timedelta(days=30)
    
    stats_periode = {
        'commandes_aujourd_hui': Commande.objects.filter(date_creation__date=aujourd_hui).count(),
        'commandes_7_jours': Commande.objects.filter(date_creation__date__gte=il_y_a_7_jours).count(),
        'commandes_30_jours': Commande.objects.filter(date_creation__date__gte=il_y_a_30_jours).count(),
    }
    
    # Statistiques par statut
    stats_statut = Commande.objects.values('statut').annotate(count=Count('id'))
    
    # Top clients
    top_clients = User.objects.filter(role='client').annotate(
        nb_commandes=Count('commandes')
    ).order_by('-nb_commandes')[:10]
    
    return render(request, 'admin/rapports.html', {
        'stats_periode': stats_periode,
        'stats_statut': stats_statut,
        'top_clients': top_clients
    })

@api_view(['GET'])
def api_statistiques(request):
    """API pour récupérer les statistiques"""
    if request.user.role != 'admin':
        return Response({'error': 'Accès non autorisé'}, status=403)
    
    stats = {
        'utilisateurs': {
            'total': User.objects.count(),
            'clients': User.objects.filter(role='client').count(),
            'transporteurs': User.objects.filter(role='transporteur').count(),
            'planificateurs': User.objects.filter(role='planificateur').count(),
        },
        'commandes': {
            'total': Commande.objects.count(),
            'en_attente': Commande.objects.filter(statut='en_attente').count(),
            'confirmees': Commande.objects.filter(statut='confirmee').count(),
            'en_cours': Commande.objects.filter(statut='en_cours').count(),
            'livrees': Commande.objects.filter(statut='livree').count(),
            'annulees': Commande.objects.filter(statut='annulee').count(),
        }
    }
    
    return Response(stats)

@api_view(['POST'])
def api_supprimer_utilisateur(request, user_id):
    """API pour supprimer un utilisateur"""
    if request.user.role != 'admin':
        return Response({'error': 'Accès non autorisé'}, status=403)
    
    try:
        user = User.objects.get(id=user_id)
        if user == request.user:
            return Response({'error': 'Impossible de supprimer votre propre compte'}, status=400)
        
        username = user.username
        user.delete()
        
        # Journal d'activité
        JournalActivite.objects.create(
            utilisateur=request.user,
            action=f"Suppression utilisateur {username}",
            details={'user_id': str(user_id)},
            adresse_ip=request.META.get('REMOTE_ADDR', '')
        )
        
        return Response({'success': True, 'message': f'Utilisateur {username} supprimé'})
        
    except User.DoesNotExist:
        return Response({'error': 'Utilisateur non trouvé'}, status=404)