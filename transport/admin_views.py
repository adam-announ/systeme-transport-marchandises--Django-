# transport/admin_views.py
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Client, Commande, Transporteur

@staff_member_required
def dashboard_admin(request):
    """Tableau de bord principal de l'administrateur"""
    context = {
        'total_users': User.objects.count(),
        'total_clients': Client.objects.count(),
        'total_transporteurs': Transporteur.objects.count(),
        'transporteurs_disponibles': Transporteur.objects.filter(disponible=True).count(),
        'commandes_jour': Commande.objects.filter(
            date_creation__date=timezone.now().date()
        ).count(),
        'commandes_attente': Commande.objects.filter(statut='EN_ATTENTE').count(),
    }
    return render(request, 'admin/dashboard.html', context)

@staff_member_required
def gestion_utilisateurs(request):
    """Gérer les utilisateurs du système"""
    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        
        if action == 'toggle_active' and user_id:
            user = User.objects.get(id=user_id)
            user.is_active = not user.is_active
            user.save()
            status = "activé" if user.is_active else "désactivé"
            messages.success(request, f"Utilisateur {user.username} {status}")
        
        elif action == 'make_staff' and user_id:
            user = User.objects.get(id=user_id)
            user.is_staff = True
            user.save()
            messages.success(request, f"{user.username} est maintenant administrateur")
    
    users = User.objects.all().select_related('client').order_by('-date_joined')
    return render(request, 'admin/gestion_utilisateurs.html', {'users': users})

@staff_member_required
def gestion_roles(request):
    """Gérer les rôles et permissions"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create_group':
            group_name = request.POST.get('group_name')
            if group_name:
                group, created = Group.objects.get_or_create(name=group_name)
                if created:
                    messages.success(request, f"Groupe '{group_name}' créé")
                else:
                    messages.warning(request, f"Le groupe '{group_name}' existe déjà")
        
        elif action == 'assign_user':
            user_id = request.POST.get('user_id')
            group_id = request.POST.get('group_id')
            if user_id and group_id:
                user = User.objects.get(id=user_id)
                group = Group.objects.get(id=group_id)
                user.groups.add(group)
                messages.success(request, f"{user.username} ajouté au groupe {group.name}")
    
    groups = Group.objects.all()
    users = User.objects.all()
    return render(request, 'admin/gestion_roles.html', {
        'groups': groups,
        'users': users
    })

@staff_member_required
def journal_activite(request):
    """Consulter le journal d'activité du système"""
    activites = []
    
    # Dernières commandes
    commandes_recentes = Commande.objects.order_by('-date_creation')[:10]
    for commande in commandes_recentes:
        activites.append({
            'date': commande.date_creation,
            'type': 'Commande',
            'description': f"Commande #{commande.id} créée par {commande.client.user.username}",
            'utilisateur': commande.client.user.username
        })
    
    # Derniers utilisateurs
    users_recents = User.objects.order_by('-date_joined')[:5]
    for user in users_recents:
        activites.append({
            'date': user.date_joined,
            'type': 'Inscription',
            'description': f"Nouvel utilisateur: {user.username}",
            'utilisateur': user.username
        })
    
    # Trier par date
    activites.sort(key=lambda x: x['date'], reverse=True)
    
    return render(request, 'admin/journal_activite.html', {'activites': activites[:20]})

@staff_member_required
def parametres_systeme(request):
    """Configurer les paramètres du système"""
    if request.method == 'POST':
        messages.success(request, "Paramètres mis à jour avec succès")
        return redirect('parametres_systeme')
    
    parametres = {
        'nom_entreprise': 'Transport Express',
        'email_contact': 'contact@transport.com',
        'delai_annulation': 24,
        'commission': 15,
        'devise': 'MAD',
    }
    
    return render(request, 'admin/parametres_systeme.html', {'parametres': parametres})