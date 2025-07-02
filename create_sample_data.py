#!/usr/bin/env python
"""
Script pour créer des données d'exemple pour le système de transport
"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'transport_system.settings')
django.setup()

from core.models import User, Commande, Vehicule, ConfigurationSysteme
import uuid

def create_sample_data():
    print("Création des données d'exemple...")
    
    # 1. Créer un superutilisateur admin
    if not User.objects.filter(username='admin').exists():
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@transport.com',
            password='admin123',
            role='admin',
            first_name='Administrateur',
            last_name='Système'
        )
        print(f"[OK] Superutilisateur cree: {admin.username}")
    
    # 2. Créer des utilisateurs de test
    users_data = [
        {
            'username': 'client1',
            'email': 'client1@test.com',
            'password': 'test123',
            'role': 'client',
            'first_name': 'Ahmed',
            'last_name': 'Benali',
            'telephone': '0612345678',
            'adresse': 'Casablanca, Maroc'
        },
        {
            'username': 'client2',
            'email': 'client2@test.com',
            'password': 'test123',
            'role': 'client',
            'first_name': 'Fatima',
            'last_name': 'Alami',
            'telephone': '0623456789',
            'adresse': 'Rabat, Maroc'
        },
        {
            'username': 'transporteur1',
            'email': 'transporteur1@test.com',
            'password': 'test123',
            'role': 'transporteur',
            'first_name': 'Mohamed',
            'last_name': 'Tazi',
            'telephone': '0634567890',
            'adresse': 'Casablanca, Maroc'
        },
        {
            'username': 'transporteur2',
            'email': 'transporteur2@test.com',
            'password': 'test123',
            'role': 'transporteur',
            'first_name': 'Youssef',
            'last_name': 'Idrissi',
            'telephone': '0645678901',
            'adresse': 'Marrakech, Maroc'
        },
        {
            'username': 'planificateur1',
            'email': 'planificateur1@test.com',
            'password': 'test123',
            'role': 'planificateur',
            'first_name': 'Aicha',
            'last_name': 'Bennani',
            'telephone': '0656789012',
            'adresse': 'Casablanca, Maroc'
        }
    ]
    
    created_users = {}
    for user_data in users_data:
        if not User.objects.filter(username=user_data['username']).exists():
            user = User.objects.create_user(**user_data)
            created_users[user_data['role']] = created_users.get(user_data['role'], []) + [user]
            print(f"[OK] Utilisateur cree: {user.username} ({user.role})")
    
    # 3. Créer des véhicules pour les transporteurs
    transporteurs = User.objects.filter(role='transporteur')
    vehicules_data = [
        {
            'immatriculation': '123456-A-12',
            'type_vehicule': 'camionnette',
            'capacite_poids': 1500.0,
            'capacite_volume': 10.0
        },
        {
            'immatriculation': '789012-B-34',
            'type_vehicule': 'camion',
            'capacite_poids': 5000.0,
            'capacite_volume': 25.0
        },
        {
            'immatriculation': '345678-C-56',
            'type_vehicule': 'semi_remorque',
            'capacite_poids': 15000.0,
            'capacite_volume': 50.0
        }
    ]
    
    for i, transporteur in enumerate(transporteurs):
        if i < len(vehicules_data):
            vehicule_data = vehicules_data[i]
            vehicule_data['transporteur'] = transporteur
            
            if not Vehicule.objects.filter(immatriculation=vehicule_data['immatriculation']).exists():
                vehicule = Vehicule.objects.create(**vehicule_data)
                print(f"[OK] Vehicule cree: {vehicule.immatriculation} pour {transporteur.username}")
    
    # 4. Créer des commandes d'exemple
    clients = User.objects.filter(role='client')
    transporteurs = User.objects.filter(role='transporteur')
    
    if clients.exists() and transporteurs.exists():
        commandes_data = [
            {
                'client': clients[0],
                'transporteur': transporteurs[0] if transporteurs.exists() else None,
                'adresse_enlevement': 'Avenue Mohammed V, Casablanca',
                'adresse_livraison': 'Avenue Allal Ben Abdellah, Rabat',
                'latitude_enlevement': 33.5731,
                'longitude_enlevement': -7.5898,
                'latitude_livraison': 34.0209,
                'longitude_livraison': -6.8416,
                'description_marchandise': 'Matériel informatique',
                'poids': 50.0,
                'volume': 2.0,
                'statut': 'confirmee',
                'date_enlevement_prevue': timezone.now() + timedelta(days=1),
                'date_livraison_prevue': timezone.now() + timedelta(days=2)
            },
            {
                'client': clients[1] if len(clients) > 1 else clients[0],
                'adresse_enlevement': 'Boulevard Zerktouni, Casablanca',
                'adresse_livraison': 'Avenue Hassan II, Marrakech',
                'latitude_enlevement': 33.5892,
                'longitude_enlevement': -7.6031,
                'latitude_livraison': 31.6295,
                'longitude_livraison': -7.9811,
                'description_marchandise': 'Produits alimentaires',
                'poids': 200.0,
                'volume': 5.0,
                'statut': 'en_attente',
                'date_enlevement_prevue': timezone.now() + timedelta(days=3),
                'date_livraison_prevue': timezone.now() + timedelta(days=4)
            },
            {
                'client': clients[0],
                'transporteur': transporteurs[1] if len(transporteurs) > 1 else transporteurs[0],
                'adresse_enlevement': 'Quartier Agdal, Rabat',
                'adresse_livraison': 'Zone Industrielle, Tanger',
                'latitude_enlevement': 34.0181,
                'longitude_enlevement': -6.8414,
                'latitude_livraison': 35.7595,
                'longitude_livraison': -5.8340,
                'description_marchandise': 'Pièces automobiles',
                'poids': 800.0,
                'volume': 15.0,
                'statut': 'en_cours',
                'date_enlevement_prevue': timezone.now() - timedelta(hours=2),
                'date_livraison_prevue': timezone.now() + timedelta(hours=6),
                'date_enlevement_reelle': timezone.now() - timedelta(hours=1)
            }
        ]
        
        for i, commande_data in enumerate(commandes_data):
            commande_data['numero'] = f"CMD-{uuid.uuid4().hex[:8].upper()}"
            commande = Commande.objects.create(**commande_data)
            print(f"[OK] Commande creee: {commande.numero}")
    
    # 5. Créer des configurations système
    configurations = [
        {
            'cle': 'system_name',
            'valeur': 'Système de Transport de Marchandises',
            'description': 'Nom du système'
        },
        {
            'cle': 'max_commandes_par_jour',
            'valeur': '100',
            'description': 'Nombre maximum de commandes par jour'
        },
        {
            'cle': 'delai_livraison_standard',
            'valeur': '24',
            'description': 'Délai de livraison standard en heures'
        },
        {
            'cle': 'email_notifications',
            'valeur': 'true',
            'description': 'Activer les notifications par email'
        }
    ]
    
    for config_data in configurations:
        config, created = ConfigurationSysteme.objects.get_or_create(
            cle=config_data['cle'],
            defaults={
                'valeur': config_data['valeur'],
                'description': config_data['description']
            }
        )
        if created:
            print(f"[OK] Configuration creee: {config.cle}")
    
    print("\nDonnees d'exemple creees avec succes!")
    print("\nComptes de test crees:")
    print("- Admin: admin / admin123")
    print("- Client: client1 / test123")
    print("- Client: client2 / test123") 
    print("- Transporteur: transporteur1 / test123")
    print("- Transporteur: transporteur2 / test123")
    print("- Planificateur: planificateur1 / test123")
    print("\nVous pouvez maintenant demarrer le serveur avec: python manage.py runserver")

if __name__ == '__main__':
    create_sample_data()