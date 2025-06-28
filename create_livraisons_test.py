import os
import django
import sys
from datetime import datetime, timedelta
from decimal import Decimal

# Configuration Django
sys.path.append('c:\\Users\\HP\\Desktop\\transport_system')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'transport_system.settings')
django.setup()

from utilisateurs.models import User, Commande, Vehicule, Livraison

print("=== CRÉATION DE LIVRAISONS DE TEST ===")

# Récupérer un transporteur
try:
    transporteur = User.objects.get(username='transporteur1')
    print(f"Transporteur: {transporteur.username}")
    
    # Créer un véhicule si nécessaire
    vehicule, created = Vehicule.objects.get_or_create(
        transporteur=transporteur,
        immatriculation='ABC-123',
        defaults={
            'type_vehicule': 'camion',
            'capacite_max': Decimal('1000.0'),
            'disponible': True
        }
    )
    if created:
        print(f"Véhicule créé: {vehicule.immatriculation}")
    
    # Créer des commandes avec livraisons
    commandes_data = [
        {
            'client': User.objects.get(username='client1'),
            'origine': 'Casablanca Centre',
            'destination': 'Rabat Agdal',
            'description_marchandise': 'Documents',
            'poids': Decimal('5.0'),
            'statut': 'affectee',
            'priorite': 'normale'
        },
        {
            'client': User.objects.get(username='client2'),
            'origine': 'Casablanca Maarif',
            'destination': 'Salé Médina',
            'description_marchandise': 'Équipements',
            'poids': Decimal('12.0'),
            'statut': 'affectee',
            'priorite': 'haute'
        },
        {
            'client': User.objects.get(username='client3'),
            'origine': 'Casablanca Ain Chock',
            'destination': 'Témara Centre',
            'description_marchandise': 'Produits',
            'poids': Decimal('8.0'),
            'statut': 'affectee',
            'priorite': 'urgente'
        }
    ]
    
    livraisons_creees = 0
    
    for cmd_data in commandes_data:
        # Créer la commande
        commande = Commande.objects.create(
            client=cmd_data['client'],
            transporteur=transporteur,
            origine=cmd_data['origine'],
            destination=cmd_data['destination'],
            description_marchandise=cmd_data['description_marchandise'],
            poids=cmd_data['poids'],
            date_livraison_prevue=datetime.now() + timedelta(days=1),
            statut=cmd_data['statut'],
            priorite=cmd_data['priorite']
        )
        
        # Créer la livraison
        livraison = Livraison.objects.create(
            commande=commande,
            vehicule=vehicule,
            statut='en_attente'
        )
        
        livraisons_creees += 1
        print(f"✅ Livraison #{livraison.id} créée: {commande.origine} → {commande.destination}")
    
    print(f"\n🎉 {livraisons_creees} livraisons créées avec succès!")
    print(f"\n📋 Pour tester l'optimisation:")
    print(f"1. Connectez-vous avec: transporteur1 / trans123")
    print(f"2. Allez sur 'Optimiser itinéraire'")
    print(f"3. Sélectionnez les livraisons et cliquez 'Optimiser'")
    
except Exception as e:
    print(f"❌ Erreur: {str(e)}")
    print("Assurez-vous d'avoir exécuté create_users.py d'abord")

print("\n=== TERMINÉ ===")