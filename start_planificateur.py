import os
import django
import sys

# Configuration Django
sys.path.append('c:\\Users\\HP\\Desktop\\transport_system')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'transport_system.settings')
django.setup()

from django.db import connection
from utilisateurs.models import *
from datetime import datetime, timedelta
from django.utils import timezone
from decimal import Decimal
import random

def setup_basic_data():
    """Configuration de base pour le planificateur"""
    
    print("🚀 Configuration du système planificateur...")
    
    # Ajouter les colonnes manquantes si nécessaire
    with connection.cursor() as cursor:
        try:
            # Vérifier et ajouter la colonne priorité
            cursor.execute("PRAGMA table_info(commandes)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'priorite' not in columns:
                print("✅ Ajout de la colonne 'priorite'")
                cursor.execute("ALTER TABLE commandes ADD COLUMN priorite VARCHAR(10) DEFAULT 'normale'")
            
            if 'planificateur_id' not in columns:
                print("✅ Ajout de la colonne 'planificateur_id'")
                cursor.execute("ALTER TABLE commandes ADD COLUMN planificateur_id INTEGER")
                
        except Exception as e:
            print(f"⚠️ Erreur lors de la modification: {e}")
    
    # Mettre à jour les commandes existantes avec des priorités
    commandes = Commande.objects.all()
    if commandes.exists():
        print(f"📦 Mise à jour de {commandes.count()} commandes...")
        
        priorites = ['basse', 'normale', 'haute', 'urgente']
        weights = [0.2, 0.5, 0.2, 0.1]
        
        for commande in commandes:
            if not hasattr(commande, 'priorite') or not commande.priorite:
                nouvelle_priorite = random.choices(priorites, weights=weights)[0]
                commande.priorite = nouvelle_priorite
                commande.save()
    
    # Créer quelques véhicules si nécessaire
    transporteurs = User.objects.filter(role='transporteur')
    for transporteur in transporteurs:
        if not transporteur.vehicules.exists():
            print(f"🚛 Création d'un véhicule pour {transporteur.get_full_name()}")
            
            Vehicule.objects.create(
                transporteur=transporteur,
                immatriculation=f"{random.randint(10000, 99999)}-A-{random.randint(1, 9)}",
                type_vehicule=random.choice(['camionnette', 'camion']),
                capacite_max=Decimal(str(random.randint(1000, 5000))),
                disponible=True,
                marque='Mercedes',
                modele='Sprinter'
            )
    
    print("✅ Configuration terminée!")
    
    # Statistiques
    stats = {
        'commandes': Commande.objects.count(),
        'commandes_en_attente': Commande.objects.filter(statut='en_attente').count(),
        'transporteurs': User.objects.filter(role='transporteur').count(),
        'vehicules': Vehicule.objects.count(),
        'planificateurs': User.objects.filter(role='planificateur').count()
    }
    
    print(f"\n📊 Statistiques du système:")
    print(f"   📦 Commandes: {stats['commandes']} (dont {stats['commandes_en_attente']} en attente)")
    print(f"   🚛 Véhicules: {stats['vehicules']}")
    print(f"   👤 Transporteurs: {stats['transporteurs']}")
    print(f"   📋 Planificateurs: {stats['planificateurs']}")
    
    print(f"\n🌐 Accès au système:")
    print(f"   URL: http://127.0.0.1:8000/")
    print(f"   Planificateur: http://127.0.0.1:8000/planificateur/dashboard/")
    print(f"   Login: planificateur1 / planif123")

if __name__ == "__main__":
    setup_basic_data()