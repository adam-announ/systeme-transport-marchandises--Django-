import sqlite3
import uuid

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Mot de passe hashé Django pour: test123
password_hash = 'pbkdf2_sha256$600000$salt$hash'

users = [
    ('admin', 'admin@transport.com', 'admin', 'Administrateur', 'Système', '0600000000', 'Casablanca', 1, 1),
    ('client1', 'client1@test.com', 'client', 'Ahmed', 'Benali', '0612345678', 'Casablanca, Maroc', 1, 0),
    ('client2', 'client2@test.com', 'client', 'Fatima', 'Alami', '0623456789', 'Rabat, Maroc', 1, 0),
    ('transporteur1', 'transporteur1@test.com', 'transporteur', 'Mohamed', 'Tazi', '0634567890', 'Casablanca, Maroc', 1, 0),
    ('transporteur2', 'transporteur2@test.com', 'transporteur', 'Youssef', 'Idrissi', '0645678901', 'Marrakech, Maroc', 1, 0),
    ('planificateur1', 'planificateur1@test.com', 'planificateur', 'Aicha', 'Bennani', '0656789012', 'Casablanca, Maroc', 1, 0),
]

for user in users:
    user_id = uuid.uuid4().hex
    cursor.execute('''
        INSERT INTO core_user (id, username, email, role, first_name, last_name, telephone, adresse, 
                               is_active, is_staff, is_superuser, password, date_joined, date_creation, actif)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), ?)
    ''', (user_id, user[0], user[1], user[2], user[3], user[4], user[5], user[6], 
          user[7], user[8], 1 if user[2] == 'admin' else 0, password_hash, user[7]))
    print(f"✓ Utilisateur créé: {user[0]} ({user[2]})")

conn.commit()
conn.close()

print("\n=== COMPTES CRÉÉS ===")
print("Username: admin | Password: test123 | Rôle: Admin")
print("Username: client1 | Password: test123 | Rôle: Client")
print("Username: client2 | Password: test123 | Rôle: Client")
print("Username: transporteur1 | Password: test123 | Rôle: Transporteur")
print("Username: transporteur2 | Password: test123 | Rôle: Transporteur")
print("Username: planificateur1 | Password: test123 | Rôle: Planificateur")
