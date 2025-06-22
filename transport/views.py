from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Q, Count
from django.contrib.auth.models import User
import csv
from .models import (
    Commande, Client, Transporteur, Adresse, SupportMessage, 
    Notification, ParametreSysteme, MissionTransporteur
)
from .forms import CommandeForm, AdresseForm, InscriptionForm, RapportForm

def index(request):
    """Page d'accueil"""
    if request.user.is_authenticated:
        # Redirection selon le profil
        if hasattr(request.user, 'client'):
            return redirect('liste_commandes')
        elif hasattr(request.user, 'transporteur'):
            return redirect('dashboard_transporteur')
        elif request.user.is_staff:
            return redirect('dashboard_planificateur')
    
    # Utiliser le template index.html existant
    return render(request, 'transport/index.html')

def inscription(request):
    """Inscription d'un nouvel utilisateur (client ou transporteur)"""
    if request.method == 'POST':
        form = InscriptionForm(request.POST)
        if form.is_valid():
            user = form.save()  # InscriptionForm gère création User + profil Client/Transporteur
            login(request, user)
            messages.success(request, "Inscription réussie! Bienvenue sur notre plateforme.")
            
            # Rediriger selon le type de compte
            if form.cleaned_data['type_compte'] == 'client':
                return redirect('liste_commandes')
            else:
                return redirect('dashboard_transporteur')
    else:
        form = InscriptionForm()
    return render(request, 'registration/inscription.html', {'form': form})

@require_http_methods(["GET", "POST"])
def logout_view(request):
    """Déconnexion de l'utilisateur"""
    logout(request)
    messages.info(request, "Vous avez été déconnecté avec succès.")
    return redirect('index')

@login_required
def liste_commandes(request):
    """Liste des commandes - Admin voit tout, client voit les siennes"""
    if request.user.is_staff:
        # Admin voit toutes les commandes
        commandes = Commande.objects.all().select_related(
            'client', 'transporteur', 'adresse_enlevement', 'adresse_livraison'
        ).order_by('-date_creation')
    else:
        # Client voit seulement ses commandes
        try:
            client = request.user.client
            commandes = Commande.objects.filter(client=client).select_related(
                'transporteur', 'adresse_enlevement', 'adresse_livraison'
            ).order_by('-date_creation')
        except Client.DoesNotExist:
            messages.error(request, "Veuillez compléter votre profil client.")
            return redirect('index')
    
    return render(request, 'transport/liste_commandes.html', {'commandes': commandes})

@login_required
def creer_commande(request):
    """Création d'une nouvelle commande par un client"""
    # Vérifier que c'est bien un client
    if request.user.is_staff and not hasattr(request.user, 'client'):
        messages.error(request, "Les administrateurs ne peuvent pas créer de commandes. Utilisez un compte client.")
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
            
            # Créer les adresses
            adr_enlev = adresse_enlevement_form.save()
            adr_livr = adresse_livraison_form.save()
            
            # Créer la commande
            commande = commande_form.save(commit=False)
            commande.client = client
            commande.adresse_enlevement = adr_enlev
            commande.adresse_livraison = adr_livr
            commande.save()
            
            # Créer une notification pour les planificateurs
            for user in User.objects.filter(is_staff=True):
                Notification.objects.create(
                    destinataire=user,
                    type='MISSION',
                    titre='Nouvelle commande à affecter',
                    message=f'Commande #{commande.id} - {commande.type_marchandise} ({commande.poids}kg)',
                    commande=commande,
                    priorite='NORMALE' if commande.priorite == 0 else 'HAUTE'
                )
            
            messages.success(request, f"Commande #{commande.id} créée avec succès!")
            return redirect('suivre_commande', commande_id=commande.id)
    else:
        commande_form = CommandeForm()
        adresse_enlevement_form = AdresseForm(prefix='enlevement')
        adresse_livraison_form = AdresseForm(prefix='livraison')
    
    return render(request, 'transport/creer_commande.html', {
        'commande_form': commande_form,
        'adresse_enlevement_form': adresse_enlevement_form,
        'adresse_livraison_form': adresse_livraison_form
    })

@login_required
def suivre_commande(request, commande_id):
    """Suivi détaillé d'une commande"""
    # Admin peut voir n'importe quelle commande
    if request.user.is_staff:
        commande = get_object_or_404(
            Commande.objects.select_related(
                'client', 'transporteur', 'adresse_enlevement', 'adresse_livraison'
            ), 
            id=commande_id
        )
    else:
        # Client ne voit que sa propre commande
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
            messages.error(request, "Veuillez compléter votre profil client.")
            return redirect('index')
    
    # Récupérer la mission associée si elle existe
    mission = None
    if commande.transporteur:
        try:
            mission = MissionTransporteur.objects.get(commande=commande)
        except MissionTransporteur.DoesNotExist:
            pass
    
    context = {
        'commande': commande,
        'mission': mission,
    }
    
    return render(request, 'transport/suivre_commande.html', context)

@login_required
def supprimer_commande(request, commande_id):
    """Annulation d'une commande"""
    # Admin peut annuler n'importe quelle commande
    if request.user.is_staff:
        commande = get_object_or_404(Commande, id=commande_id)
    else:
        try:
            client = request.user.client
            commande = get_object_or_404(Commande, id=commande_id, client=client)
        except Client.DoesNotExist:
            messages.error(request, "Veuillez compléter votre profil client.")
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
        messages.error(request, "Cette commande ne peut plus être annulée car elle est déjà en cours de livraison.")
        return redirect('liste_commandes')
    
    # Vérifier le délai d'annulation
    if commande.date_creation < timezone.now() - timedelta(hours=delai_h):
        messages.error(request, f"Cette commande ne peut plus être annulée (délai de {delai_h}h dépassé).")
        return redirect('liste_commandes')
    
    if request.method == 'POST':
        # Annuler la commande
        commande.statut = 'ANNULEE'
        commande.save()
        
        # Si une mission était assignée, l'annuler aussi
        try:
            mission = MissionTransporteur.objects.get(commande=commande)
            mission.statut = 'ANNULEE'
            mission.save()
            
            # Notifier le transporteur
            Notification.objects.create(
                destinataire=mission.transporteur.user,
                type='STATUT',
                titre='Mission annulée',
                message=f'La commande #{commande.id} a été annulée par le client.',
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
    """Génération de rapport de commandes sur une période, en PDF ou CSV"""
    # Déterminer si c'est un admin ou un client
    is_admin = request.user.is_staff
    client = None
    
    if not is_admin:
        try:
            client = request.user.client
        except Client.DoesNotExist:
            messages.error(request, "Veuillez compléter votre profil client pour générer un rapport.")
            return redirect('index')
    
    if request.method == 'POST':
        form = RapportForm(request.POST)
        if form.is_valid():
            date_debut = form.cleaned_data['date_debut']
            date_fin = form.cleaned_data['date_fin']
            format_export = form.cleaned_data['format_export']
            
            # Filtrer les commandes selon le profil
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
                # Génération CSV
                response = HttpResponse(content_type='text/csv')
                filename = f'rapport_{"global" if is_admin else "commandes"}_{date_debut}_{date_fin}.csv'
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                
                writer = csv.writer(response)
                # En-têtes
                headers = ['N° Commande', 'Date', 'Type Marchandise', 'Poids (kg)', 
                          'Adresse Enlèvement', 'Adresse Livraison', 'Statut']
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
                        f"{commande.adresse_enlevement.ville}",
                        f"{commande.adresse_livraison.ville}",
                        commande.get_statut_display()
                    ]
                    if is_admin:
                        row.insert(1, commande.client.user.username)
                    
                    writer.writerow(row)
                
                return response
            else:
                # Génération PDF (affichage HTML pour impression)
                # Calculer les statistiques
                stats = {
                    'total_commandes': commandes.count(),
                    'commandes_livrees': commandes.filter(statut='LIVREE').count(),
                    'commandes_en_cours': commandes.filter(
                        statut__in=['EN_ATTENTE', 'AFFECTEE', 'EN_TRANSIT']
                    ).count(),
                    'commandes_annulees': commandes.filter(statut='ANNULEE').count(),
                }
                
                # Calculer le poids total
                poids_total = sum(c.poids for c in commandes)
                
                context = {
                    'commandes': commandes,
                    'date_debut': date_debut,
                    'date_fin': date_fin,
                    'client': client,
                    'is_admin': is_admin,
                    'stats': stats,
                    'poids_total': poids_total,
                }
                
                return render(request, 'transport/rapport_pdf.html', context)
    else:
        form = RapportForm()
    
    return render(request, 'transport/generer_rapport.html', {
        'form': form,
        'is_admin': is_admin
    })

@login_required
def messagerie_support(request):
    """Interface de messagerie support pour l'utilisateur (client ou transporteur)"""
    # Interdit aux admins d'utiliser cette vue (ils ont leur interface)
    if request.user.is_staff:
        return redirect('support_clients')
    
    # Récupérer la conversation de l'utilisateur courant avec le support
    messages_chain = SupportMessage.objects.filter(
        Q(sender=request.user, destinataire__is_staff=True) | 
        Q(sender__is_staff=True, destinataire=request.user)
    ).order_by('date_envoi')
    
    # Marquer comme lus tous les messages du support destinés à l'utilisateur
    SupportMessage.objects.filter(
        sender__is_staff=True, 
        destinataire=request.user, 
        lu=False
    ).update(lu=True)
    
    if request.method == 'POST':
        contenu = request.POST.get('contenu')
        if contenu:
            # Envoyer le message du client/transporteur au support
            # On adresse au premier admin trouvé
            admin_user = User.objects.filter(is_staff=True).first()
            if admin_user:
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
                
                messages.success(request, "Votre message a été envoyé au support.")
            else:
                messages.error(request, "Aucun administrateur disponible pour recevoir le message.")
            
            return redirect('messagerie_support')
    
    return render(request, 'transport/messagerie_support.html', {
        'messages': messages_chain
    })