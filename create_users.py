import os
import django
import sys

# Configuration Django
sys.path.append('c:\\Users\\HP\\Desktop\\transport_system')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'transport_system.settings')
django.setup()

from utilisateurs.models import User, Commande

# Supprimer tous les utilisateurs existants
User.objects.all().delete()

# Créer les utilisateurs de test
users_data = [
    # Administrateurs
    {
        'username': 'admin',
        'email': 'admin@transport.com',
        'password': 'admin123',
        'role': 'admin',
        'first_name': 'Admin',
        'last_name': 'System',
        'phone': '+212600000001',
        'is_active': True
    },
    {
        'username': 'superadmin',
        'email': 'superadmin@transport.com',
        'password': 'super123',
        'role': 'admin',
        'first_name': 'Super',
        'last_name': 'Admin',
        'phone': '+212600000002',
        'is_active': True
    },
    
    # Planificateurs
    {
        'username': 'planificateur1',
        'email': 'planif1@transport.com',
        'password': 'planif123',
        'role': 'planificateur',
        'first_name': 'Ahmed',
        'last_name': 'Benali',
        'phone': '+212600000003',
        'is_active': True
    },
    {
        'username': 'planificateur2',
        'email': 'planif2@transport.com',
        'password': 'planif123',
        'role': 'planificateur',
        'first_name': 'Fatima',
        'last_name': 'Zahra',
        'phone': '+212600000004',
        'is_active': True
    },
    {
        'username': 'planificateur3',
        'email': 'planif3@transport.com',
        'password': 'planif123',
        'role': 'planificateur',
        'first_name': 'Karim',
        'last_name': 'Mansouri',
        'phone': '+212600000013',
        'is_active': True
    },
    
    # Transporteurs
    {
        'username': 'transporteur1',
        'email': 'transport1@transport.com',
        'password': 'trans123',
        'role': 'transporteur',
        'first_name': 'Mohamed',
        'last_name': 'Alami',
        'phone': '+212600000005',
        'is_active': True
    },
    {
        'username': 'transporteur2',
        'email': 'transport2@transport.com',
        'password': 'trans123',
        'role': 'transporteur',
        'first_name': 'Youssef',
        'last_name': 'Tazi',
        'phone': '+212600000006',
        'is_active': True
    },
    {
        'username': 'transporteur3',
        'email': 'transport3@transport.com',
        'password': 'trans123',
        'role': 'transporteur',
        'first_name': 'Rachid',
        'last_name': 'Bennani',
        'phone': '+212600000007',
        'is_active': True
    },
    
    # Clients
    {
        'username': 'client1',
        'email': 'client1@transport.com',
        'password': 'client123',
        'role': 'client',
        'first_name': 'Aicha',
        'last_name': 'Idrissi',
        'phone': '+212600000008',
        'is_active': True
    },
    {
        'username': 'client2',
        'email': 'client2@transport.com',
        'password': 'client123',
        'role': 'client',
        'first_name': 'Omar',
        'last_name': 'Fassi',
        'phone': '+212600000009',
        'is_active': True
    },
    {
        'username': 'client3',
        'email': 'client3@transport.com',
        'password': 'client123',
        'role': 'client',
        'first_name': 'Khadija',
        'last_name': 'Berrada',
        'phone': '+212600000010',
        'is_active': True
    },
    {
        'username': 'client4',
        'email': 'client4@transport.com',
        'password': 'client123',
        'role': 'client',
        'first_name': 'Hassan',
        'last_name': 'Cherkaoui',
        'phone': '+212600000011',
        'is_active': True
    },
    {
        'username': 'client5',
        'email': 'client5@transport.com',
        'password': 'client123',
        'role': 'client',
        'first_name': 'Laila',
        'last_name': 'Amrani',
        'phone': '+212600000012',
        'is_active': True
    }
]

# Créer les utilisateurs
created_users = []
for user_data in users_data:
    user = User.objects.create(**user_data)
    created_users.append(user)
    print(f"[OK] Utilisateur cree: {user.username} ({user.role}) - {user.email}")

print(f"\n[SUCCESS] {len(created_users)} utilisateurs crees avec succes!")

print("\n" + "="*60)
print("COMPTES DE CONNEXION DISPONIBLES")
print("="*60)

print("\n[ADMIN] ADMINISTRATEURS:")
print("Username: admin | Password: admin123 | Email: admin@transport.com")
print("Username: superadmin | Password: super123 | Email: superadmin@transport.com")

print("\n[PLANIF] PLANIFICATEURS:")
print("Username: planificateur1 | Password: planif123 | Email: planif1@transport.com")
print("Username: planificateur2 | Password: planif123 | Email: planif2@transport.com")
print("Username: planificateur3 | Password: planif123 | Email: planif3@transport.com")

print("\n[TRANSPORT] TRANSPORTEURS:")
print("Username: transporteur1 | Password: trans123 | Email: transport1@transport.com")
print("Username: transporteur2 | Password: trans123 | Email: transport2@transport.com")
print("Username: transporteur3 | Password: trans123 | Email: transport3@transport.com")

print("\n[CLIENT] CLIENTS:")
print("Username: client1 | Password: client123 | Email: client1@transport.com")
print("Username: client2 | Password: client123 | Email: client2@transport.com")
print("Username: client3 | Password: client123 | Email: client3@transport.com")
print("Username: client4 | Password: client123 | Email: client4@transport.com")
print("Username: client5 | Password: client123 | Email: client5@transport.com")

# Créer des commandes de test
from datetime import datetime, timedelta
from decimal import Decimal

print("\n[INFO] Création de commandes de test...")

try:

# Commandes pour les clients
commandes_test = [
    {
        'client': User.objects.get(username='client1'),
        'origine': 'Casablanca Centre',
        'destination': 'Rabat Agdal',
        'description_marchandise': 'Documents administratifs',
        'poids': Decimal('2.5'),
        'date_livraison_prevue': datetime.now() + timedelta(days=1),
        'statut': 'en_attente',
        'priorite': 'normale'
    },
    {
        'client': User.objects.get(username='client2'),
        'origine': 'Marrakech Gueliz',
        'destination': 'Casablanca Maarif',
        'description_marchandise': 'Équipements informatiques',
        'poids': Decimal('15.0'),
        'date_livraison_prevue': datetime.now() + timedelta(days=2),
        'statut': 'en_attente',
        'priorite': 'haute'
    },
    {
        'client': User.objects.get(username='client3'),
        'origine': 'Fès Médina',
        'destination': 'Tanger Ville',
        'description_marchandise': 'Produits artisanaux',
        'poids': Decimal('8.3'),
        'date_livraison_prevue': datetime.now() + timedelta(hours=12),
        'statut': 'affectee',
        'priorite': 'urgente',
        'transporteur': User.objects.get(username='transporteur1')
    }
]

    for cmd_data in commandes_test:
        commande = Commande.objects.create(**cmd_data)
        print(f"[OK] Commande #{commande.id} créée: {commande.origine} → {commande.destination}")
    
    print(f"\n[SUCCESS] {len(commandes_test)} commandes de test créées!")
    
except Exception as e:
    print(f"[ERROR] Erreur lors de la création des commandes: {str(e)}")
    print("[INFO] Les utilisateurs ont été créés avec succès, mais pas les commandes de test.")

print("\n" + "="*60)
print("[WEB] ACCÈS AU SYSTÈME:")
print("URL: http://127.0.0.1:8000/")
print("API: http://127.0.0.1:8000/api/")
print("Connexion: http://127.0.0.1:8000/login/")
print("Inscription: http://127.0.0.1:8000/register/")
print("="*60)

print("\n[AMÉLIORATIONS APPORTÉES:]")
print("✅ API REST avec Django REST Framework")
print("✅ Interface utilisateur moderne et responsive")
print("✅ Composants JavaScript réutilisables")
print("✅ Service d'optimisation de tournées")
print("✅ Notifications en temps réel")
print("✅ Dashboard client amélioré")
print("✅ Gestion avancée des statuts")
print("✅ Support CORS pour applications frontend")
print("="*60)