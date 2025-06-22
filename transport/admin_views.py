# transport/admin_views.py - Version corrigée avec fonctionnalités complètes

from datetime import timedelta
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User, Group
from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm
from django.core.paginator import Paginator

from .models import (
    Client, Commande, Transporteur, Incident,
    Notification, SupportMessage, ParametreSysteme
)
from .forms import InscriptionForm

@staff_member_required
def dashboard_admin(request):
    """Tableau de bord principal de l'administrateur"""
    # Statistiques générales
    stats = {
        'total_users': User.objects.count(),
        'total_clients': Client.objects.count(),
        'total_transporteurs': Transporteur.objects.count(),
        'total_planificateurs': User.objects.filter(is_staff=True, is_superuser=False).count(),
        'transporteurs_disponibles': Transporteur.objects.filter(disponible=True).count(),
        'commandes_jour': Commande.objects.filter(date_creation__date=timezone.now().date()).count(),
        'commandes_attente': Commande.objects.filter(statut='EN_ATTENTE').count(),
        'livraisons_24h': Commande.objects.filter(
            statut='LIVREE', 
            date_creation__gte=timezone.now() - timedelta(days=1)
        ).count(),
        'incidents_ouverts': Incident.objects.filter(resolu=False).count(),
    }
    
    # Activités récentes
    activites_recentes = []
    
    # Dernières inscriptions
    nouveaux_users = User.objects.order_by('-date_joined')[:5]
    for user in nouveaux_users:
        activites_recentes.append({
            'type': 'inscription',
            'description': f'Nouvel utilisateur: {user.username}',
            'date': user.date_joined,
            'user': user.username
        })
    
    # Dernières commandes
    nouvelles_commandes = Commande.objects.order_by('-date_creation')[:5]
    for commande in nouvelles_commandes:
        activites_recentes.append({
            'type': 'commande',
            'description': f'Commande #{commande.id} créée par {commande.client.user.username}',
            'date': commande.date_creation,
            'user': commande.client.user.username
        })
    
    # Trier par date décroissante
    activites_recentes.sort(key=lambda x: x['date'], reverse=True)
    activites_recentes = activites_recentes[:10]
    
    # Messages support non lus
    messages_support = SupportMessage.objects.filter(
        sender__is_staff=False, 
        destinataire__is_staff=True, 
        lu=False
    ).count()
    
    context = {
        'stats': stats,
        'activites_recentes': activites_recentes,
        'messages_support': messages_support,
    }
    
    return render(request, 'admin/dashboard.html', context)

@staff_member_required
def creer_compte(request):
    """Créer un nouveau compte utilisateur (Client, Transporteur, Planificateur)"""
    if request.method == 'POST':
        type_compte = request.POST.get('type_compte')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        
        # Vérifications de base
        if not all([type_compte, username, email, password]):
            messages.error(request, "Tous les champs obligatoires doivent être remplis.")
            return render(request, 'admin/creer_compte.html')
        
        # Vérifier si l'utilisateur existe déjà
        if User.objects.filter(username=username).exists():
            messages.error(request, "Ce nom d'utilisateur existe déjà.")
            return render(request, 'admin/creer_compte.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "Cet email est déjà utilisé.")
            return render(request, 'admin/creer_compte.html')
        
        try:
            # Créer l'utilisateur
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            if type_compte == 'client':
                # Créer le profil client
                telephone = request.POST.get('telephone', '')
                adresse = request.POST.get('adresse', '')
                
                Client.objects.create(
                    user=user,
                    telephone=telephone,
                    adresse=adresse
                )
                messages.success(request, f"Compte client créé pour {username}")
                
            elif type_compte == 'transporteur':
                # Créer le profil transporteur
                matricule = request.POST.get('matricule', '')
                type_vehicule = request.POST.get('type_vehicule', '')
                capacite_charge = request.POST.get('capacite_charge', 0)
                
                if not matricule or not type_vehicule or not capacite_charge:
                    user.delete()
                    messages.error(request, "Tous les champs transporteur sont obligatoires.")
                    return render(request, 'admin/creer_compte.html')
                
                Transporteur.objects.create(
                    user=user,
                    matricule=matricule,
                    type_vehicule=type_vehicule,
                    capacite_charge=float(capacite_charge)
                )
                messages.success(request, f"Compte transporteur créé pour {username}")
                
            elif type_compte == 'planificateur':
                # Donner les droits staff
                user.is_staff = True
                user.save()
                
                # Ajouter au groupe planificateurs s'il existe
                try:
                    group = Group.objects.get(name='Planificateurs')
                    user.groups.add(group)
                except Group.DoesNotExist:
                    # Créer le groupe s'il n'existe pas
                    group = Group.objects.create(name='Planificateurs')
                    user.groups.add(group)
                
                messages.success(request, f"Compte planificateur créé pour {username}")
            
            # Envoyer une notification de bienvenue
            Notification.objects.create(
                destinataire=user,
                type='SYSTEME',
                titre='Bienvenue sur TransportPro',
                message=f'Votre compte {type_compte} a été créé par un administrateur.',
                priorite='NORMALE'
            )
            
            return redirect('gestion_utilisateurs')
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la création du compte: {str(e)}")
    
    return render(request, 'admin/creer_compte.html')

@staff_member_required
def gestion_utilisateurs(request):
    """Gérer les utilisateurs avec pagination et filtres"""
    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        
        if user_id:
            user = get_object_or_404(User, id=user_id)
            
            if action == 'toggle_active':
                user.is_active = not user.is_active
                user.save()
                status = "activé" if user.is_active else "désactivé"
                messages.success(request, f"Utilisateur {user.username} {status}")
                
            elif action == 'make_staff':
                user.is_staff = True
                user.save()
                messages.success(request, f"{user.username} est maintenant planificateur")
                
            elif action == 'remove_staff':
                if user != request.user and not user.is_superuser:
                    user.is_staff = False
                    user.save()
                    messages.success(request, f"{user.username} n'est plus planificateur")
                else:
                    messages.error(request, "Impossible de retirer les droits à ce compte")
                    
            elif action == 'delete_user':
                if user != request.user and not user.is_superuser:
                    username = user.username
                    user.delete()
                    messages.success(request, f"Utilisateur {username} supprimé")
                else:
                    messages.error(request, "Impossible de supprimer ce compte")
    
    # Filtres
    user_type = request.GET.get('type', 'all')
    search = request.GET.get('search', '')
    
    users = User.objects.all().order_by('-date_joined')
    
    # Appliquer les filtres
    if user_type == 'clients':
        users = users.filter(client__isnull=False)
    elif user_type == 'transporteurs':
        users = users.filter(transporteur__isnull=False)
    elif user_type == 'planificateurs':
        users = users.filter(is_staff=True, is_superuser=False)
    elif user_type == 'admins':
        users = users.filter(is_superuser=True)
    
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'user_type': user_type,
        'search': search,
        'total_users': users.count(),
    }
    
    return render(request, 'admin/gestion_utilisateurs.html', context)

@staff_member_required
def gestion_roles(request):
    """Gérer les rôles et groupes"""
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
            user = User.objects.filter(id=user_id).first()
            group = Group.objects.filter(id=group_id).first()
            
            if user and group:
                user.groups.add(group)
                messages.success(request, f"{user.username} ajouté au groupe {group.name}")
                
        elif action == 'remove_user_from_group':
            user_id = request.POST.get('user_id')
            group_id = request.POST.get('group_id')
            user = User.objects.filter(id=user_id).first()
            group = Group.objects.filter(id=group_id).first()
            
            if user and group:
                user.groups.remove(group)
                messages.success(request, f"{user.username} retiré du groupe {group.name}")
    
    groups = Group.objects.all().prefetch_related('user_set')
    users = User.objects.all().order_by('username')
    
    context = {
        'groups': groups,
        'users': users,
    }
    
    return render(request, 'admin/gestion_roles.html', context)

@staff_member_required
def journal_activite(request):
    """Journal d'activité système avec filtres"""
    # Créer des entrées d'activité depuis différentes sources
    activites = []
    
    # Activités des commandes
    for commande in Commande.objects.order_by('-date_creation')[:20]:
        activites.append({
            'date': commande.date_creation,
            'type': 'Commande',
            'description': f"Commande #{commande.id} créée par {commande.client.user.username}",
            'utilisateur': commande.client.user,
            'details': f"Type: {commande.type_marchandise}, Poids: {commande.poids}kg"
        })
    
    # Activités des inscriptions
    for user in User.objects.order_by('-date_joined')[:10]:
        type_user = 'Admin' if user.is_superuser else ('Staff' if user.is_staff else 'Client')
        activites.append({
            'date': user.date_joined,
            'type': 'Inscription',
            'description': f"Nouvel utilisateur {type_user}: {user.username}",
            'utilisateur': user,
            'details': f"Email: {user.email}"
        })
    
    # Activités des incidents
    for incident in Incident.objects.order_by('-date_signalement')[:10]:
        activites.append({
            'date': incident.date_signalement,
            'type': 'Incident',
            'description': f"Incident {incident.get_type_display()} signalé",
            'utilisateur': incident.transporteur.user,
            'details': incident.description[:100] + '...' if len(incident.description) > 100 else incident.description
        })
    
    # Trier par date décroissante
    activites.sort(key=lambda x: x['date'], reverse=True)
    
    # Filtrage par type
    type_filter = request.GET.get('type')
    if type_filter:
        activites = [a for a in activites if a['type'] == type_filter]
    
    # Pagination
    paginator = Paginator(activites, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Types disponibles pour le filtre
    types_disponibles = list(set([a['type'] for a in activites]))
    
    context = {
        'page_obj': page_obj,
        'type_filter': type_filter,
        'types_disponibles': types_disponibles,
    }
    
    return render(request, 'admin/journal_activite.html', context)

@staff_member_required
def parametres_systeme(request):
    """Modifier les paramètres système"""
    if request.method == 'POST':
        # Récupérer tous les paramètres du formulaire
        for key, value in request.POST.items():
            if key != 'csrfmiddlewaretoken':
                param, created = ParametreSysteme.objects.get_or_create(
                    nom=key,
                    defaults={'valeur': value, 'type': 'string'}
                )
                if not created:
                    param.valeur = value
                    param.save()
        
        messages.success(request, "Paramètres mis à jour avec succès.")
        return redirect('parametres_systeme')
    
    # Paramètres par défaut
    parametres_defaut = {
        'nom_entreprise': 'TransportPro',
        'email_contact': 'contact@transportpro.ma',
        'telephone_contact': '+212 600 000 000',
        'delai_annulation': '24',
        'commission': '10.0',
        'devise': 'MAD',
        'temps_max_livraison': '48',
        'rayon_recherche_transporteur': '50',
        'prix_base_livraison': '50',
        'prix_par_kg': '2',
        'prix_par_km': '1.5',
    }
    
    # Récupérer les paramètres existants
    parametres = {}
    for param in ParametreSysteme.objects.all():
        parametres[param.nom] = param.valeur
    
    # Ajouter les paramètres manquants avec leurs valeurs par défaut
    for nom, valeur_defaut in parametres_defaut.items():
        if nom not in parametres:
            parametres[nom] = valeur_defaut
    
    context = {
        'parametres': parametres,
    }
    
    return render(request, 'admin/parametres_systeme.html', context)

@staff_member_required
def envoyer_notification_globale(request):
    """Envoyer une notification à tous les utilisateurs"""
    if request.method == 'POST':
        titre = request.POST.get('titre')
        message = request.POST.get('message')
        cible = request.POST.get('cible')
        priorite = request.POST.get('priorite', 'NORMALE')
        
        if titre and message and cible:
            # Déterminer les destinataires
            if cible == 'all':
                users = User.objects.filter(is_active=True)
            elif cible == 'clients':
                users = User.objects.filter(is_active=True, client__isnull=False)
            elif cible == 'transporteurs':
                users = User.objects.filter(is_active=True, transporteur__isnull=False)
            elif cible == 'planificateurs':
                users = User.objects.filter(is_active=True, is_staff=True, is_superuser=False)
            else:
                users = User.objects.none()
            
            # Créer les notifications
            notifications_creees = 0
            for user in users:
                Notification.objects.create(
                    destinataire=user,
                    type='SYSTEME',
                    titre=titre,
                    message=message,
                    priorite=priorite
                )
                notifications_creees += 1
            
            messages.success(request, f"Notification envoyée à {notifications_creees} utilisateurs.")
            return redirect('envoyer_notification_globale')
    
    context = {
        'total_users': User.objects.filter(is_active=True).count(),
        'total_clients': Client.objects.filter(user__is_active=True).count(),
        'total_transporteurs': Transporteur.objects.filter(user__is_active=True).count(),
        'total_planificateurs': User.objects.filter(is_active=True, is_staff=True, is_superuser=False).count(),
    }
    
    return render(request, 'admin/envoyer_notification.html', context)

@staff_member_required
def support_clients(request):
    """Interface support pour les administrateurs"""
    # Grouper les conversations par utilisateur
    conversations = []
    
    # Récupérer tous les utilisateurs qui ont envoyé des messages
    users_with_messages = User.objects.filter(
        messages_envoyes__destinataire__is_staff=True
    ).distinct()
    
    for user in users_with_messages:
        # Compter les messages non lus de cet utilisateur
        non_lus = SupportMessage.objects.filter(
            sender=user,
            destinataire__is_staff=True,
            lu=False
        ).count()
        
        # Dernier message de cette conversation
        dernier_message = SupportMessage.objects.filter(
            Q(sender=user, destinataire__is_staff=True) |
            Q(sender__is_staff=True, destinataire=user)
        ).order_by('-date_envoi').first()
        
        conversations.append({
            'user': user,
            'non_lus': non_lus,
            'dernier_message': dernier_message,
            'priorite': 'haute' if non_lus > 3 else 'normale'
        })
    
    # Trier par priorité et date du dernier message
    conversations.sort(key=lambda x: (
        x['priorite'] == 'haute',
        x['dernier_message'].date_envoi if x['dernier_message'] else timezone.now()
    ), reverse=True)
    
    context = {
        'conversations': conversations,
        'total_non_lus': sum(c['non_lus'] for c in conversations),
    }
    
    return render(request, 'admin/support_clients.html', context)

@staff_member_required
def support_conversation(request, user_id):
    """Conversation support avec un utilisateur"""
    user = get_object_or_404(User, id=user_id, is_staff=False)
    
    # Récupérer tous les messages de cette conversation
    messages_chain = SupportMessage.objects.filter(
        Q(sender=user, destinataire__is_staff=True) |
        Q(sender__is_staff=True, destinataire=user)
    ).order_by('date_envoi')
    
    # Marquer comme lus les messages de l'utilisateur
    SupportMessage.objects.filter(
        sender=user,
        destinataire__is_staff=True,
        lu=False
    ).update(lu=True)
    
    if request.method == 'POST':
        contenu = request.POST.get('contenu')
        if contenu:
            # Créer la réponse
            SupportMessage.objects.create(
                sender=request.user,
                destinataire=user,
                contenu=contenu
            )
            
            # Notifier l'utilisateur
            Notification.objects.create(
                destinataire=user,
                type='SYSTEME',
                titre='Réponse du support',
                message='Vous avez reçu une réponse à votre demande de support.',
                priorite='NORMALE'
            )
            
            messages.success(request, "Réponse envoyée.")
            return redirect('support_conversation', user_id=user.id)
    
    # Informations sur l'utilisateur
    user_info = {
        'type': 'Client' if hasattr(user, 'client') else ('Transporteur' if hasattr(user, 'transporteur') else 'Utilisateur'),
        'date_inscription': user.date_joined,
        'derniere_connexion': user.last_login,
        'actif': user.is_active,
    }
    
    # Statistiques de l'utilisateur
    if hasattr(user, 'client'):
        user_info['commandes'] = Commande.objects.filter(client=user.client).count()
    elif hasattr(user, 'transporteur'):
        user_info['missions'] = user.transporteur.missiontransporteur_set.count()
    
    context = {
        'interlocuteur': user,
        'messages': messages_chain,
        'user_info': user_info,
    }
    
    return render(request, 'admin/support_conversation.html', context)

@staff_member_required
def statistiques_avancees(request):
    """Statistiques avancées et rapports"""
    # Période (par défaut 30 derniers jours)
    from datetime import datetime, timedelta
    
    periode = request.GET.get('periode', '30')
    try:
        jours = int(periode)
    except:
        jours = 30
    
    date_debut = timezone.now() - timedelta(days=jours)
    
    # Statistiques des commandes
    commandes_stats = {
        'total': Commande.objects.filter(date_creation__gte=date_debut).count(),
        'livrees': Commande.objects.filter(date_creation__gte=date_debut, statut='LIVREE').count(),
        'en_cours': Commande.objects.filter(date_creation__gte=date_debut, statut__in=['EN_ATTENTE', 'AFFECTEE', 'EN_TRANSIT']).count(),
        'annulees': Commande.objects.filter(date_creation__gte=date_debut, statut='ANNULEE').count(),
    }
    
    # Taux de réussite
    if commandes_stats['total'] > 0:
        commandes_stats['taux_reussite'] = round((commandes_stats['livrees'] / commandes_stats['total']) * 100, 1)
    else:
        commandes_stats['taux_reussite'] = 0
    
    # Statistiques des transporteurs
    transporteurs_stats = {
        'total': Transporteur.objects.count(),
        'actifs': Transporteur.objects.filter(disponible=True).count(),
        'en_mission': Transporteur.objects.filter(missiontransporteur__statut='EN_COURS').distinct().count(),
    }
    
    # Évolution quotidienne des commandes
    evolution_commandes = []
    for i in range(jours):
        date = (timezone.now() - timedelta(days=i)).date()
        count = Commande.objects.filter(date_creation__date=date).count()
        evolution_commandes.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': count
        })
    
    evolution_commandes.reverse()
    
    # Top transporteurs
    top_transporteurs = Transporteur.objects.annotate(
        missions_count=Count('missiontransporteur')
    ).order_by('-missions_count')[:10]
    
    context = {
        'periode': periode,
        'date_debut': date_debut,
        'commandes_stats': commandes_stats,
        'transporteurs_stats': transporteurs_stats,
        'evolution_commandes': evolution_commandes,
        'top_transporteurs': top_transporteurs,
    }
    
    return render(request, 'admin/statistiques_avancees.html', context)