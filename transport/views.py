# transport/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Commande, Client, Transporteur, Adresse
from .forms import CommandeForm

def index(request):
    return render(request, 'transport/index.html')

@login_required
def liste_commandes(request):
    if hasattr(request.user, 'client'):
        commandes = Commande.objects.filter(client=request.user.client)
    else:
        commandes = Commande.objects.all()
    return render(request, 'transport/liste_commandes.html', {'commandes': commandes})

@login_required
def creer_commande(request):
    if request.method == 'POST':
        form = CommandeForm(request.POST)
        if form.is_valid():
            commande = form.save(commit=False)
            commande.client = request.user.client
            commande.save()
            messages.success(request, 'Commande créée avec succès!')
            return redirect('liste_commandes')
    else:
        form = CommandeForm()
    return render(request, 'transport/creer_commande.html', {'form': form})

@login_required
def suivre_commande(request, commande_id):
    commande = get_object_or_404(Commande, id=commande_id)
    return render(request, 'transport/suivre_commande.html', {'commande': commande})

def optimiser_itineraire(request):
    # Logique d'optimisation simple
    commandes_en_attente = Commande.objects.filter(statut='EN_ATTENTE')
    transporteurs_disponibles = Transporteur.objects.filter(disponible=True)
    
    return render(request, 'transport/optimiser_itineraire.html', {
        'commandes': commandes_en_attente,
        'transporteurs': transporteurs_disponibles
    })