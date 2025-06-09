# transport/views.py - Version corrigée pour les administrateurs
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime
import csv
from .models import Commande, Client, Transporteur, Adresse
from .forms import CommandeForm, AdresseForm, InscriptionForm, RapportForm

def index(request):
    return render(request, 'transport/index.html')

def inscription(request):
    if request.method == 'POST':
        form = InscriptionForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Inscription réussie! Bienvenue sur notre plateforme.')
            return redirect('index')
    else:
        form = InscriptionForm()
    return render(request, 'registration/inscription.html', {'form': form})

@require_http_methods(["GET", "POST"])
def logout_view(request):
    logout(request)
    messages.info(request, 'Vous avez été déconnecté avec succès.')
    return redirect('index')

@login_required
def liste_commandes(request):
    # Les administrateurs peuvent voir toutes les commandes
    if request.user.is_staff:
        commandes = Commande.objects.all().order_by('-date_creation')
        return render(request, 'transport/liste_commandes.html', {'commandes': commandes})
    
    # Les clients voient seulement leurs commandes
    try:
        client = request.user.client
        commandes = Commande.objects.filter(client=client).order_by('-date_creation')
    except Client.DoesNotExist:
        messages.error(request, 'Veuillez compléter votre profil client.')
        return redirect('index')
    
    return render(request, 'transport/liste_commandes.html', {'commandes': commandes})

@login_required
def creer_commande(request):
    # Les administrateurs ne peuvent pas créer de commandes directement
    if request.user.is_staff:
        messages.error(request, 'Les administrateurs ne peuvent pas créer de commandes. Veuillez utiliser un compte client.')
        return redirect('index')
    
    try:
        client = request.user.client
    except Client.DoesNotExist:
        messages.error(request, 'Veuillez compléter votre profil client.')
        return redirect('index')
    
    if request.method == 'POST':
        commande_form = CommandeForm(request.POST)
        adresse_enlevement_form = AdresseForm(request.POST, prefix='enlevement')
        adresse_livraison_form = AdresseForm(request.POST, prefix='livraison')
        
        if all([commande_form.is_valid(), adresse_enlevement_form.is_valid(), 
                adresse_livraison_form.is_valid()]):
            # Créer les adresses
            adresse_enlevement = adresse_enlevement_form.save()
            adresse_livraison = adresse_livraison_form.save()
            
            # Créer la commande
            commande = commande_form.save(commit=False)
            commande.client = client
            commande.adresse_enlevement = adresse_enlevement
            commande.adresse_livraison = adresse_livraison
            commande.save()
            
            messages.success(request, f'Commande #{commande.id} créée avec succès!')
            return redirect('suivre_commande', commande_id=commande.id)
    else:
        commande_form = CommandeForm()
        adresse_enlevement_form = AdresseForm(prefix='enlevement')
        adresse_livraison_form = AdresseForm(prefix='livraison')
    
    context = {
        'commande_form': commande_form,
        'adresse_enlevement_form': adresse_enlevement_form,
        'adresse_livraison_form': adresse_livraison_form,
    }
    return render(request, 'transport/creer_commande.html', context)

@login_required
def suivre_commande(request, commande_id):
    # Les administrateurs peuvent voir toutes les commandes
    if request.user.is_staff:
        commande = get_object_or_404(Commande, id=commande_id)
        return render(request, 'transport/suivre_commande.html', {'commande': commande})
    
    # Les clients ne peuvent voir que leurs propres commandes
    try:
        client = request.user.client
        commande = get_object_or_404(Commande, id=commande_id, client=client)
    except Client.DoesNotExist:
        messages.error(request, 'Veuillez compléter votre profil client.')
        return redirect('index')
    
    return render(request, 'transport/suivre_commande.html', {'commande': commande})

@login_required
def supprimer_commande(request, commande_id):
    # Les administrateurs peuvent supprimer n'importe quelle commande
    if request.user.is_staff:
        commande = get_object_or_404(Commande, id=commande_id)
    else:
        try:
            client = request.user.client
            commande = get_object_or_404(Commande, id=commande_id, client=client)
        except Client.DoesNotExist:
            messages.error(request, 'Veuillez compléter votre profil client.')
            return redirect('index')
    
    # Vérifier que la commande peut être supprimée
    if commande.statut in ['EN_TRANSIT', 'LIVREE']:
        messages.error(request, 'Cette commande ne peut pas être supprimée.')
        return redirect('liste_commandes')
    
    if request.method == 'POST':
        commande.statut = 'ANNULEE'
        commande.save()
        messages.success(request, f'Commande #{commande.id} annulée avec succès.')
        return redirect('liste_commandes')
    
    return render(request, 'transport/supprimer_commande.html', {'commande': commande})

@login_required
def generer_rapport(request):
    # Les administrateurs peuvent générer des rapports pour tous les clients
    if request.user.is_staff:
        if request.method == 'POST':
            form = RapportForm(request.POST)
            if form.is_valid():
                date_debut = form.cleaned_data['date_debut']
                date_fin = form.cleaned_data['date_fin']
                format_export = form.cleaned_data['format_export']
                
                # Récupérer toutes les commandes dans la période
                commandes = Commande.objects.filter(
                    date_creation__date__gte=date_debut,
                    date_creation__date__lte=date_fin
                ).order_by('-date_creation')
                
                if format_export == 'csv':
                    response = HttpResponse(content_type='text/csv')
                    response['Content-Disposition'] = f'attachment; filename="rapport_global_{date_debut}_{date_fin}.csv"'
                    
                    writer = csv.writer(response)
                    writer.writerow(['N° Commande', 'Client', 'Date', 'Type Marchandise', 'Poids (kg)', 
                                   'Adresse Enlèvement', 'Adresse Livraison', 'Statut'])
                    
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
                        'client': None,  # Pas de client spécifique pour l'admin
                        'total_commandes': commandes.count(),
                        'commandes_livrees': commandes.filter(statut='LIVREE').count(),
                        'commandes_en_cours': commandes.filter(statut__in=['EN_ATTENTE', 'AFFECTEE', 'EN_TRANSIT']).count(),
                        'commandes_annulees': commandes.filter(statut='ANNULEE').count(),
                    }
                    return render(request, 'transport/rapport_pdf.html', context)
        else:
            form = RapportForm()
        
        return render(request, 'transport/generer_rapport.html', {'form': form})
    
    # Pour les clients normaux
    try:
        client = request.user.client
    except Client.DoesNotExist:
        messages.error(request, 'Veuillez compléter votre profil client.')
        return redirect('index')
    
    if request.method == 'POST':
        form = RapportForm(request.POST)
        if form.is_valid():
            date_debut = form.cleaned_data['date_debut']
            date_fin = form.cleaned_data['date_fin']
            format_export = form.cleaned_data['format_export']
            
            commandes = Commande.objects.filter(
                client=client,
                date_creation__date__gte=date_debut,
                date_creation__date__lte=date_fin
            ).order_by('-date_creation')
            
            if format_export == 'csv':
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="rapport_commandes_{date_debut}_{date_fin}.csv"'
                
                writer = csv.writer(response)
                writer.writerow(['N° Commande', 'Date', 'Type Marchandise', 'Poids (kg)', 
                               'Adresse Enlèvement', 'Adresse Livraison', 'Statut'])
                
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
                    'commandes_en_cours': commandes.filter(statut__in=['EN_ATTENTE', 'AFFECTEE', 'EN_TRANSIT']).count(),
                    'commandes_annulees': commandes.filter(statut='ANNULEE').count(),
                }
                return render(request, 'transport/rapport_pdf.html', context)
    else:
        form = RapportForm()
    
    return render(request, 'transport/generer_rapport.html', {'form': form})