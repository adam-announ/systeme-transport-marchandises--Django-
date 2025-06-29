#!/usr/bin/env python
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'transport_system.settings')
django.setup()

from utilisateurs.models import User, Commande
from datetime import datetime, timedelta
from django.utils import timezone

def create_test_commandes():
    # Récupérer ou créer des clients
    clients = []
    for i in range(3):
        client, created = User.objects.get_or_create(
            username=f'client{i+1}',
            defaults={
                'email': f'client{i+1}@test.com',
                'password': 'password123',
                'role': 'client',
                'first_name': f'Client{i+1}',
                'last_name': 'Test',
                'is_active': True
            }
        )
        clients.append(client)
    
    # Créer des commandes de test
    commandes_data = [
        {
            'origine': 'Casablanca Centre',
            'destination': 'Rabat Agdal',
            'description_marchandise': 'Matériel informatique',
            'poids': 25.5,
            'priorite': 'urgente'
        },
        {
            'origine': 'Casablanca Maarif',
            'destination': 'Salé Médina',
            'description_marchandise': 'Documents administratifs',
            'poids': 2.0,
            'priorite': 'haute'
        },
        {
            'origine': 'Mohammedia Port',
            'destination': 'Témara Centre',
            'description_marchandise': 'Pièces automobiles',
            'poids': 45.0,
            'priorite': 'normale'
        },
        {
            'origine': 'Casablanca Anfa',
            'destination': 'Kenitra Ville',
            'description_marchandise': 'Produits pharmaceutiques',
            'poids': 15.8,
            'priorite': 'urgente'
        },
        {
            'origine': 'Ain Sebaa',
            'destination': 'Rabat Hassan',
            'description_marchandise': 'Équipements électroniques',
            'poids': 32.0,
            'priorite': 'haute'
        },
        {
            'origine': 'Casablanca Sidi Bernoussi',
            'destination': 'Salé Tabriquet',
            'description_marchandise': 'Textiles',
            'poids': 18.5,
            'priorite': 'normale'
        }
    ]
    
    created_count = 0
    for i, data in enumerate(commandes_data):
        # Vérifier si la commande existe déjà
        if not Commande.objects.filter(
            origine=data['origine'],
            destination=data['destination']
        ).exists():
            
            commande = Commande.objects.create(
                client=clients[i % len(clients)],
                origine=data['origine'],
                destination=data['destination'],
                description_marchandise=data['description_marchandise'],
                poids=data['poids'],
                priorite=data['priorite'],
                date_livraison_prevue=timezone.now() + timedelta(days=1),
                statut='en_attente',
                notes=f'Commande de test #{i+1}'
            )
            created_count += 1
            print(f"✅ Commande créée: #{commande.id} - {data['origine']} → {data['destination']}")
    
    print(f"\n🎉 {created_count} nouvelles commandes créées!")
    print(f"📊 Total commandes en attente: {Commande.objects.filter(statut='en_attente').count()}")

if __name__ == '__main__':
    create_test_commandes()