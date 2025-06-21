from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.utils import timezone
from django.db.models import Q
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import json
from datetime import datetime
from .models import Transporteur, Commande, BonLivraison, Notification, MissionTransporteur, Incident
from .forms import StatutLivraisonForm, IncidentForm

@login_required
def dashboard_transporteur(request):
    """Tableau de bord du transporteur"""
    try:
        transporteur = request.user.transporteur
    except Transporteur.DoesNotExist:
        messages.error(request, "Vous n'êtes pas enregistré comme transporteur.")
        return redirect('index')
    # Missions en cours ou assignées
    missions_actives = MissionTransporteur.objects.filter(transporteur=transporteur, statut__in=['EN_COURS', 'ASSIGNEE']).order_by('-date_assignation')
    # Historique (dernières missions terminées)
    missions_terminees = MissionTransporteur.objects.filter(transporteur=transporteur, statut='TERMINEE').order_by('-date_fin')[:10]
    # Notifications non lues
    notifications = Notification.objects.filter(destinataire=request.user, lu=False).order_by('-date_creation')
    context = {
        'transporteur': transporteur,
        'missions_actives': missions_actives,
        'missions_terminees': missions_terminees,
        'notifications': notifications,
        'nombre_livraisons_jour': missions_terminees.filter(date_fin__date=timezone.now().date()).count(),
    }
    return render(request, 'transport/transporteur/dashboard.html', context)

@login_required
def voir_mission(request, mission_id):
    """Voir les détails d'une mission avec itinéraire et suivi"""
    try:
        transporteur = request.user.transporteur
    except Transporteur.DoesNotExist:
        messages.error(request, "Accès non autorisé.")
        return redirect('index')
    mission = get_object_or_404(MissionTransporteur, id=mission_id, transporteur=transporteur)
    # Si l'itinéraire optimisé n'est pas encore calculé, le calculer maintenant
    if not mission.itineraire_optimise:
        from .utils import calculer_itineraire_optimise
        itineraire = calculer_itineraire_optimise(mission.commande.adresse_enlevement, mission.commande.adresse_livraison)
        mission.itineraire_optimise = itineraire
        mission.save()
    return render(request, 'transport/transporteur/voir_mission.html', {
        'mission': mission,
        'commande': mission.commande,
        'itineraire': mission.itineraire_optimise
    })

@login_required
def mettre_a_jour_statut(request, mission_id):
    """Mettre à jour le statut de livraison d'une mission (en cours, terminée, annulée)"""
    try:
        transporteur = request.user.transporteur
    except Transporteur.DoesNotExist:
        messages.error(request, "Accès non autorisé.")
        return redirect('index')
    mission = get_object_or_404(MissionTransporteur, id=mission_id, transporteur=transporteur)
    if request.method == 'POST':
        form = StatutLivraisonForm(request.POST)
        if form.is_valid():
            nouveau_statut = form.cleaned_data['statut']
            commentaire = form.cleaned_data.get('commentaire', '')
            # Mettre à jour la mission et la commande liée
            mission.statut = nouveau_statut
            if nouveau_statut == 'TERMINEE':
                mission.date_fin = timezone.now()
                mission.commande.statut = 'LIVREE'
            elif nouveau_statut == 'EN_COURS':
                mission.date_debut = mission.date_debut or timezone.now()
                mission.commande.statut = 'EN_TRANSIT'
            elif nouveau_statut == 'ANNULEE':
                mission.commande.statut = 'ANNULEE'
            mission.save()
            mission.commande.save()
            # Créer une notification pour le client (informe du changement de statut)
            Notification.objects.create(
                destinataire=mission.commande.client.user,
                type='STATUT',
                titre=f"Mise à jour de votre commande #{mission.commande.id}",
                message=f"Statut: {mission.get_statut_display()}. {commentaire}",
                commande=mission.commande
            )
            messages.success(request, "Statut mis à jour avec succès.")
            return redirect('voir_mission', mission_id=mission.id)
    else:
        form = StatutLivraisonForm(initial={'statut': mission.statut})
    return render(request, 'transport/transporteur/mettre_a_jour_statut.html', {'mission': mission, 'form': form})

@login_required
def notifier_incident(request, mission_id):
    """Notifier un incident survenu pendant la livraison"""
    try:
        transporteur = request.user.transporteur
    except Transporteur.DoesNotExist:
        messages.error(request, "Accès non autorisé.")
        return redirect('index')
    mission = get_object_or_404(MissionTransporteur, id=mission_id, transporteur=transporteur)
    if request.method == 'POST':
        form = IncidentForm(request.POST, request.FILES)
        if form.is_valid():
            incident = form.save(commit=False)
            incident.mission = mission
            incident.transporteur = transporteur
            incident.save()
            # Notifier l'administrateur (priorité haute car incident)
            admins = User.objects.filter(is_staff=True)
            for admin in admins:
                Notification.objects.create(
                    destinataire=admin,
                    type='INCIDENT',
                    titre=f"Incident sur la commande #{mission.commande.id}",
                    message=f"Type: {incident.get_type_display()} – {incident.description}",
                    commande=mission.commande,
                    priorite='HAUTE'
                )
            # Notifier le client également
            Notification.objects.create(
                destinataire=mission.commande.client.user,
                type='INCIDENT',
                titre="Incident sur votre livraison",
                message=f"Un incident a été signalé : {incident.get_type_display()}",
                commande=mission.commande
            )
            messages.success(request, "Incident signalé avec succès.")
            return redirect('voir_mission', mission_id=mission.id)
    else:
        form = IncidentForm()
    return render(request, 'transport/transporteur/notifier_incident.html', {'mission': mission, 'form': form})

@login_required
def generer_bon_livraison(request, mission_id):
    """Générer le bon de livraison PDF pour la mission donnée"""
    try:
        transporteur = request.user.transporteur
    except Transporteur.DoesNotExist:
        messages.error(request, "Accès non autorisé.")
        return redirect('index')
    mission = get_object_or_404(MissionTransporteur, id=mission_id, transporteur=transporteur)
    # Créer ou récupérer le bon de livraison associé à la commande
    bon_livraison, created = BonLivraison.objects.get_or_create(
        commande=mission.commande,
        defaults={'transporteur': transporteur, 'statut': 'EN_COURS'}
    )
    # Générer le PDF du BL via ReportLab
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="bon_livraison_{bon_livraison.id}.pdf"'
    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    # Titre
    elements.append(Paragraph("BON DE LIVRAISON", styles['Title']))
    elements.append(Spacer(1, 0.5*inch))
    # Infos principales
    data = [
        ['N° Bon :', f'BL-{bon_livraison.id}'],
        ['Date :', bon_livraison.date_creation.strftime('%d/%m/%Y %H:%M')],
        ['Transporteur :', transporteur.user.get_full_name() or transporteur.user.username],
        ['Véhicule :', transporteur.matricule],
    ]
    t = Table(data, colWidths=[2*inch, 4*inch])
    t.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.3*inch))
    # Détails de la commande
    elements.append(Paragraph("DÉTAILS DE LA COMMANDE", styles['Heading2']))
    commande_data = [
        ['N° Commande :', f'#{mission.commande.id}'],
        ['Client :', mission.commande.client.user.get_full_name() or mission.commande.client.user.username],
        ['Type de marchandise :', mission.commande.type_marchandise],
        ['Poids :', f"{mission.commande.poids} kg"],
    ]
    t2 = Table(commande_data, colWidths=[2*inch, 4*inch])
    t2.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t2)
    elements.append(Spacer(1, 0.3*inch))
    # Adresses (enlèvement / livraison)
    elements.append(Paragraph("ADRESSES", styles['Heading2']))
    adresse_data = [
        ['Enlèvement :', str(mission.commande.adresse_enlevement)],
        ['', f"{mission.commande.adresse_enlevement.code_postal} {mission.commande.adresse_enlevement.ville}"],
        ['', ''],
        ['Livraison :', str(mission.commande.adresse_livraison)],
        ['', f"{mission.commande.adresse_livraison.code_postal} {mission.commande.adresse_livraison.ville}"],
    ]
    t3 = Table(adresse_data, colWidths=[2*inch, 4*inch])
    t3.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t3)
    elements.append(Spacer(1, 0.5*inch))
    # Sections pour signatures
    elements.append(Paragraph("SIGNATURES", styles['Heading2']))
    signature_data = [
        ['Transporteur :', '_' * 40],
        ['', ''],
        ['Client/Destinataire :', '_' * 40],
        ['', ''],
        ['Date et heure de livraison :', '_' * 40],
    ]
    t4 = Table(signature_data, colWidths=[2.5*inch, 3.5*inch])
    t4.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(t4)
    # Build du PDF
    doc.build(elements)
    return response

@login_required
def marquer_notification_lue(request, notification_id):
    """Marquer une notification comme lue (appelé via AJAX ou lien)"""
    try:
        notif = get_object_or_404(Notification, id=notification_id, destinataire=request.user)
        notif.lu = True
        notif.save()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return redirect('dashboard_transporteur')
    except Notification.DoesNotExist:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False})
        raise Http404

@login_required
def basculer_disponibilite(request):
    """Basculer la disponibilité du transporteur (disponible/indisponible)"""
    try:
        transporteur = request.user.transporteur
        transporteur.disponible = not transporteur.disponible
        transporteur.save()
        status = "disponible" if transporteur.disponible else "indisponible"
        messages.success(request, f"Vous êtes maintenant {status}.")
        return redirect('dashboard_transporteur')
    except Transporteur.DoesNotExist:
        messages.error(request, "Erreur : profil transporteur introuvable.")
        return redirect('index')
