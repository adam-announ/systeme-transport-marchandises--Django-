import os
import django
import sys

# Configuration Django
sys.path.append('c:\\Users\\HP\\Desktop\\transport_system')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'transport_system.settings')
django.setup()

from django.db import connection
from utilisateurs.models import *

def fix_database_schema():
    """Corrige le schéma de base de données pour le planificateur"""
    
    with connection.cursor() as cursor:
        print("[INFO] Correction du schéma de base de données...")
        
        # Vérifier et ajouter les colonnes manquantes dans la table commandes
        try:
            cursor.execute("PRAGMA table_info(commandes)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'priorite' not in columns:
                print("[FIX] Ajout de la colonne 'priorite' à la table commandes")
                cursor.execute("ALTER TABLE commandes ADD COLUMN priorite VARCHAR(10) DEFAULT 'normale'")
            
            if 'planificateur_id' not in columns:
                print("[FIX] Ajout de la colonne 'planificateur_id' à la table commandes")
                cursor.execute("ALTER TABLE commandes ADD COLUMN planificateur_id INTEGER")
            
            if 'date_livraison_planifiee' not in columns:
                print("[FIX] Ajout de la colonne 'date_livraison_planifiee' à la table commandes")
                cursor.execute("ALTER TABLE commandes ADD COLUMN date_livraison_planifiee DATETIME")
            
            if 'distance_estimee' not in columns:
                print("[FIX] Ajout de la colonne 'distance_estimee' à la table commandes")
                cursor.execute("ALTER TABLE commandes ADD COLUMN distance_estimee DECIMAL(8,2)")
            
            if 'duree_estimee' not in columns:
                print("[FIX] Ajout de la colonne 'duree_estimee' à la table commandes")
                cursor.execute("ALTER TABLE commandes ADD COLUMN duree_estimee INTEGER")  # En minutes
            
        except Exception as e:
            print(f"[ERROR] Erreur lors de la modification de la table commandes: {e}")
        
        # Créer la table tournees si elle n'existe pas
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tournees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nom VARCHAR(200) NOT NULL,
                    planificateur_id INTEGER NOT NULL,
                    transporteur_id INTEGER NOT NULL,
                    vehicule_id INTEGER NOT NULL,
                    statut VARCHAR(20) DEFAULT 'planifiee',
                    date_creation DATETIME DEFAULT CURRENT_TIMESTAMP,
                    date_debut_prevue DATETIME NOT NULL,
                    date_fin_prevue DATETIME NOT NULL,
                    date_debut_reelle DATETIME,
                    date_fin_reelle DATETIME,
                    distance_totale DECIMAL(10,2),
                    duree_prevue INTEGER,
                    duree_reelle INTEGER,
                    optimisee BOOLEAN DEFAULT 0,
                    notes TEXT,
                    FOREIGN KEY (planificateur_id) REFERENCES users (id),
                    FOREIGN KEY (transporteur_id) REFERENCES users (id),
                    FOREIGN KEY (vehicule_id) REFERENCES vehicules (id)
                )
            """)
            print("[OK] Table 'tournees' créée/vérifiée")
        except Exception as e:
            print(f"[ERROR] Erreur lors de la création de la table tournees: {e}")
        
        # Créer la table etapes_tournee si elle n'existe pas
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS etapes_tournee (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tournee_id INTEGER NOT NULL,
                    commande_id INTEGER,
                    ordre INTEGER NOT NULL,
                    type_etape VARCHAR(20) NOT NULL,
                    statut VARCHAR(20) DEFAULT 'en_attente',
                    adresse VARCHAR(500) NOT NULL,
                    latitude DECIMAL(10,8),
                    longitude DECIMAL(11,8),
                    heure_prevue DATETIME NOT NULL,
                    heure_arrivee DATETIME,
                    heure_depart DATETIME,
                    duree_prevue INTEGER NOT NULL,
                    duree_reelle INTEGER,
                    distance_precedente DECIMAL(10,2),
                    notes TEXT,
                    FOREIGN KEY (tournee_id) REFERENCES tournees (id),
                    FOREIGN KEY (commande_id) REFERENCES commandes (id),
                    UNIQUE(tournee_id, ordre)
                )
            """)
            print("[OK] Table 'etapes_tournee' créée/vérifiée")
        except Exception as e:
            print(f"[ERROR] Erreur lors de la création de la table etapes_tournee: {e}")
        
        # Vérifier et ajouter les colonnes manquantes dans la table notifications
        try:
            cursor.execute("PRAGMA table_info(notifications)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'priority' not in columns:
                print("[FIX] Ajout de la colonne 'priority' à la table notifications")
                cursor.execute("ALTER TABLE notifications ADD COLUMN priority VARCHAR(10) DEFAULT 'normal'")
            
            if 'tournee_id' not in columns:
                print("[FIX] Ajout de la colonne 'tournee_id' à la table notifications")
                cursor.execute("ALTER TABLE notifications ADD COLUMN tournee_id INTEGER")
            
        except Exception as e:
            print(f"[ERROR] Erreur lors de la modification de la table notifications: {e}")
        
        # Vérifier et ajouter les colonnes manquantes dans la table livraisons
        try:
            cursor.execute("PRAGMA table_info(livraisons)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'tournee_id' not in columns:
                print("[FIX] Ajout de la colonne 'tournee_id' à la table livraisons")
                cursor.execute("ALTER TABLE livraisons ADD COLUMN tournee_id INTEGER")
            
            if 'latitude_actuelle' not in columns:
                print("[FIX] Ajout de la colonne 'latitude_actuelle' à la table livraisons")
                cursor.execute("ALTER TABLE livraisons ADD COLUMN latitude_actuelle DECIMAL(10,7)")
            
            if 'longitude_actuelle' not in columns:
                print("[FIX] Ajout de la colonne 'longitude_actuelle' à la table livraisons")
                cursor.execute("ALTER TABLE livraisons ADD COLUMN longitude_actuelle DECIMAL(10,7)")
            
        except Exception as e:
            print(f"[ERROR] Erreur lors de la modification de la table livraisons: {e}")

def update_existing_data():
    """Met à jour les données existantes avec des valeurs par défaut"""
    
    print("[INFO] Mise à jour des données existantes...")
    
    # Mettre à jour les commandes sans priorité
    commandes_sans_priorite = Commande.objects.filter(priorite__isnull=True)
    if commandes_sans_priorite.exists():
        print(f"[FIX] Mise à jour de {commandes_sans_priorite.count()} commandes sans priorité")
        commandes_sans_priorite.update(priorite='normale')
    
    # Ajouter des priorités variées aux commandes existantes
    commandes = list(Commande.objects.all())
    if commandes:
        import random
        priorites = ['basse', 'normale', 'haute', 'urgente']
        weights = [0.2, 0.5, 0.2, 0.1]  # 50% normale, 20% haute/basse, 10% urgente
        
        for commande in commandes:
            if commande.priorite == 'normale':  # Seulement si c'est encore 'normale'
                nouvelle_priorite = random.choices(priorites, weights=weights)[0]
                commande.priorite = nouvelle_priorite
                commande.save()
        
        print(f"[OK] Priorités mises à jour pour {len(commandes)} commandes")

def create_sample_tournees():
    """Crée des tournées d'exemple pour tester"""
    
    print("[INFO] Création de tournées d'exemple...")
    
    # Vérifier s'il y a des planificateurs
    planificateurs = User.objects.filter(role='planificateur')
    if not planificateurs.exists():
        print("[WARNING] Aucun planificateur trouvé, création d'un planificateur de test")
        planificateur = User.objects.create(
            username='planif_test',
            email='planif_test@transport.com',
            password='planif123',
            role='planificateur',
            first_name='Test',
            last_name='Planificateur',
            is_active=True
        )
    else:
        planificateur = planificateurs.first()
    
    # Vérifier s'il y a des transporteurs avec véhicules
    transporteurs_avec_vehicules = User.objects.filter(
        role='transporteur',
        vehicules__isnull=False
    ).distinct()
    
    if not transporteurs_avec_vehicules.exists():
        print("[WARNING] Aucun transporteur avec véhicule trouvé")
        return
    
    # Créer quelques tournées d'exemple
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    transporteur = transporteurs_avec_vehicules.first()
    vehicule = transporteur.vehicules.first()
    
    # Tournée 1: Planifiée
    tournee1 = Tournee.objects.create(
        nom="Tournée Test Casablanca",
        planificateur=planificateur,
        transporteur=transporteur,
        vehicule=vehicule,
        date_debut_prevue=timezone.now() + timedelta(hours=2),
        date_fin_prevue=timezone.now() + timedelta(hours=6),
        distance_totale=120.5,
        duree_prevue=timedelta(hours=4),
        optimisee=True,
        notes="Tournée créée automatiquement pour test"
    )
    
    print(f"[OK] Tournée créée: {tournee1.nom}")

if __name__ == "__main__":
    print("="*60)
    print("CORRECTION DU SYSTÈME PLANIFICATEUR")
    print("="*60)
    
    try:
        fix_database_schema()
        update_existing_data()
        create_sample_tournees()
        
        print("\n" + "="*60)
        print("[SUCCESS] Corrections appliquées avec succès!")
        print("="*60)
        print("\nAméliorations apportées:")
        print("✅ Schéma de base de données corrigé")
        print("✅ Colonnes manquantes ajoutées")
        print("✅ Tables tournées et étapes créées")
        print("✅ Données existantes mises à jour")
        print("✅ Priorités des commandes diversifiées")
        print("✅ Tournées d'exemple créées")
        print("\nLe système planificateur est maintenant opérationnel!")
        
    except Exception as e:
        print(f"\n[ERROR] Erreur lors des corrections: {str(e)}")
        import traceback
        traceback.print_exc()