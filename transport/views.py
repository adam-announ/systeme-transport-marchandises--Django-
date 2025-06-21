from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from datetime import datetime, timedelta
import csv
from .models import Commande, Client, Transporteur, Adresse, SupportMessage, Notification
from .forms import CommandeForm, AdresseForm, InscriptionForm, RapportForm

def index(request):
    return render(request, 'transport/index.html')

def inscription(request):
    if request.method == 'POST':
        form = InscriptionForm(request.POST)
        if form.is_valid():
            user = form.save()  # InscriptionForm gère création User + profil Client/Transporteur
            login(request, user)
            messages.success(request, "Inscription réussie! Bienvenue sur notre plateforme.")
            return redirect('index')
    else:
        form = InscriptionForm()
    return render(request, 'registration/inscription.html', {'form': form})

@require_http_methods(["GET", "POST"])
def logout_view(request):
    logout(request)
    messages.info(request, "Vous avez été déconnecté avec succès.")
    return redirect('index')

@login_required
def liste_commandes(request):
    # Admin voit toutes les commandes
    if request.user.is_staff:
        commandes = Commande.objects.all().order_by('-date_creation')
    else:
        # Client voit seulement ses commandes
        try:
            client = request.user.client
        except Client.DoesNotExist:
            messages.error(request, "Veuillez compléter votre profil client.")
            return redirect('index')
        commandes = Commande.objects.filter(client=client).order_by('-date_creation')
    return render(request, 'transport/liste_commandes.html', {'commandes': commandes})

@login_required
def creer_commande(request):
    # Un administrateur ne crée pas de commande (doit passer par un compte client)
    if request.user.is_staff:
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
        if commande_form.is_valid() and adresse_enlevement_form.is_valid() and adresse_livraison_form.is_valid():
            # Créer les adresses
            adr_enlev = adresse_enlevement_form.save()
            adr_livr = adresse_livraison_form.save()
            # Créer la commande
            commande = commande_form.save(commit=False)
            commande.client = client
            commande.adresse_enlevement = adr_enlev
            commande.adresse_livraison = adr_livr
            commande.save()
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
    # Admin peut voir n'importe quelle commande
    if request.user.is_staff:
        commande = get_object_or_404(Commande, id=commande_id)
    else:
        # Client ne voit que sa propre commande
        try:
            client = request.user.client
            commande = get_object_or_404(Commande, id=commande_id, client=client)
        except Client.DoesNotExist:
            messages.error(request, "Veuillez compléter votre profil client.")
            return redirect('index')
    return render(request, 'transport/suivre_commande.html', {'commande': commande})

@login_required
def supprimer_commande(request, commande_id):
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
    # On empêche si déjà en transit ou livrée, et on pourrait ajouter une contrainte de délai d'annulation
    delai_h = 0
    try:
        param = ParametreSysteme.objects.get(nom='delai_annulation')
        delai_h = int(param.valeur)
    except:
        delai_h = 24  # défaut 24h si non configuré
    if commande.statut in ['EN_TRANSIT', 'LIVREE'] or (commande.date_creation < timezone.now() - timedelta(hours=delai_h)):
        messages.error(request, "Cette commande ne peut plus être annulée.")
        return redirect('liste_commandes')
    if request.method == 'POST':
        commande.statut = 'ANNULEE'
        commande.save()
        messages.success(request, f"Commande #{commande.id} annulée avec succès.")
        return redirect('liste_commandes')
    return render(request, 'transport/supprimer_commande.html', {'commande': commande})

@login_required
def generer_rapport(request):
    """Génération de rapport de commandes sur une période, en PDF ou CSV."""
    if request.user.is_staff:
        # Administrateur: rapport global sur tous les clients
        if request.method == 'POST':
            form = RapportForm(request.POST)
            if form.is_valid():
                date_debut = form.cleaned_data['date_debut']
                date_fin = form.cleaned_data['date_fin']
                format_export = form.cleaned_data['format_export']
                commandes = Commande.objects.filter(date_creation__date__gte=date_debut, date_creation__date__lte=date_fin).order_by('-date_creation')
                if format_export == 'csv':
                    response = HttpResponse(content_type='text/csv')
                    response['Content-Disposition'] = f'attachment; filename="rapport_global_{date_debut}_{date_fin}.csv"'
                    writer = csv.writer(response)
                    writer.writerow(['N° Commande', 'Client', 'Date', 'Type Marchandise', 'Poids (kg)', 'Adresse Enlèvement', 'Adresse Livraison', 'Statut'])
                    for commande in commandes:
                        writer.writerow([
                            commande.id,
                            commande.client.user.username,
                            commande.date_creation.strftime('%d/%m/%Y %H:%M'),
                            commande.type_marchandise,
                            commande.poids,
                            str(commande.adresse_enlevement),
                            str(commande.adresse_livraison),
                            commande.get_statut_display()
                        ])
                    return response
                else:
                    context = {
                        'commandes': commandes,
                        'date_debut': date_debut,
                        'date_fin': date_fin,
                        'client': None,
                        'total_commandes': commandes.count(),
                        'commandes_livrees': commandes.filter(statut='LIVREE').count(),
                        'commandes_en_cours': commandes.filter(statut__in=['EN_ATTENTE','AFFECTEE','EN_TRANSIT']).count(),
                        'commandes_annulees': commandes.filter(statut='ANNULEE').count(),
                    }
                    return render(request, 'transport/rapport_pdf.html', context)
        else:
            form = RapportForm()
        return render(request, 'transport/generer_rapport.html', {'form': form})
    # Pour un client normal: rapport de ses propres commandes
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
            commandes = Commande.objects.filter(client=client, date_creation__date__gte=date_debut, date_creation__date__lte=date_fin).order_by('-date_creation')
            if format_export == 'csv':
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="rapport_commandes_{date_debut}_{date_fin}.csv"'
                writer = csv.writer(response)
                writer.writerow(['N° Commande', 'Date', 'Type Marchandise', 'Poids (kg)', 'Adresse Enlèvement', 'Adresse Livraison', 'Statut'])
                for commande in commandes:
                    writer.writerow([
                        commande.id,
                        commande.date_creation.strftime('%d/%m/%Y %H:%M'),
                        commande.type_marchandise,
                        commande.poids,
                        str(commande.adresse_enlevement),
                        str(commande.adresse_livraison),
                        commande.get_statut_display()
                    ])
                return response
            else:
                context = {
                    'commandes': commandes,
                    'date_debut': date_debut,
                    'date_fin': date_fin,
                    'client': client,
                    'total_commandes': commandes.count(),
                    'commandes_livrees': commandes.filter(statut='LIVREE').count(),
                    'commandes_en_cours': commandes.filter(statut__in=['EN_ATTENTE','AFFECTEE','EN_TRANSIT']).count(),
                    'commandes_annulees': commandes.filter(statut='ANNULEE').count(),
                }
                return render(request, 'transport/rapport_pdf.html', context)
    else:
        form = RapportForm()
    return render(request, 'transport/generer_rapport.html', {'form': form})

@login_required
def messagerie_support(request):
    """Interface de messagerie support pour l'utilisateur (client ou transporteur)"""
    # Interdit aux admins d'utiliser cette vue (ils ont leur interface)
    if request.user.is_staff:
        return HttpResponseForbidden("Réservé aux utilisateurs non administrateurs.")
    # Récupérer la conversation de l'utilisateur courant avec le support (admins)
    messages_chain = SupportMessage.objects.filter(
        Q(sender=request.user, destinataire__is_staff=True) | 
        Q(sender__is_staff=True, destinataire=request.user)
    ).order_by('date_envoi')
    # Marquer comme lus tous les messages du support destinés à l'utilisateur
    SupportMessage.objects.filter(sender__is_staff=True, destinataire=request.user, lu=False).update(lu=True)
    if request.method == 'POST':
        contenu = request.POST.get('contenu')
        if contenu:
            # Envoyer le message du client/transporteur au support (on adresse au premier admin trouvé)
            admin_user = User.objects.filter(is_staff=True).first()
            if admin_user:
                SupportMessage.objects.create(sender=request.user, destinataire=admin_user, contenu=contenu)
                messages.success(request, "Votre message a été envoyé au support.")
            else:
                messages.error(request, "Aucun administrateur disponible pour recevoir le message.")
            return redirect('messagerie_support')
    return render(request, 'transport/messagerie_support.html', {'messages': messages_chain})
