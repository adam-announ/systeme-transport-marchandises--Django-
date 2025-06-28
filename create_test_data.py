import os
import django
import sys
from datetime import datetime, timedelta
from decimal import Decimal
import random

# Configuration Django
sys.path.append('c:\\Users\\HP\\Desktop\\transport_system')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'transport_system.settings')
django.setup()

from utilisateurs.models import User, Commande, Notification

print("=== CRÉATION DE DONNÉES DE TEST POUR LE DASHBOARD ===")

# Récupérer les utilisateurs existants
clients = User.objects.filter(role='client')
transporteurs = User.objects.filter(role='transporteur')

if not clients.exists():
    print("❌ Aucun client trouvé. Exécutez d'abord create_users.py")
    sys.exit(1)

# Villes marocaines pour les trajets
villes = [
    'Casablanca', 'Rabat', 'Marrakech', 'Fès', 'Tanger', 'Agadir', 
    'Meknès', 'Oujda', 'Kenitra', 'Tétouan', 'Safi', 'El Jadida'
]

# Types de marchandises
marchandises = [
    'Documents administratifs', 'Équipements informatiques', 'Produits artisanaux',
    'Matériel médical', 'Pièces automobiles', 'Produits alimentaires',
    'Vêtements et textiles', 'Livres et fournitures', 'Électroménager',
    'Matériaux de construction', 'Produits cosmétiques', 'Jouets et jeux'
]

# Statuts possibles
statuts = ['en_attente', 'affectee', 'en_cours', 'livree', 'annulee']
priorites = ['basse', 'normale', 'haute', 'urgente']

print(f"Création de commandes pour {clients.count()} clients...")

# Créer des commandes pour les 3 derniers mois
commandes_creees = 0
notifications_creees = 0

for client in clients:
    # Créer entre 5 et 15 commandes par client
    nb_commandes = random.randint(5, 15)
    
    for i in range(nb_commandes):
        # Date aléatoire dans les 3 derniers mois
        jours_arriere = random.randint(1, 90)
        date_creation = datetime.now() - timedelta(days=jours_arriere)
        
        # Sélectionner origine et destination différentes
        origine = random.choice(villes)
        destination = random.choice([v for v in villes if v != origine])
        
        # Statut basé sur l'ancienneté
        if jours_arriere > 30:
            statut = random.choice(['livree', 'annulee'])
        elif jours_arriere > 7:
            statut = random.choice(['livree', 'en_cours', 'affectee'])
        else:
            statut = random.choice(['en_attente', 'affectee', 'en_cours'])
        
        # Transporteur si affecté
        transporteur = None
        if statut in ['affectee', 'en_cours', 'livree']:
            transporteur = random.choice(transporteurs) if transporteurs.exists() else None
        
        # Prix si livré
        prix = None
        if statut == 'livree':
            prix = Decimal(str(random.uniform(50, 500)))
        
        commande = Commande.objects.create(
            client=client,
            transporteur=transporteur,
            origine=f"{origine} {random.choice(['Centre', 'Gare', 'Aéroport', 'Zone Industrielle'])}",
            destination=f"{destination} {random.choice(['Centre', 'Gare', 'Aéroport', 'Zone Industrielle'])}",
            description_marchandise=random.choice(marchandises),
            poids=Decimal(str(random.uniform(0.5, 50.0))),
            date_creation=date_creation,
            date_livraison_prevue=date_creation + timedelta(days=random.randint(1, 7)),
            statut=statut,
            priorite=random.choice(priorites),
            prix=prix,
            notes=f"Commande de test créée automatiquement"
        )
        
        commandes_creees += 1
        
        # Créer des notifications pour certaines commandes
        if random.random() < 0.3:  # 30% de chance
            if statut == 'affectee':
                notif_type = 'commande_affectee'
                titre = 'Commande acceptée'
                message = f'Votre commande #{commande.id} a été acceptée par un transporteur.'
            elif statut == 'livree':
                notif_type = 'statut_livraison'
                titre = 'Commande livrée'
                message = f'Votre commande #{commande.id} a été livrée avec succès.'
            else:
                notif_type = 'nouvelle_commande'
                titre = 'Commande créée'
                message = f'Votre commande #{commande.id} a été créée et est en attente.'
            
            Notification.objects.create(
                utilisateur=client,
                type_notification=notif_type,
                titre=titre,
                message=message,
                date_creation=date_creation + timedelta(hours=random.randint(1, 24))
            )
            notifications_creees += 1

print(f"\n✅ {commandes_creees} commandes créées")
print(f"✅ {notifications_creees} notifications créées")

# Statistiques finales
print(f"\n=== STATISTIQUES GLOBALES ===")
total_commandes = Commande.objects.count()
print(f"Total commandes: {total_commandes}")

for statut_code, statut_label in Commande.STATUS_CHOICES:
    count = Commande.objects.filter(statut=statut_code).count()
    print(f"- {statut_label}: {count}")

total_notifications = Notification.objects.count()
print(f"\nTotal notifications: {total_notifications}")

print(f"\n=== DASHBOARD CLIENT AMÉLIORÉ ===")
print("✅ Statistiques détaillées avec sous-totaux")
print("✅ Graphiques interactifs (Chart.js)")
print("✅ Tableau des commandes enrichi")
print("✅ Notifications avec icônes")
print("✅ Actions rapides modernisées")
print("✅ Animations et effets visuels")
print("✅ Design responsive et moderne")

print(f"\n🌐 Connectez-vous avec un client pour voir le dashboard amélioré:")
for client in clients[:3]:
    print(f"   Username: {client.username} | Password: client123")

print(f"\n=== DONNÉES DE TEST CRÉÉES AVEC SUCCÈS ===")