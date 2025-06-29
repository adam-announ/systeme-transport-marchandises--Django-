from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.hashers import check_password, make_password
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token
from .models import User, Commande, Vehicule, Livraison, Notification, Tournee, EtapeTournee, ParametreSysteme
import json

def accueil(request):
    return render(request, 'public/index.html')

def gestion_commandes(request):
    return render(request, 'public/gestion_commandes.html')

def optimisation_tournees(request):
    return render(request, 'public/optimisation_tournees.html')

def suivi_temps_reel(request):
    return render(request, 'public/suivi_temps_reel.html')

def contact(request):
    return render(request, 'public/contact.html')

def login_view(request):
    if 'user_id' in request.session:
        role = request.session.get('role')
        if role == 'admin':
            return redirect('admin_dashboard')
        elif role == 'planificateur':
            return redirect('planificateur_dashboard')
        elif role == 'transporteur':
            return redirect('transporteur_dashboard')
        elif role == 'client':
            return redirect('client_dashboard')
        else:
            return redirect('accueil')
    
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        
        try:
            user = User.objects.get(username=username, is_active=True)
            if check_password(password, user.password):
                request.session['user_id'] = user.id
                request.session['username'] = user.username
                request.session['role'] = user.role
                request.session['first_name'] = user.first_name
                request.session['last_name'] = user.last_name
                
                if user.role == 'admin':
                    return redirect('admin_dashboard')
                elif user.role == 'planificateur':
                    return redirect('planificateur_dashboard')
                elif user.role == 'transporteur':
                    return redirect('transporteur_dashboard')
                elif user.role == 'client':
                    return redirect('client_dashboard')
                else:
                    return redirect('accueil')
            else:
                messages.error(request, 'Mot de passe incorrect.')
        except User.DoesNotExist:
            messages.error(request, 'Nom d\'utilisateur introuvable.')
    
    return render(request, 'auth/login.html')

def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        role = request.POST['role']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        phone = request.POST.get('phone', '')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Ce nom d\'utilisateur existe déjà.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Cet email est déjà utilisé.')
        else:
            user = User(
                username=username,
                email=email,
                password=password,
                role=role,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                is_active=True
            )
            user.save()
            messages.success(request, 'Compte créé avec succès ! Vous pouvez maintenant vous connecter.')
            return redirect('login')
    
    return render(request, 'auth/register.html')

def logout_view(request):
    if 'user_id' in request.session:
        request.session.flush()
    return redirect('accueil')

# Décorateurs
def admin_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if 'user_id' not in request.session or request.session.get('role') != 'admin':
            messages.error(request, 'Accès non autorisé.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def transporteur_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if 'user_id' not in request.session or request.session.get('role') != 'transporteur':
            messages.error(request, 'Accès non autorisé.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def client_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if 'user_id' not in request.session or request.session.get('role') != 'client':
            messages.error(request, 'Accès non autorisé.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def planificateur_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if 'user_id' not in request.session or request.session.get('role') != 'planificateur':
            messages.error(request, 'Accès non autorisé.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# Vues Admin
@admin_required
def admin_dashboard(request):
    stats = {
        'total_users': User.objects.count(),
        'commandes_mois': Commande.objects.filter(
            date_creation__gte=timezone.now().replace(day=1)
        ).count(),
        'livraisons_cours': Livraison.objects.filter(statut='en_cours').count(),
        'revenus_mois': 0
    }
    
    recent_commandes = Commande.objects.select_related('client').order_by('-date_creation')[:10]
    
    context = {
        'stats': stats,
        'recent_commandes': recent_commandes
    }
    return render(request, 'admin/admin_dashboard.html', context)

@admin_required
def admin_users(request):
    users = User.objects.all().order_by('-created_at')
    
    # Filtres
    search = request.GET.get('search')
    role = request.GET.get('role')
    status = request.GET.get('status')
    
    if search:
        users = users.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(username__icontains=search) |
            Q(email__icontains=search)
        )
    
    if role:
        users = users.filter(role=role)
    
    if status:
        if status == 'active':
            users = users.filter(is_active=True)
        elif status == 'inactive':
            users = users.filter(is_active=False)
    
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    users_page = paginator.get_page(page_number)
    
    context = {
        'users': users_page,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': users_page
    }
    return render(request, 'admin/admin_users.html', context)

@admin_required
def admin_create_user(request):
    if request.method == 'POST':
        try:
            username = request.POST['username']
            email = request.POST['email']
            
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Ce nom d\'utilisateur existe déjà.')
                return render(request, 'admin/admin_create_user.html')
            
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Cet email est déjà utilisé.')
                return render(request, 'admin/admin_create_user.html')
            
            user = User.objects.create(
                username=username,
                email=email,
                password=request.POST['password'],
                role=request.POST['role'],
                first_name=request.POST.get('first_name', ''),
                last_name=request.POST.get('last_name', ''),
                phone=request.POST.get('phone', ''),
                is_active=request.POST.get('is_active') == 'on'
            )
            
            messages.success(request, f'Utilisateur {username} créé avec succès!')
            return redirect('admin_users')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la création: {str(e)}')
    
    return render(request, 'admin/admin_create_user.html')

@admin_required
def admin_edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        try:
            email = request.POST['email']
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                messages.error(request, 'Cet email est déjà utilisé par un autre utilisateur.')
            else:
                user.first_name = request.POST.get('first_name', '')
                user.last_name = request.POST.get('last_name', '')
                user.email = email
                user.phone = request.POST.get('phone', '')
                user.role = request.POST['role']
                user.is_active = request.POST.get('is_active') == 'on'
                
                user.save()
                messages.success(request, 'Utilisateur mis à jour avec succès!')
                return redirect('admin_users')
                
        except Exception as e:
            messages.error(request, f'Erreur lors de la mise à jour: {str(e)}')
    
    return render(request, 'admin/admin_edit_user.html', {'user': user})

@admin_required
def admin_toggle_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        user.is_active = not user.is_active
        user.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

@admin_required
def admin_delete_user(request, user_id):
    if request.method == 'POST':
        try:
            user = get_object_or_404(User, id=user_id)
            
            # Empêcher la suppression des comptes admin
            if user.role == 'admin':
                return JsonResponse({
                    'success': False,
                    'message': 'Impossible de supprimer un compte administrateur.'
                })
            
            # Empêcher l'auto-suppression
            if user.id == request.session.get('user_id'):
                return JsonResponse({
                    'success': False,
                    'message': 'Vous ne pouvez pas supprimer votre propre compte.'
                })
            
            username = user.username
            user.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Utilisateur {username} supprimé avec succès.'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur lors de la suppression: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})

@admin_required
def admin_commandes(request):
    commandes = Commande.objects.select_related('client', 'transporteur').order_by('-date_creation')
    
    # Filtres
    statut = request.GET.get('statut')
    transporteur_id = request.GET.get('transporteur')
    date = request.GET.get('date')
    
    if statut:
        commandes = commandes.filter(statut=statut)
    if transporteur_id:
        commandes = commandes.filter(transporteur_id=transporteur_id)
    if date:
        commandes = commandes.filter(date_creation__date=date)
    
    # Statistiques
    commandes_en_attente = commandes.filter(statut='en_attente').count()
    commandes_en_cours = commandes.filter(statut__in=['affectee', 'en_cours']).count()
    commandes_livrees = commandes.filter(statut='livree').count()
    
    # Transporteurs pour les filtres et assignations
    transporteurs = User.objects.filter(role='transporteur', is_active=True)
    
    paginator = Paginator(commandes, 20)
    page_number = request.GET.get('page')
    commandes_page = paginator.get_page(page_number)
    
    context = {
        'commandes': commandes_page,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': commandes_page,
        'transporteurs': transporteurs,
        'commandes_en_attente': commandes_en_attente,
        'commandes_en_cours': commandes_en_cours,
        'commandes_livrees': commandes_livrees
    }
    return render(request, 'admin/admin_commandes.html', context)

@admin_required
def admin_reports(request):
    from django.db.models import Count, Sum, Avg
    from datetime import datetime, timedelta
    
    # Données réelles des commandes
    total_commandes = Commande.objects.count()
    commandes_livrees = Commande.objects.filter(statut='livree').count()
    commandes_en_cours = Commande.objects.filter(statut__in=['affectee', 'en_cours']).count()
    commandes_en_attente = Commande.objects.filter(statut='en_attente').count()
    commandes_annulees = Commande.objects.filter(statut='annulee').count()
    
    # Revenus réels (simulation basée sur les commandes)
    revenus_totaux = commandes_livrees * 150  # 150€ par commande livrée en moyenne
    
    # Poids total transporté
    poids_total = Commande.objects.aggregate(total=Sum('poids'))['total'] or 0
    
    # Utilisateurs réels
    total_users = User.objects.count()
    total_clients = User.objects.filter(role='client').count()
    total_transporteurs = User.objects.filter(role='transporteur').count()
    total_planificateurs = User.objects.filter(role='planificateur').count()
    
    # Véhicules réels
    total_vehicules = Vehicule.objects.count()
    vehicules_disponibles = Vehicule.objects.filter(disponible=True).count()
    vehicules_camionnettes = Vehicule.objects.filter(type_vehicule='camionnette').count()
    vehicules_camions = Vehicule.objects.filter(type_vehicule='camion').count()
    vehicules_semi = Vehicule.objects.filter(type_vehicule='semi-remorque').count()
    
    # Graphique des revenus (6 derniers mois)
    chart_labels = []
    chart_revenus = []
    for i in range(5, -1, -1):
        date = timezone.now() - timedelta(days=30*i)
        month_name = date.strftime('%b')
        chart_labels.append(month_name)
        # Simulation basée sur les commandes du mois
        commandes_mois = Commande.objects.filter(
            date_creation__year=date.year,
            date_creation__month=date.month,
            statut='livree'
        ).count()
        chart_revenus.append(commandes_mois * 150)
    
    # Répartition des véhicules
    vehicules_repartition = [vehicules_camionnettes, vehicules_camions, vehicules_semi]
    
    # Métriques calculées
    taux_livraison = round((commandes_livrees / total_commandes * 100) if total_commandes > 0 else 0, 1)
    taux_annulation = round((commandes_annulees / total_commandes * 100) if total_commandes > 0 else 0, 1)
    
    metrics = {
        'revenus_totaux': revenus_totaux,
        'croissance_revenus': 8,  # Simulation
        'commandes_traitees': commandes_livrees,
        'croissance_commandes': 12,  # Simulation
        'taux_satisfaction': 85,  # Simulation
        'delai_moyen': 24,  # Simulation
        'amelioration_delai': 2,  # Simulation
        'taux_ponctualite': taux_livraison,
        'temps_prise_charge': 3,  # Simulation
        'taux_incidents': taux_annulation,
        'capacite_utilisee': 75,  # Simulation
        'total_commandes': total_commandes,
        'total_users': total_users,
        'total_vehicules': total_vehicules,
        'poids_total': poids_total
    }
    
    # Top transporteurs réels
    top_transporteurs = []
    transporteurs = User.objects.filter(role='transporteur', is_active=True)
    for transporteur in transporteurs:
        commandes_transporteur = Commande.objects.filter(transporteur=transporteur, statut='livree').count()
        revenus_transporteur = commandes_transporteur * 150
        if commandes_transporteur > 0:
            top_transporteurs.append({
                'first_name': transporteur.first_name or 'N/A',
                'last_name': transporteur.last_name or '',
                'email': transporteur.email,
                'total_livraisons': commandes_transporteur,
                'total_revenus': revenus_transporteur,
                'note_moyenne': 4.2  # Simulation
            })
    
    # Trier par nombre de livraisons
    top_transporteurs = sorted(top_transporteurs, key=lambda x: x['total_livraisons'], reverse=True)[:10]
    
    # Top destinations réelles
    destinations_data = Commande.objects.values('destination').annotate(
        total_commandes=Count('id'),
        total_poids=Sum('poids')
    ).order_by('-total_commandes')[:10]
    
    top_destinations = []
    for dest in destinations_data:
        top_destinations.append({
            'ville': dest['destination'],
            'total_commandes': dest['total_commandes'],
            'total_poids': dest['total_poids'] or 0,
            'total_revenus': dest['total_commandes'] * 150
        })
    
    context = {
        'chart_labels': chart_labels,
        'chart_revenus': chart_revenus,
        'vehicules_repartition': vehicules_repartition,
        'metrics': metrics,
        'top_transporteurs': top_transporteurs,
        'top_destinations': top_destinations,
        'stats': {
            'total_commandes': total_commandes,
            'commandes_livrees': commandes_livrees,
            'commandes_en_cours': commandes_en_cours,
            'commandes_en_attente': commandes_en_attente,
            'commandes_annulees': commandes_annulees,
            'total_clients': total_clients,
            'total_transporteurs': total_transporteurs,
            'vehicules_disponibles': vehicules_disponibles
        }
    }
    return render(request, 'admin/admin_reports.html', context)

@admin_required
def admin_reports_export(request):
    from django.http import HttpResponse
    import json
    
    export_format = request.GET.get('export', 'pdf')
    
    if export_format == 'pdf':
        # Générer un rapport PDF simple
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="rapport_transport.pdf"'
        
        # Contenu PDF simple (vous pouvez utiliser reportlab pour un vrai PDF)
        pdf_content = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 200 >>
stream
BT
/F1 12 Tf
50 750 Td
(RAPPORT TRANSPORT SYSTEM) Tj
0 -20 Td
(Date: {timezone.now().strftime('%d/%m/%Y')}) Tj
0 -20 Td
(Total commandes: {Commande.objects.count()}) Tj
0 -20 Td
(Commandes livrées: {Commande.objects.filter(statut='livree').count()}) Tj
0 -20 Td
(Total utilisateurs: {User.objects.count()}) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000110 00000 n 
0000000252 00000 n 
0000000504 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
565
%%EOF"""
        
        response.write(pdf_content.encode('utf-8'))
        return response
        
    elif export_format == 'excel':
        # Générer un fichier Excel simple
        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename="rapport_transport.xls"'
        
        excel_content = f"""Rapport Transport System\t\t\t
Date\t{timezone.now().strftime('%d/%m/%Y')}\t\t\t
\t\t\t\t
Statistiques\t\t\t\t
Total commandes\t{Commande.objects.count()}\t\t\t
Commandes livrées\t{Commande.objects.filter(statut='livree').count()}\t\t\t
Commandes en cours\t{Commande.objects.filter(statut__in=['affectee', 'en_cours']).count()}\t\t\t
Total utilisateurs\t{User.objects.count()}\t\t\t
Total transporteurs\t{User.objects.filter(role='transporteur').count()}\t\t\t
Total véhicules\t{Vehicule.objects.count()}\t\t\t"""
        
        response.write(excel_content)
        return response
    
    return HttpResponse('Format non supporté', status=400)

@admin_required
def admin_system_config(request):
    if request.method == 'POST':
        try:
            # Traitement des paramètres généraux
            if 'company_name' in request.POST:
                ParametreSysteme.objects.update_or_create(
                    cle='company_name',
                    defaults={'valeur': request.POST.get('company_name', 'Transport System')}
                )
                ParametreSysteme.objects.update_or_create(
                    cle='contact_email',
                    defaults={'valeur': request.POST.get('contact_email', 'contact@transportsystem.com')}
                )
                ParametreSysteme.objects.update_or_create(
                    cle='phone',
                    defaults={'valeur': request.POST.get('phone', '+33 1 23 45 67 89')}
                )
                ParametreSysteme.objects.update_or_create(
                    cle='default_currency',
                    defaults={'valeur': request.POST.get('default_currency', 'EUR')}
                )
            
            # Traitement des paramètres de transport
            if 'min_price_per_kg' in request.POST:
                ParametreSysteme.objects.update_or_create(
                    cle='min_price_per_kg',
                    defaults={'valeur': request.POST.get('min_price_per_kg', '0.50'), 'type_valeur': 'float'}
                )
                ParametreSysteme.objects.update_or_create(
                    cle='max_price_per_kg',
                    defaults={'valeur': request.POST.get('max_price_per_kg', '5.00'), 'type_valeur': 'float'}
                )
                ParametreSysteme.objects.update_or_create(
                    cle='min_delivery_time',
                    defaults={'valeur': request.POST.get('min_delivery_time', '2'), 'type_valeur': 'integer'}
                )
                ParametreSysteme.objects.update_or_create(
                    cle='system_commission',
                    defaults={'valeur': request.POST.get('system_commission', '5'), 'type_valeur': 'float'}
                )
                ParametreSysteme.objects.update_or_create(
                    cle='auto_assignment',
                    defaults={'valeur': 'true' if request.POST.get('auto_assignment') else 'false', 'type_valeur': 'boolean'}
                )
            
            # Traitement des paramètres de notification
            if 'email_notifications' in request.POST or 'sms_notifications' in request.POST:
                ParametreSysteme.objects.update_or_create(
                    cle='email_notifications',
                    defaults={'valeur': 'true' if request.POST.get('email_notifications') else 'false', 'type_valeur': 'boolean'}
                )
                ParametreSysteme.objects.update_or_create(
                    cle='sms_notifications',
                    defaults={'valeur': 'true' if request.POST.get('sms_notifications') else 'false', 'type_valeur': 'boolean'}
                )
            
            messages.success(request, 'Configuration sauvegardée avec succès!')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la sauvegarde: {str(e)}')
    
    # Récupérer les paramètres actuels
    def get_param(cle, default=''):
        try:
            param = ParametreSysteme.objects.get(cle=cle)
            return param.get_typed_value()
        except ParametreSysteme.DoesNotExist:
            return default
    
    context = {
        'config': {
            'company_name': get_param('company_name', 'Transport System'),
            'contact_email': get_param('contact_email', 'contact@transportsystem.com'),
            'phone': get_param('phone', '+33 1 23 45 67 89'),
            'default_currency': get_param('default_currency', 'EUR'),
            'min_price_per_kg': get_param('min_price_per_kg', 0.50),
            'max_price_per_kg': get_param('max_price_per_kg', 5.00),
            'min_delivery_time': get_param('min_delivery_time', 2),
            'system_commission': get_param('system_commission', 5),
            'auto_assignment': get_param('auto_assignment', True),
            'email_notifications': get_param('email_notifications', True),
            'sms_notifications': get_param('sms_notifications', False)
        }
    }
    return render(request, 'admin/admin_system_config.html', context)

@admin_required
def admin_notifications(request):
    return render(request, 'admin/admin_notifications.html')

@admin_required
def admin_profil(request):
    user_id = request.session['user_id']
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        try:
            user.first_name = request.POST.get('first_name', '').strip()
            user.last_name = request.POST.get('last_name', '').strip()
            user.email = request.POST.get('email', '').strip()
            user.phone = request.POST.get('phone', '').strip()
            user.save()
            
            request.session['first_name'] = user.first_name
            request.session['last_name'] = user.last_name
            
            messages.success(request, 'Profil mis à jour avec succès!')
            return redirect('admin_profil')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la mise à jour: {str(e)}')
    
    return render(request, 'admin/admin_profil.html', {'user': user})

# Vues Transporteur
@transporteur_required
def transporteur_dashboard(request):
    user_id = request.session['user_id']
    
    stats = {
        'livraisons_completees': 0,
        'livraisons_en_cours': 0,
        'revenus_mois': 0,
        'note_moyenne': 4.2
    }
    
    context = {
        'stats': stats,
    }
    return render(request, 'transporteur/transporteur_dashboard.html', context)

@transporteur_required
def transporteur_commandes(request):
    user_id = request.session['user_id']
    commandes = Commande.objects.filter(statut='en_attente').select_related('client')
    paginator = Paginator(commandes, 12)
    page_number = request.GET.get('page')
    commandes_page = paginator.get_page(page_number)
    
    # Récupérer les véhicules du transporteur
    mes_vehicules = Vehicule.objects.filter(transporteur_id=user_id, disponible=True)
    
    context = {
        'commandes': commandes_page,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': commandes_page,
        'mes_vehicules': mes_vehicules,
        'commandes_disponibles': commandes.count(),
    }
    return render(request, 'transporteur/transporteur_commandes.html', context)

@transporteur_required
def transporteur_accept_commande(request, commande_id):
    if request.method == 'POST':
        try:
            user_id = request.session['user_id']
            commande = get_object_or_404(Commande, id=commande_id, statut='en_attente')
            
            # Vérifier si le transporteur a des véhicules
            vehicules = Vehicule.objects.filter(transporteur_id=user_id, disponible=True)
            if not vehicules.exists():
                return JsonResponse({
                    'success': False,
                    'message': 'Vous devez d\'abord ajouter au moins un véhicule pour accepter des commandes.'
                })
            
            data = json.loads(request.body)
            vehicule_id = data.get('vehicule_id')
            heure_depart = data.get('heure_depart')
            notes = data.get('notes', '')
            
            if not vehicule_id or not heure_depart:
                return JsonResponse({
                    'success': False,
                    'message': 'Veuillez remplir tous les champs obligatoires.'
                })
            
            # Vérifier que le véhicule appartient au transporteur
            vehicule = get_object_or_404(Vehicule, id=vehicule_id, transporteur_id=user_id)
            
            # Vérifier la capacité du véhicule
            if commande.poids > vehicule.capacite_max:
                return JsonResponse({
                    'success': False,
                    'message': f'Le poids de la commande ({commande.poids}kg) dépasse la capacité du véhicule ({vehicule.capacite_max}kg).'
                })
            
            with transaction.atomic():
                # Mettre à jour la commande
                commande.transporteur_id = user_id
                commande.statut = 'affectee'
                commande.save()
                
                # Créer la livraison
                livraison = Livraison.objects.create(
                    commande=commande,
                    vehicule=vehicule,
                    statut='en_attente',
                    notes_livraison=notes
                )
                
                # Créer une notification pour le client
                Notification.objects.create(
                    utilisateur=commande.client,
                    titre='Commande acceptée',
                    message=f'Votre commande #{commande.id} a été acceptée par un transporteur.',
                    type_notification='commande_acceptee'
                )
            
            return JsonResponse({
                'success': True,
                'message': 'Commande acceptée avec succès !'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur lors de l\'acceptation: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})

@transporteur_required
def transporteur_livraisons(request):
    user_id = request.session['user_id']
    livraisons = Livraison.objects.filter(
        commande__transporteur_id=user_id
    ).select_related('commande', 'vehicule').order_by('-commande__date_creation')
    
    paginator = Paginator(livraisons, 15)
    page_number = request.GET.get('page')
    livraisons_page = paginator.get_page(page_number)
    
    context = {
        'livraisons': livraisons_page,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': livraisons_page,
    }
    return render(request, 'transporteur/transporteur_livraisons.html', context)

@transporteur_required
def transporteur_livraison_details(request, livraison_id):
    user_id = request.session['user_id']
    livraison = get_object_or_404(Livraison, id=livraison_id, commande__transporteur_id=user_id)
    
    context = {
        'livraison': livraison,
        'commande': livraison.commande,
    }
    return render(request, 'transporteur/transporteur_livraison_details.html', context)

@transporteur_required
def transporteur_update_livraison(request, livraison_id):
    return JsonResponse({'success': False})

@transporteur_required
def transporteur_vehicules(request):
    user_id = request.session['user_id']
    vehicules = Vehicule.objects.filter(transporteur_id=user_id).order_by('-id')
    
    # Statistiques
    vehicules_disponibles = vehicules.filter(disponible=True).count()
    vehicules_en_service = vehicules.filter(disponible=False).count()
    capacite_totale = sum(float(v.capacite_max) for v in vehicules)
    
    context = {
        'vehicules': vehicules,
        'vehicules_disponibles': vehicules_disponibles,
        'vehicules_en_service': vehicules_en_service,
        'capacite_totale': int(capacite_totale),
    }
    return render(request, 'transporteur/transporteur_vehicules.html', context)

@transporteur_required
def transporteur_add_vehicule(request):
    if request.method == 'POST':
        try:
            user_id = request.session['user_id']
            
            vehicule = Vehicule.objects.create(
                transporteur_id=user_id,
                immatriculation=request.POST['immatriculation'],
                type_vehicule=request.POST['type_vehicule'],
                capacite_max=float(request.POST['capacite_max']),
                disponible=True
            )
            
            messages.success(request, 'Véhicule ajouté avec succès.')
            return redirect('transporteur_vehicules')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de l\'ajout du véhicule: {str(e)}')
    
    return render(request, 'transporteur/transporteur_add_vehicule.html')

@transporteur_required
def transporteur_vehicule_details(request, vehicule_id):
    user_id = request.session['user_id']
    vehicule = get_object_or_404(Vehicule, id=vehicule_id, transporteur_id=user_id)
    
    # Récupérer les livraisons récentes pour ce véhicule
    livraisons_recentes = Livraison.objects.filter(
        vehicule=vehicule
    ).select_related('commande').order_by('-commande__date_creation')[:5]
    
    context = {
        'vehicule': vehicule,
        'livraisons_recentes': livraisons_recentes,
    }
    
    # Si c'est une requête AJAX, retourner seulement le contenu HTML
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'transporteur/vehicule_details_content.html', context)
    
    return render(request, 'transporteur/transporteur_vehicule_details.html', context)

@transporteur_required
def transporteur_vehicule_update(request, vehicule_id):
    if request.method == 'POST':
        try:
            user_id = request.session['user_id']
            vehicule = get_object_or_404(Vehicule, id=vehicule_id, transporteur_id=user_id)
            
            data = json.loads(request.body)
            
            if data.get('toggle_disponibilite'):
                vehicule.disponible = not vehicule.disponible
            else:
                vehicule.immatriculation = data.get('immatriculation')
                vehicule.type_vehicule = data.get('type_vehicule')
                vehicule.capacite_max = float(data.get('capacite_max'))
                vehicule.disponible = data.get('disponible', False)
            
            vehicule.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Véhicule mis à jour avec succès.'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})

@transporteur_required
def transporteur_start_tournee(request):
    if request.method == 'POST':
        try:
            user_id = request.session['user_id']
            data = json.loads(request.body)
            
            livraison_ids = data.get('livraison_ids', [])
            vehicule_id = data.get('vehicule_id')
            
            if not livraison_ids:
                return JsonResponse({
                    'success': False,
                    'message': 'Aucune livraison sélectionnée'
                })
            
            # Vérifier que toutes les livraisons appartiennent au transporteur
            livraisons = Livraison.objects.filter(
                id__in=livraison_ids,
                commande__transporteur_id=user_id,
                statut='en_attente'
            )
            
            if livraisons.count() != len(livraison_ids):
                return JsonResponse({
                    'success': False,
                    'message': 'Certaines livraisons ne sont pas valides'
                })
            
            # Mettre à jour le statut des livraisons
            with transaction.atomic():
                for livraison in livraisons:
                    livraison.statut = 'en_cours'
                    livraison.date_debut = timezone.now()
                    livraison.save()
                    
                    # Mettre à jour le statut de la commande
                    livraison.commande.statut = 'en_cours'
                    livraison.commande.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Tournée démarrée avec {livraisons.count()} livraison(s)'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})

@transporteur_required
def transporteur_itineraire(request):
    user_id = request.session['user_id']
    
    # Récupérer les livraisons en attente ou en cours pour ce transporteur
    livraisons_en_cours = Livraison.objects.filter(
        commande__transporteur_id=user_id,
        statut__in=['en_attente', 'en_cours']
    ).select_related('commande', 'vehicule', 'commande__client').order_by('commande__date_livraison_prevue')
    
    # Statistiques pour la sidebar
    commandes_disponibles = Commande.objects.filter(statut='en_attente').count()
    livraisons_actives = livraisons_en_cours.count()
    
    # Statistiques d'optimisation
    stats_optimisation = {
        'distance_moyenne_par_livraison': 25,  # km
        'temps_moyen_par_arret': 30,  # minutes
        'vitesse_moyenne_recommandee': 60,  # km/h
        'consommation_moyenne': 8.5,  # L/100km
        'prix_carburant_actuel': 1.45,  # €/L
    }
    
    # Véhicules disponibles
    vehicules_disponibles = Vehicule.objects.filter(
        transporteur_id=user_id,
        disponible=True
    )
    
    context = {
        'livraisons_en_cours': livraisons_en_cours,
        'commandes_disponibles': commandes_disponibles,
        'livraisons_actives': livraisons_actives,
        'stats_optimisation': stats_optimisation,
        'vehicules_disponibles': vehicules_disponibles,
        'total_poids': sum(float(l.commande.poids) for l in livraisons_en_cours),
        'livraisons_urgentes': livraisons_en_cours.filter(commande__priorite='urgente').count(),
    }
    return render(request, 'transporteur/transporteur_itineraire.html', context)

@transporteur_required
def transporteur_profil(request):
    user_id = request.session['user_id']
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            phone = request.POST.get('phone', '').strip()
            
            # Validation des champs obligatoires
            if not first_name or not last_name or not email:
                messages.error(request, 'Les champs Prénom, Nom et Email sont obligatoires.')
                return render(request, 'transporteur/transporteur_profil.html', {'user': user})
            
            # Vérifier si l'email est déjà utilisé par un autre utilisateur
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                messages.error(request, 'Cet email est déjà utilisé par un autre utilisateur.')
                return render(request, 'transporteur/transporteur_profil.html', {'user': user})
            
            # Mettre à jour les informations de l'utilisateur
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.phone = phone
            user.save()
            
            # Mettre à jour la session avec les nouvelles informations
            request.session['first_name'] = user.first_name
            request.session['last_name'] = user.last_name
            
            messages.success(request, 'Profil mis à jour avec succès!')
            return redirect('transporteur_profil')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la mise à jour du profil: {str(e)}')
    
    context = {
        'user': user,
    }
    return render(request, 'transporteur/transporteur_profil.html', context)

# Vues Client
@client_required
def client_dashboard(request):
    user_id = request.session['user_id']
    
    # Statistiques détaillées
    commandes_client = Commande.objects.filter(client_id=user_id)
    
    stats = {
        'commandes_total': commandes_client.count(),
        'commandes_en_cours': commandes_client.filter(statut__in=['affectee', 'en_cours']).count(),
        'commandes_livrees': commandes_client.filter(statut='livree').count(),
        'commandes_en_attente': commandes_client.filter(statut='en_attente').count(),
        'commandes_annulees': commandes_client.filter(statut='annulee').count(),
        'depenses_totales': sum(float(c.prix or 0) for c in commandes_client.filter(prix__isnull=False)),
        'poids_total': sum(float(c.poids) for c in commandes_client),
    }
    
    # Commandes récentes
    commandes_recentes = commandes_client.select_related('transporteur').order_by('-date_creation')[:5]
    
    # Notifications récentes
    notifications = Notification.objects.filter(
        utilisateur_id=user_id
    ).order_by('-date_creation')[:3]
    
    # Statistiques par mois (3 derniers mois)
    from datetime import datetime, timedelta
    today = timezone.now()
    stats_mensuelles = []
    
    for i in range(3):
        debut_mois = (today - timedelta(days=30*i)).replace(day=1)
        fin_mois = (debut_mois + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        commandes_mois = commandes_client.filter(
            date_creation__gte=debut_mois,
            date_creation__lte=fin_mois
        )
        
        stats_mensuelles.append({
            'mois': debut_mois.strftime('%B %Y'),
            'commandes': commandes_mois.count(),
            'livrees': commandes_mois.filter(statut='livree').count(),
            'depenses': sum(float(c.prix or 0) for c in commandes_mois.filter(prix__isnull=False))
        })
    
    context = {
        'stats': stats,
        'commandes_recentes': commandes_recentes,
        'notifications': notifications,
        'stats_mensuelles': stats_mensuelles,
    }
    return render(request, 'client/client_dashboard.html', context)

@client_required
def client_commandes(request):
    user_id = request.session['user_id']
    commandes = Commande.objects.filter(client_id=user_id).order_by('-date_creation')
    
    paginator = Paginator(commandes, 10)
    page_number = request.GET.get('page')
    commandes_page = paginator.get_page(page_number)
    
    context = {
        'commandes': commandes_page,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': commandes_page
    }
    return render(request, 'client/client_commandes.html', context)

@client_required
def client_nouvelle_commande(request):
    if request.method == 'POST':
        try:
            user_id = request.session['user_id']
            
            commande = Commande.objects.create(
                client_id=user_id,
                origine=request.POST['origine'],
                destination=request.POST['destination'],
                description_marchandise=request.POST['description_marchandise'],
                poids=float(request.POST['poids']),
                date_livraison_prevue=request.POST['date_livraison_prevue'],
                notes=request.POST.get('notes', ''),
                statut='en_attente'
            )
            
            messages.success(request, 'Commande créée avec succès!')
            return redirect('client_commandes')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la création de la commande: {str(e)}')
    
    return render(request, 'client/client_nouvelle_commande.html')

@client_required
def client_commande_detail(request, commande_id):
    user_id = request.session['user_id']
    commande = get_object_or_404(Commande, id=commande_id, client_id=user_id)
    
    context = {
        'commande': commande,
    }
    return render(request, 'client/client_commande_detail.html', context)

@client_required
def client_suivi_commande(request, commande_id):
    user_id = request.session['user_id']
    commande = get_object_or_404(Commande, id=commande_id, client_id=user_id)
    
    context = {
        'commande': commande,
    }
    return render(request, 'client/client_suivi_commande.html', context)

@client_required
def client_profil(request):
    user_id = request.session['user_id']
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            phone = request.POST.get('phone', '').strip()
            
            # Validation des champs obligatoires
            if not first_name or not last_name or not email:
                messages.error(request, 'Les champs Prénom, Nom et Email sont obligatoires.')
                return render(request, 'client/client_profil.html', {'user': user})
            
            # Vérifier si l'email est déjà utilisé par un autre utilisateur
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                messages.error(request, 'Cet email est déjà utilisé par un autre utilisateur.')
                return render(request, 'client/client_profil.html', {'user': user})
            
            # Mettre à jour les informations de l'utilisateur
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.phone = phone
            user.save()
            
            # Mettre à jour la session avec les nouvelles informations
            request.session['first_name'] = user.first_name
            request.session['last_name'] = user.last_name
            
            messages.success(request, 'Profil mis à jour avec succès!')
            return redirect('client_profil')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la mise à jour du profil: {str(e)}')
    
    context = {
        'user': user
    }
    return render(request, 'client/client_profil.html', context)

@client_required
def client_factures(request):
    user_id = request.session['user_id']
    commandes_facturees = Commande.objects.filter(
        client_id=user_id,
        statut='livree'
    ).order_by('-date_creation')
    
    paginator = Paginator(commandes_facturees, 15)
    page_number = request.GET.get('page')
    factures_page = paginator.get_page(page_number)
    
    context = {
        'factures': factures_page,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': factures_page
    }
    return render(request, 'client/client_factures.html', context)

@client_required
def client_annuler_commande(request, commande_id):
    if request.method == 'POST':
        try:
            user_id = request.session['user_id']
            commande = get_object_or_404(Commande, id=commande_id, client_id=user_id)
            
            # Vérifier si la commande peut être annulée
            if commande.statut in ['livree', 'annulee']:
                return JsonResponse({
                    'success': False,
                    'message': 'Cette commande ne peut plus être annulée.'
                })
            
            # Annuler la commande
            commande.statut = 'annulee'
            commande.save()
            
            # Créer une notification pour le transporteur si la commande était affectée
            if commande.transporteur:
                Notification.objects.create(
                    utilisateur=commande.transporteur,
                    titre='Commande annulée',
                    message=f'La commande #{commande.id} a été annulée par le client.',
                    type_notification='commande_annulee'
                )
            
            return JsonResponse({
                'success': True,
                'message': 'Commande annulée avec succès.'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur lors de l\'annulation: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})

@client_required
def client_change_password(request):
    if request.method == 'POST':
        try:
            user_id = request.session['user_id']
            user = get_object_or_404(User, id=user_id)
            
            data = json.loads(request.body)
            current_password = data.get('current_password')
            new_password = data.get('new_password')
            
            # Validation des données
            if not current_password or not new_password:
                return JsonResponse({
                    'success': False,
                    'message': 'Tous les champs sont obligatoires.'
                })
            
            if len(new_password) < 8:
                return JsonResponse({
                    'success': False,
                    'message': 'Le nouveau mot de passe doit contenir au moins 8 caractères.'
                })
            
            # Vérifier le mot de passe actuel
            if not check_password(current_password, user.password):
                return JsonResponse({
                    'success': False,
                    'message': 'Le mot de passe actuel est incorrect.'
                })
            
            # Mettre à jour le mot de passe
            user.password = make_password(new_password)
            user.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Mot de passe changé avec succès.'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur lors du changement de mot de passe: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})

@transporteur_required
def transporteur_change_password(request):
    if request.method == 'POST':
        try:
            user_id = request.session['user_id']
            user = get_object_or_404(User, id=user_id)
            
            data = json.loads(request.body)
            current_password = data.get('current_password')
            new_password = data.get('new_password')
            
            # Validation des données
            if not current_password or not new_password:
                return JsonResponse({
                    'success': False,
                    'message': 'Tous les champs sont obligatoires.'
                })
            
            if len(new_password) < 8:
                return JsonResponse({
                    'success': False,
                    'message': 'Le nouveau mot de passe doit contenir au moins 8 caractères.'
                })
            
            # Vérifier le mot de passe actuel
            if not check_password(current_password, user.password):
                return JsonResponse({
                    'success': False,
                    'message': 'Le mot de passe actuel est incorrect.'
                })
            
            # Mettre à jour le mot de passe
            user.password = make_password(new_password)
            user.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Mot de passe changé avec succès.'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur lors du changement de mot de passe: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})

@planificateur_required
def planificateur_profil(request):
    user_id = request.session['user_id']
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            phone = request.POST.get('phone', '').strip()
            
            # Validation des champs obligatoires
            if not first_name or not last_name or not email:
                messages.error(request, 'Les champs Prénom, Nom et Email sont obligatoires.')
                return render(request, 'planificateur/planificateur_profil.html', {'user': user})
            
            # Vérifier si l'email est déjà utilisé par un autre utilisateur
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                messages.error(request, 'Cet email est déjà utilisé par un autre utilisateur.')
                return render(request, 'planificateur/planificateur_profil.html', {'user': user})
            
            # Mettre à jour les informations de l'utilisateur
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.phone = phone
            user.save()
            
            # Mettre à jour la session avec les nouvelles informations
            request.session['first_name'] = user.first_name
            request.session['last_name'] = user.last_name
            
            messages.success(request, 'Profil mis à jour avec succès!')
            return redirect('planificateur_profil')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la mise à jour du profil: {str(e)}')
    
    context = {
        'user': user
    }
    return render(request, 'planificateur/planificateur_profil.html', context)

# Vues Planificateur
@planificateur_required
def planificateur_dashboard(request):
    user_id = request.session['user_id']
    
    # Statistiques réelles
    commandes_a_planifier = Commande.objects.filter(statut='en_attente').count()
    tournees_planifiees = Tournee.objects.filter(planificateur_id=user_id, statut='planifiee').count()
    tournees_en_cours = Tournee.objects.filter(planificateur_id=user_id, statut='en_cours').count()
    
    # Commandes planifiées ce mois
    debut_mois = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    commandes_planifiees_mois = Commande.objects.filter(
        planificateur_id=user_id,
        date_creation__gte=debut_mois,
        statut__in=['planifiee', 'en_cours', 'livree']
    ).count()
    
    stats = {
        'commandes_a_planifier': commandes_a_planifier,
        'tournees_planifiees': tournees_planifiees,
        'tournees_en_cours': tournees_en_cours,
        'commandes_planifiees_mois': commandes_planifiees_mois,
    }
    
    # Commandes urgentes à planifier
    commandes_urgentes = Commande.objects.filter(
        statut='en_attente',
        priorite='urgente'
    ).select_related('client').order_by('date_livraison_prevue')[:10]
    
    # Tournées du jour
    aujourd_hui = timezone.now().date()
    tournees_jour = Tournee.objects.filter(
        planificateur_id=user_id,
        date_debut_prevue__date=aujourd_hui
    ).select_related('transporteur', 'vehicule').annotate(
        nb_commandes=Count('etapes__commande', distinct=True)
    )[:5]
    
    # Notifications récentes
    notifications = Notification.objects.filter(
        utilisateur_id=user_id
    ).order_by('-date_creation')[:5]
    
    # Calcul de l'efficacité de planification
    total_commandes_traitees = Commande.objects.filter(
        planificateur_id=user_id,
        statut__in=['planifiee', 'en_cours', 'livree']
    ).count()
    
    commandes_livrees_temps = Commande.objects.filter(
        planificateur_id=user_id,
        statut='livree'
    ).count()
    
    efficacite_planification = (
        (commandes_livrees_temps / total_commandes_traitees * 100) 
        if total_commandes_traitees > 0 else 0
    )
    
    context = {
        'stats': stats,
        'commandes_urgentes': commandes_urgentes,
        'tournees_jour': tournees_jour,
        'notifications': notifications,
        'efficacite_planification': round(efficacite_planification, 1),
        'temps_moyen_planification': 15,
    }
    return render(request, 'planificateur/planificateur_dashboard.html', context)

@planificateur_required
def planificateur_commandes(request):
    # Filtres
    statut = request.GET.get('statut', '')
    priorite = request.GET.get('priorite', '')
    search = request.GET.get('search', '')
    date_livraison = request.GET.get('date_livraison', '')
    
    # Base queryset
    commandes = Commande.objects.select_related('client', 'transporteur', 'planificateur')
    
    # Appliquer les filtres
    if statut:
        commandes = commandes.filter(statut=statut)
    if priorite:
        commandes = commandes.filter(priorite=priorite)
    if search:
        commandes = commandes.filter(
            Q(id__icontains=search) |
            Q(client__first_name__icontains=search) |
            Q(client__last_name__icontains=search) |
            Q(origine__icontains=search) |
            Q(destination__icontains=search)
        )
    if date_livraison:
        commandes = commandes.filter(date_livraison_prevue__date=date_livraison)
    
    # Ordonner par priorité et date
    commandes = commandes.order_by(
        '-priorite',  # Urgente en premier
        'date_livraison_prevue',
        '-date_creation'
    )
    
    # Statistiques pour les widgets
    commandes_urgentes = commandes.filter(priorite='urgente', statut='en_attente').count()
    transporteurs_disponibles = User.objects.filter(
        role='transporteur', 
        is_active=True,
        vehicules__disponible=True
    ).distinct().count()
    
    vehicules_disponibles = Vehicule.objects.filter(disponible=True).count()
    
    paginator = Paginator(commandes, 20)
    page_number = request.GET.get('page')
    commandes_page = paginator.get_page(page_number)
    
    context = {
        'commandes': commandes_page,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': commandes_page,
        'commandes_urgentes': commandes_urgentes,
        'transporteurs_disponibles': transporteurs_disponibles,
        'vehicules_disponibles': vehicules_disponibles,
        'filters': {
            'statut': statut,
            'priorite': priorite,
            'search': search,
            'date_livraison': date_livraison
        }
    }
    return render(request, 'planificateur/planificateur_commandes.html', context)

@planificateur_required
def planificateur_tournees(request):
    user_id = request.session['user_id']
    tournees = Tournee.objects.filter(planificateur_id=user_id).select_related('transporteur', 'vehicule').order_by('-date_creation')
    
    paginator = Paginator(tournees, 15)
    page_number = request.GET.get('page')
    tournees_page = paginator.get_page(page_number)
    
    transporteurs = User.objects.filter(role='transporteur', is_active=True)
    
    context = {
        'tournees': tournees_page,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': tournees_page,
        'transporteurs': transporteurs,
    }
    return render(request, 'planificateur/planificateur_tournees.html', context)

@planificateur_required
def planificateur_create_tournee(request):
    if request.method == 'POST':
        try:
            user_id = request.session['user_id']
            
            # Récupérer les données du formulaire
            nom = request.POST.get('nom', '')
            transporteur_id = request.POST.get('transporteur')
            vehicule_id = request.POST.get('vehicule')
            date_debut = request.POST.get('date_debut')
            commandes_ids = request.POST.getlist('commandes')
            notes = request.POST.get('notes', '')
            optimiser = request.POST.get('optimiser') == 'on'
            
            # Validation
            if not all([nom, transporteur_id, vehicule_id, date_debut, commandes_ids]):
                messages.error(request, 'Tous les champs obligatoires doivent être remplis.')
                return redirect('planificateur_create_tournee')
            
            # Vérifications
            transporteur = get_object_or_404(User, id=transporteur_id, role='transporteur')
            vehicule = get_object_or_404(Vehicule, id=vehicule_id, transporteur=transporteur)
            commandes = Commande.objects.filter(id__in=commandes_ids, statut='en_attente')
            
            if not commandes.exists():
                messages.error(request, 'Aucune commande valide sélectionnée.')
                return redirect('planificateur_create_tournee')
            
            # Vérifier la capacité
            poids_total = sum(float(cmd.poids) for cmd in commandes)
            if poids_total > float(vehicule.capacite_max):
                messages.error(request, f'Poids total ({poids_total}kg) dépasse la capacité du véhicule ({vehicule.capacite_max}kg).')
                return redirect('planificateur_create_tournee')
            
            with transaction.atomic():
                # Créer la tournée
                date_debut_dt = datetime.strptime(date_debut, '%Y-%m-%dT%H:%M')
                date_debut_dt = timezone.make_aware(date_debut_dt)
                
                # Estimation de la durée (30 min par commande + trajet)
                duree_estimee = timedelta(minutes=len(commandes) * 30 + 120)
                
                tournee = Tournee.objects.create(
                    nom=nom,
                    planificateur_id=user_id,
                    transporteur=transporteur,
                    vehicule=vehicule,
                    date_debut_prevue=date_debut_dt,
                    date_fin_prevue=date_debut_dt + duree_estimee,
                    distance_totale=len(commandes) * 25,  # Estimation: 25km par commande
                    duree_prevue=duree_estimee,
                    optimisee=optimiser,
                    notes=notes
                )
                
                # Créer les étapes
                heure_actuelle = date_debut_dt
                
                for i, commande in enumerate(commandes):
                    # Étape de collecte (origine)
                    EtapeTournee.objects.create(
                        tournee=tournee,
                        commande=commande,
                        ordre=i * 2 + 1,
                        type_etape='collecte',
                        adresse=commande.origine,
                        heure_prevue=heure_actuelle,
                        duree_prevue=timedelta(minutes=15)
                    )
                    
                    heure_actuelle += timedelta(minutes=30)
                    
                    # Étape de livraison (destination)
                    EtapeTournee.objects.create(
                        tournee=tournee,
                        commande=commande,
                        ordre=i * 2 + 2,
                        type_etape='livraison',
                        adresse=commande.destination,
                        heure_prevue=heure_actuelle,
                        duree_prevue=timedelta(minutes=15)
                    )
                    
                    heure_actuelle += timedelta(minutes=30)
                    
                    # Mettre à jour la commande
                    commande.statut = 'planifiee'
                    commande.planificateur_id = user_id
                    commande.transporteur = transporteur
                    commande.date_livraison_planifiee = heure_actuelle
                    commande.save()
                    
                    # Créer la livraison
                    Livraison.objects.create(
                        commande=commande,
                        vehicule=vehicule,
                        tournee=tournee,
                        statut='en_attente'
                    )
                
                # Marquer le véhicule comme non disponible
                vehicule.disponible = False
                vehicule.save()
                
                # Notifications
                Notification.objects.create(
                    utilisateur=transporteur,
                    type_notification='tournee_creee',
                    titre='Nouvelle tournée assignée',
                    message=f'Une tournée "{nom}" avec {len(commandes)} commande(s) vous a été assignée.',
                    tournee=tournee,
                    priority='high'
                )
                
                for commande in commandes:
                    Notification.objects.create(
                        utilisateur=commande.client,
                        type_notification='commande_planifiee',
                        titre='Commande planifiée',
                        message=f'Votre commande #{commande.id} a été planifiée dans une tournée.',
                        commande=commande,
                        tournee=tournee
                    )
            
            messages.success(request, f'Tournée "{nom}" créée avec succès avec {len(commandes)} commande(s)!')
            return redirect('planificateur_tournees')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la création de la tournée: {str(e)}')
    
    # GET request - afficher le formulaire
    commandes_disponibles = Commande.objects.filter(
        statut='en_attente'
    ).select_related('client').order_by('priorite', 'date_livraison_prevue')
    
    transporteurs = User.objects.filter(
        role='transporteur', 
        is_active=True
    ).prefetch_related('vehicules')
    
    vehicules = Vehicule.objects.filter(
        disponible=True
    ).select_related('transporteur')
    
    # Commande pré-sélectionnée (si passée en paramètre)
    commande_preselect = request.GET.get('commande')
    
    context = {
        'commandes_disponibles': commandes_disponibles,
        'transporteurs': transporteurs,
        'vehicules': vehicules,
        'commande_preselect': commande_preselect,
        'date_defaut': (timezone.now() + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'),
    }
    return render(request, 'planificateur/planificateur_create_tournee.html', context)

@planificateur_required
def nouvelle_tournee(request):
    """Nouvelle page moderne de création de tournée"""
    
    commandes_disponibles = Commande.objects.filter(
        statut='en_attente'
    ).select_related('client').order_by('-priorite', '-date_creation')
    
    vehicules = Vehicule.objects.filter(
        disponible=True,
        transporteur__is_active=True
    ).select_related('transporteur').order_by('type_vehicule', 'capacite_max')
    
    context = {
        'commandes_disponibles': commandes_disponibles,
        'vehicules': vehicules,
        'page_title': 'Nouvelle Tournée'
    }
    
    return render(request, 'planificateur/nouvelle_tournee.html', context)

def check_role(request, required_role):
    """Vérifier le rôle de l'utilisateur"""
    return 'user_id' in request.session and request.session.get('role') == required_role

# API
@admin_required
def assign_commande(request, commande_id):
    if request.method == 'POST':
        try:
            commande = get_object_or_404(Commande, id=commande_id)
            
            if commande.statut != 'en_attente':
                return JsonResponse({
                    'success': False,
                    'message': 'Cette commande ne peut plus être assignée.'
                })
            
            data = json.loads(request.body)
            transporteur_id = data.get('transporteur_id')
            
            if not transporteur_id:
                return JsonResponse({
                    'success': False,
                    'message': 'Veuillez sélectionner un transporteur.'
                })
            
            transporteur = get_object_or_404(User, id=transporteur_id, role='transporteur')
            
            # Assigner la commande
            commande.transporteur = transporteur
            commande.statut = 'affectee'
            commande.save()
            
            # Créer une notification pour le transporteur
            Notification.objects.create(
                utilisateur=transporteur,
                titre='Nouvelle commande assignée',
                message=f'La commande #{commande.id} vous a été assignée.',
                type_notification='commande_assignee'
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Commande assignée avec succès.'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur lors de l\'assignation: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})

def update_livraison_status(request, livraison_id):
    return JsonResponse({'success': False})

def mark_notifications_read(request):
    return JsonResponse({'success': False})

@admin_required
def commande_details_api(request, commande_id):
    try:
        commande = get_object_or_404(Commande, id=commande_id)
        
        data = {
            'success': True,
            'commande': {
                'id': commande.id,
                'client': f"{commande.client.first_name} {commande.client.last_name}" if commande.client.first_name else commande.client.username,
                'transporteur': f"{commande.transporteur.first_name} {commande.transporteur.last_name}" if commande.transporteur and commande.transporteur.first_name else (commande.transporteur.username if commande.transporteur else 'Non affecté'),
                'origine': commande.origine,
                'destination': commande.destination,
                'description_marchandise': commande.description_marchandise,
                'poids': str(commande.poids),
                'statut': commande.statut,
                'statut_display': commande.get_statut_display() if hasattr(commande, 'get_statut_display') else commande.statut,
                'priorite': getattr(commande, 'priorite', 'normale'),
                'priorite_display': getattr(commande, 'priorite', 'Normale').title(),
                'date_creation': commande.date_creation.strftime('%d/%m/%Y %H:%M') if commande.date_creation else '',
                'date_livraison_prevue': commande.date_livraison_prevue.strftime('%d/%m/%Y') if commande.date_livraison_prevue else '',
                'notes': getattr(commande, 'notes', ''),
                'distance_estimee': getattr(commande, 'distance_estimee', None),
                'prix': str(commande.prix) if getattr(commande, 'prix', None) else None
            }
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur lors du chargement: {str(e)}'
        })

def vehicule_details_api(request, vehicule_id):
    return JsonResponse({'error': 'Not implemented'}, status=500)

def vehicule_update_api(request, vehicule_id):
    return JsonResponse({'error': 'Not implemented'}, status=500)

def vehicule_toggle_api(request, vehicule_id):
    return JsonResponse({'error': 'Not implemented'}, status=500)

def check_new_commandes(request):
    return JsonResponse({'hasNew': False})

def check_livraisons_updates(request):
    return JsonResponse({'hasUpdates': False})

@admin_required
def get_vehicules_transporteur(request, transporteur_id):
    try:
        transporteur = get_object_or_404(User, id=transporteur_id, role='transporteur')
        vehicules = Vehicule.objects.filter(transporteur=transporteur, disponible=True)
        
        vehicules_data = []
        for vehicule in vehicules:
            vehicules_data.append({
                'id': vehicule.id,
                'immatriculation': vehicule.immatriculation,
                'type_vehicule': vehicule.type_vehicule,
                'capacite_max': str(vehicule.capacite_max)
            })
        
        return JsonResponse({
            'success': True,
            'vehicules': vehicules_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur: {str(e)}'
        })

def get_notifications_count(request):
    if 'user_id' in request.session:
        try:
            user_id = request.session['user_id']
            count = Notification.objects.filter(
                utilisateur_id=user_id,
                lu=False
            ).count()
            
            return JsonResponse({
                'success': True,
                'count': count
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'count': 0})

def optimize_route_api(request):
    if request.method == 'POST':
        try:
            if 'user_id' not in request.session:
                return JsonResponse({'success': False, 'message': 'Non authentifié'})
                
            data = json.loads(request.body)
            livraison_ids = data.get('livraison_ids', [])
            
            if not livraison_ids:
                return JsonResponse({'success': False, 'message': 'Aucune livraison sélectionnée'})
            
            user_id = request.session['user_id']
            
            # Pour les transporteurs, vérifier que les livraisons leur appartiennent
            if request.session.get('role') == 'transporteur':
                livraisons = Livraison.objects.filter(
                    id__in=livraison_ids,
                    commande__transporteur_id=user_id
                ).select_related('commande')
            else:
                # Pour les autres rôles, récupérer les livraisons par ID
                livraisons = Livraison.objects.filter(
                    id__in=livraison_ids
                ).select_related('commande')
            
            if not livraisons.exists():
                return JsonResponse({'success': False, 'message': 'Aucune livraison trouvée'})
            
            # Calcul d'optimisation
            locations = []
            for livraison in livraisons:
                locations.append({
                    'id': livraison.id,
                    'address': livraison.commande.destination,
                    'commande_id': livraison.commande.id,
                    'origine': livraison.commande.origine
                })
            
            params = data.get('optimization_params', {})
            priority = params.get('priority', 'distance')
            speed = float(params.get('speed', 60))
            consumption = float(params.get('consumption', 8))
            fuel_price = float(params.get('price', 1.45))
            
            # Calcul basique de distance
            base_distance = len(locations) * 25
            if priority == 'distance':
                total_distance = base_distance
            elif priority == 'time':
                total_distance = base_distance * 1.1
            else:  # fuel
                total_distance = base_distance * 0.9
            
            total_time = total_distance / speed
            fuel_cost = (total_distance * consumption / 100) * fuel_price
            
            # Ordre optimisé (simulation)
            import random
            optimized_locations = locations.copy()
            random.shuffle(optimized_locations)
            
            result = {
                'optimized_order': [
                    {
                        'id': loc['id'],
                        'address': loc['address'],
                        'order': i,
                        'commande_id': loc['commande_id']
                    }
                    for i, loc in enumerate(optimized_locations)
                ],
                'total_distance': round(total_distance, 1),
                'total_time': round(total_time, 2),
                'fuel_cost': round(fuel_cost, 2)
            }
            
            return JsonResponse({
                'success': True,
                'data': result
            })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})