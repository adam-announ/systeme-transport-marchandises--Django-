from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Client, Commande, Transporteur, Incident, Notification, SupportMessage

@staff_member_required
def dashboard_admin(request):
    """Tableau de bord principal de l'administrateur"""
    context = {
        'total_users': User.objects.count(),
        'total_clients': Client.objects.count(),
        'total_transporteurs': Transporteur.objects.count(),
        'transporteurs_disponibles': Transporteur.objects.filter(disponible=True).count(),
        'commandes_jour': Commande.objects.filter(date_creation__date=timezone.now().date()).count(),
        'commandes_attente': Commande.objects.filter(statut='EN_ATTENTE').count(),
        # Statistiques supplémentaires
        'livraisons_24h': Commande.objects.filter(statut='LIVREE', date_creation__gte=timezone.now()-timedelta(days=1)).count(),
        'incidents_ouverts': Incident.objects.filter(resolu=False).count(),
    }
    return render(request, 'admin/dashboard.html', context)

@staff_member_required
def gestion_utilisateurs(request):
    """Gérer les utilisateurs du système (activation, rôles, etc.)"""
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
    users = User.objects.all().select_related('client', 'transporteur').order_by('-date_joined')
    return render(request, 'admin/gestion_utilisateurs.html', {'users': users})

@staff_member_required
def gestion_roles(request):
    """Gérer les rôles et permissions (groupes Django)"""
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
    return render(request, 'admin/gestion_roles.html', {'groups': groups, 'users': users})

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
    # Derniers utilisateurs inscrits
    users_recents = User.objects.order_by('-date_joined')[:5]
    for user in users_recents:
        activites.append({
            'date': user.date_joined,
            'type': 'Inscription',
            'description': f"Nouvel utilisateur: {user.username}",
            'utilisateur': user.username
        })
    # Trier par date décroissante
    activites.sort(key=lambda x: x['date'], reverse=True)
    return render(request, 'admin/journal_activite.html', {'activites': activites[:20]})

@staff_member_required
def parametres_systeme(request):
    """Configurer les paramètres du système (formulaire de paramètres globaux)"""
    params = {p.nom: p for p in  ParametreSysteme.objects.all()}  # Dictionnaire des paramètres existants
    if request.method == 'POST':
        # Pour chaque paramètre modifiable, mettre à jour sa valeur
        for champ, valeur in request.POST.items():
            if champ in params:
                params[champ].valeur = valeur
                params[champ].save()
        messages.success(request, "Paramètres mis à jour avec succès.")
        return redirect('parametres_systeme')
    # Passer les paramètres actuels au template (pour pré-remplir le formulaire)
    return render(request, 'admin/parametres_systeme.html', {'parametres': params})

@staff_member_required
def envoyer_notification_globale(request):
    """Envoyer une notification globale à tous les utilisateurs ou à un sous-groupe"""
    if request.method == 'POST':
        titre = request.POST.get('titre')
        message = request.POST.get('message')
        cible = request.POST.get('cible')  # 'all', 'clients' ou 'transporteurs'
        if titre and message and cible:
            # Déterminer la liste des destinataires selon la cible
            if cible == 'all':
                users = User.objects.filter(is_active=True)
            elif cible == 'clients':
                users = User.objects.filter(is_active=True, client__isnull=False)
            elif cible == 'transporteurs':
                users = User.objects.filter(is_active=True, transporteur__isnull=False)
            else:
                users = []
            # Créer une notification pour chaque utilisateur ciblé
            for user in users:
                Notification.objects.create(
                    destinataire=user,
                    transporteur=None,
                    type='SYSTEME',
                    titre=titre,
                    message=message,
                    priorite='HAUTE' if cible != 'clients' and cible != 'transporteurs' else 'NORMALE'
                )
            messages.success(request, f"Notification envoyée à {users.count()} utilisateurs.")
            return redirect('envoyer_notification_globale')
    return render(request, 'admin/envoyer_notification.html')

@staff_member_required
def support_clients(request):
    """Liste des conversations de support en cours (par utilisateur)"""
    # On récupère tous les utilisateurs non staff qui ont envoyé au moins un message
    convo_users = User.objects.filter(is_staff=False, messages_envoyes__destinataire__is_staff=True).distinct()
    # Compter les messages non lus de chaque
    conversations = []
    for user in convo_users:
        non_lus = SupportMessage.objects.filter(sender=user, destinataire__is_staff=True, lu=False).count()
        last_msg = SupportMessage.objects.filter(Q(sender=user)|Q(destinataire=user), destinataire__is_staff=True).order_by('-date_envoi').first()
        conversations.append({
            'user': user,
            'non_lus': non_lus,
            'dernier_message': last_msg
        })
    return render(request, 'admin/support_clients.html', {'conversations': conversations})

@staff_member_required
def support_conversation(request, user_id):
    """Conversation de support entre un client/transporteur et l'admin"""
    user = get_object_or_404(User, id=user_id, is_staff=False)
    # Récupérer tous les messages échangés avec ce user (dans les deux sens)
    messages_chain = SupportMessage.objects.filter(
        (Q(sender=user) & Q(destinataire__is_staff=True)) | 
        (Q(sender__is_staff=True) & Q(destinataire=user))
    ).order_by('date_envoi')
    # Marquer comme lus tous les messages de ce user destinés à l'admin
    SupportMessage.objects.filter(sender=user, destinataire__is_staff=True, lu=False).update(lu=True)
    if request.method == 'POST':
        contenu = request.POST.get('contenu')
        if contenu:
            # L'admin envoie un message au user
            SupportMessage.objects.create(sender=request.user, destinataire=user, contenu=contenu)
            messages.success(request, "Message envoyé à l'utilisateur.")
            return redirect('support_conversation', user_id=user.id)
    return render(request, 'admin/support_conversation.html', {'interlocuteur': user, 'messages': messages_chain})
