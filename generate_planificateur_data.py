import os
import django
import sys
import random
from datetime import datetime, timedelta

# Configuration Django
sys.path.append('c:\\Users\\HP\\Desktop\\transport_system')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'transport_system.settings')
django.setup()

from django.utils import timezone
from decimal import Decimal
from utilisateurs.models import *

def generate_realistic_commandes():
    """Génère des commandes réalistes pour tester le planificateur"""
    
    print("[INFO] Génération de commandes réalistes...")
    
    # Villes marocaines principales
    villes = [
        'Casablanca Centre', 'Casablanca Maarif', 'Casablanca Ain Diab',
        'Rabat Agdal', 'Rabat Hassan', 'Rabat Souissi',
        'Marrakech Gueliz', 'Marrakech Médina', 'Marrakech Hivernage',
        'Fès Médina', 'Fès Ville Nouvelle', 'Fès Saiss',
        'Tanger Ville', 'Tanger Malabata', 'Tanger Ibn Batouta',
        'Agadir Centre', 'Agadir Talborjt', 'Agadir Founty',
        'Meknès Centre', 'Meknès Hamria', 'Meknès Toulal',
        'Oujda Centre', 'Oujda Lazaret', 'Oujda Sidi Maâfa'
    ]
    
    # Types de marchandises
    marchandises = [
        'Documents administratifs', 'Équipements informatiques', 'Produits pharmaceutiques',
        'Pièces automobiles', 'Vêtements et textiles', 'Produits alimentaires',
        'Matériel médical', 'Livres et fournitures scolaires', 'Produits cosmétiques',
        'Électroménager', 'Meubles et décoration', 'Produits artisanaux',
        'Matériel de construction', 'Produits chimiques', 'Équipements sportifs'
    ]
    
    # Récupérer les clients existants
    clients = list(User.objects.filter(role='client'))
    if not clients:
        print("[WARNING] Aucun client trouvé")
        return
    
    # Générer 50 commandes variées
    commandes_creees = []
    
    for i in range(50):
        client = random.choice(clients)
        origine = random.choice(villes)
        destination = random.choice([v for v in villes if v != origine])
        
        # Poids réaliste selon le type de marchandise
        marchandise = random.choice(marchandises)
        if 'Documents' in marchandise or 'Livres' in marchandise:
            poids = round(random.uniform(0.5, 5.0), 2)
        elif 'Équipements' in marchandise or 'Matériel' in marchandise:
            poids = round(random.uniform(10.0, 100.0), 2)
        elif 'Électroménager' in marchandise or 'Meubles' in marchandise:
            poids = round(random.uniform(50.0, 500.0), 2)
        else:
            poids = round(random.uniform(5.0, 50.0), 2)
        
        # Date de livraison dans les 7 prochains jours
        date_livraison = timezone.now() + timedelta(
            days=random.randint(0, 7),
            hours=random.randint(8, 18)
        )
        
        # Priorité réaliste
        priorites = ['basse', 'normale', 'haute', 'urgente']
        weights = [0.15, 0.60, 0.20, 0.05]  # 60% normale, 20% haute, 15% basse, 5% urgente
        priorite = random.choices(priorites, weights=weights)[0]
        
        # Statut réaliste
        statuts = ['en_attente', 'affectee', 'planifiee']
        weights_statut = [0.70, 0.20, 0.10]  # 70% en attente, 20% affectée, 10% planifiée
        statut = random.choices(statuts, weights=weights_statut)[0]
        
        try:
            commande = Commande.objects.create(
                client=client,
                origine=origine,
                destination=destination,
                description_marchandise=marchandise,
                poids=Decimal(str(poids)),
                date_livraison_prevue=date_livraison,
                priorite=priorite,
                statut=statut,
                notes=f"Commande générée automatiquement - {marchandise.lower()}"
            )
            
            # Si la commande est affectée ou planifiée, lui assigner un transporteur
            if statut in ['affectee', 'planifiee']:
                transporteurs = User.objects.filter(role='transporteur', is_active=True)
                if transporteurs.exists():
                    commande.transporteur = random.choice(transporteurs)
                    commande.save()
            
            commandes_creees.append(commande)
            
        except Exception as e:
            print(f"[ERROR] Erreur lors de la création de la commande {i+1}: {e}")
    
    print(f"[OK] {len(commandes_creees)} commandes créées avec succès")
    
    # Statistiques des commandes créées
    stats = {}
    for commande in commandes_creees:
        stats[commande.priorite] = stats.get(commande.priorite, 0) + 1
    
    print("\nRépartition par priorité:")
    for priorite, count in stats.items():
        print(f"  - {priorite.title()}: {count} commandes")

def generate_realistic_vehicules():
    """Génère des véhicules réalistes pour les transporteurs"""
    
    print("\n[INFO] Génération de véhicules réalistes...")
    
    # Immatriculations marocaines réalistes
    lettres = ['A', 'B', 'D', 'H', 'J', 'L', 'M', 'R', 'T', 'U', 'W']
    chiffres_region = ['1', '2', '3', '4', '5', '6', '7', '8', '9']
    
    def generer_immatriculation():
        return f"{random.randint(10000, 99999)}-{random.choice(lettres)}-{random.choice(chiffres_region)}"
    
    # Types de véhicules avec capacités réalistes
    types_vehicules = [
        ('camionnette', 1000, 3500),
        ('camion', 3500, 12000),
        ('semi_remorque', 12000, 40000)
    ]
    
    # Marques et modèles
    marques_modeles = {
        'camionnette': [
            ('Renault', 'Master'), ('Mercedes', 'Sprinter'), ('Ford', 'Transit'),
            ('Iveco', 'Daily'), ('Peugeot', 'Boxer'), ('Fiat', 'Ducato')
        ],
        'camion': [
            ('Mercedes', 'Actros'), ('Volvo', 'FH'), ('Scania', 'R-Series'),
            ('MAN', 'TGX'), ('DAF', 'XF'), ('Iveco', 'Stralis')
        ],
        'semi_remorque': [
            ('Mercedes', 'Actros'), ('Volvo', 'FH16'), ('Scania', 'R730'),
            ('MAN', 'TGX'), ('DAF', 'XF105'), ('Renault', 'T-High')
        ]
    }
    
    couleurs = ['Blanc', 'Bleu', 'Rouge', 'Gris', 'Noir', 'Vert', 'Jaune']
    
    # Récupérer les transporteurs
    transporteurs = list(User.objects.filter(role='transporteur'))
    if not transporteurs:
        print("[WARNING] Aucun transporteur trouvé")
        return
    
    vehicules_crees = []
    
    for transporteur in transporteurs:
        # Chaque transporteur a entre 1 et 4 véhicules
        nb_vehicules = random.randint(1, 4)
        
        for i in range(nb_vehicules):
            type_vehicule, capacite_min, capacite_max = random.choice(types_vehicules)
            capacite = random.randint(capacite_min, capacite_max)
            
            marque, modele = random.choice(marques_modeles[type_vehicule])
            couleur = random.choice(couleurs)
            annee = random.randint(2015, 2023)
            
            try:
                vehicule = Vehicule.objects.create(
                    transporteur=transporteur,
                    immatriculation=generer_immatriculation(),
                    type_vehicule=type_vehicule,
                    capacite_max=Decimal(str(capacite)),
                    disponible=random.choice([True, True, True, False]),  # 75% disponibles
                    marque=marque,
                    modele=modele,
                    annee=annee,
                    couleur=couleur,
                    notes=f"Véhicule {marque} {modele} {annee} - Capacité {capacite}kg"
                )
                
                vehicules_crees.append(vehicule)
                
            except Exception as e:
                print(f"[ERROR] Erreur lors de la création du véhicule: {e}")
    
    print(f"[OK] {len(vehicules_crees)} véhicules créés")
    
    # Statistiques des véhicules
    stats_vehicules = {}
    for vehicule in vehicules_crees:
        stats_vehicules[vehicule.type_vehicule] = stats_vehicules.get(vehicule.type_vehicule, 0) + 1
    
    print("\nRépartition par type:")
    for type_v, count in stats_vehicules.items():
        print(f"  - {type_v.replace('_', ' ').title()}: {count} véhicules")

def generate_notifications():
    """Génère des notifications réalistes"""
    
    print("\n[INFO] Génération de notifications...")
    
    users = list(User.objects.all())
    if not users:
        return
    
    types_notifications = [
        ('nouvelle_commande', 'Nouvelle commande reçue'),
        ('commande_affectee', 'Commande affectée à un transporteur'),
        ('commande_planifiee', 'Commande planifiée dans une tournée'),
        ('tournee_creee', 'Nouvelle tournée créée'),
        ('statut_livraison', 'Mise à jour du statut de livraison'),
        ('system', 'Notification système')
    ]
    
    messages_exemples = {
        'nouvelle_commande': [
            'Une nouvelle commande a été créée et attend traitement.',
            'Nouvelle demande de transport reçue.',
            'Commande urgente nécessitant une attention immédiate.'
        ],
        'commande_affectee': [
            'Votre commande a été affectée à un transporteur.',
            'Un transporteur a accepté votre commande.',
            'Commande assignée avec succès.'
        ],
        'commande_planifiee': [
            'Votre commande a été planifiée dans une tournée.',
            'Planification terminée - livraison prévue demain.',
            'Tournée optimisée incluant votre commande.'
        ],
        'tournee_creee': [
            'Une nouvelle tournée vous a été assignée.',
            'Tournée créée avec 5 commandes à livrer.',
            'Itinéraire optimisé disponible.'
        ],
        'statut_livraison': [
            'Votre commande est en cours de livraison.',
            'Livraison terminée avec succès.',
            'Retard signalé sur votre livraison.'
        ],
        'system': [
            'Maintenance système programmée ce soir.',
            'Nouvelle fonctionnalité disponible.',
            'Mise à jour de sécurité appliquée.'
        ]
    }
    
    notifications_creees = []
    
    for i in range(30):  # 30 notifications
        user = random.choice(users)
        type_notif, titre_base = random.choice(types_notifications)
        
        # Adapter le type selon le rôle de l'utilisateur
        if user.role == 'client' and type_notif in ['tournee_creee']:
            type_notif = 'commande_planifiee'
        elif user.role == 'transporteur' and type_notif in ['nouvelle_commande']:
            type_notif = 'tournee_creee'
        
        message = random.choice(messages_exemples[type_notif])
        priorite = random.choices(['low', 'normal', 'high', 'urgent'], weights=[0.3, 0.5, 0.15, 0.05])[0]
        lu = random.choice([True, False])
        
        # Date de création dans les 7 derniers jours
        date_creation = timezone.now() - timedelta(
            days=random.randint(0, 7),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        try:
            notification = Notification.objects.create(
                utilisateur=user,
                type_notification=type_notif,
                titre=titre_base,
                message=message,
                priority=priorite,
                lu=lu,
                date_creation=date_creation
            )
            
            if lu:
                notification.date_lecture = date_creation + timedelta(hours=random.randint(1, 48))
                notification.save()
            
            notifications_creees.append(notification)
            
        except Exception as e:
            print(f"[ERROR] Erreur lors de la création de la notification: {e}")
    
    print(f"[OK] {len(notifications_creees)} notifications créées")

if __name__ == "__main__":
    print("="*60)
    print("GÉNÉRATION DE DONNÉES RÉALISTES POUR LE PLANIFICATEUR")
    print("="*60)
    
    try:
        generate_realistic_commandes()
        generate_realistic_vehicules()
        generate_notifications()
        
        print("\n" + "="*60)
        print("[SUCCESS] Données générées avec succès!")
        print("="*60)
        
        # Statistiques finales
        print(f"\nStatistiques finales:")
        print(f"📦 Commandes totales: {Commande.objects.count()}")
        print(f"🚛 Véhicules totaux: {Vehicule.objects.count()}")
        print(f"🔔 Notifications totales: {Notification.objects.count()}")
        print(f"👥 Utilisateurs totaux: {User.objects.count()}")
        
        print(f"\nRépartition des commandes par statut:")
        for statut in ['en_attente', 'affectee', 'planifiee', 'en_cours', 'livree']:
            count = Commande.objects.filter(statut=statut).count()
            print(f"  - {statut.replace('_', ' ').title()}: {count}")
        
        print(f"\nRépartition des commandes par priorité:")
        for priorite in ['basse', 'normale', 'haute', 'urgente']:
            count = Commande.objects.filter(priorite=priorite).count()
            print(f"  - {priorite.title()}: {count}")
        
        print("\n🎉 Le système est maintenant prêt avec des données réalistes!")
        
    except Exception as e:
        print(f"\n[ERROR] Erreur lors de la génération: {str(e)}")
        import traceback
        traceback.print_exc()