# Installation Neo4j et MongoDB

## 📦 Installation des packages Python

```bash
pip install -r requirements.txt
```

## 🔧 Installation Neo4j

### Linux (Ubuntu/Debian)
```bash
# Ajouter le repository Neo4j
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo apt-key add -
echo 'deb https://debian.neo4j.com stable latest' | sudo tee /etc/apt/sources.list.d/neo4j.list

# Installer Neo4j
sudo apt-get update
sudo apt-get install neo4j

# Démarrer Neo4j
sudo systemctl start neo4j
sudo systemctl enable neo4j
```

### Docker (Recommandé)
```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

### Accès Neo4j Browser
- URL: http://localhost:7474
- Username: neo4j
- Password: password (à changer)

## 🍃 Installation MongoDB

### Linux (Ubuntu/Debian)
```bash
# Importer la clé GPG
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -

# Ajouter le repository
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

# Installer MongoDB
sudo apt-get update
sudo apt-get install -y mongodb-org

# Démarrer MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod
```

### Docker (Recommandé)
```bash
docker run -d \
  --name mongodb \
  -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=password \
  mongo:latest
```

## 🔧 Configuration du projet

1. **Copier le fichier .env**
```bash
cp .env.example .env
```

2. **Modifier les variables dans .env**
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=votre_password

MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB_NAME=transport_mongo
```

3. **Tester les connexions**
```bash
python manage.py shell
```

```python
# Test Neo4j
from core.neo4j_connection import neo4j_conn
result = neo4j_conn.query("RETURN 'Neo4j connecté!' as message")
print(result)

# Test MongoDB
from core.mongo_connection import connect_mongodb
from core.mongo_models import ActivityLog
connect_mongodb()
log = ActivityLog(user_id=1, user_role='test', action='test')
log.save()
print("MongoDB connecté!")
```

## 📊 Cas d'usage

### Neo4j - Pour :
- Graphes d'itinéraires complexes
- Relations entre lieux
- Optimisation de chemins
- Analyse de réseaux de transport

### MongoDB - Pour :
- Logs de tracking GPS en temps réel
- Historique de positions
- Analytics et métriques
- Données non structurées

### SQLite/PostgreSQL - Pour :
- Données relationnelles (users, commandes)
- Transactions ACID
- Données structurées

## 🎯 Architecture Multi-DB

```
Django App
├── SQLite/PostgreSQL (Données principales)
│   ├── Users
│   ├── Commandes
│   └── Véhicules
│
├── MongoDB (Données temps réel)
│   ├── Tracking GPS
│   ├── Activity Logs
│   └── Analytics
│
└── Neo4j (Graphes)
    ├── Routes
    ├── Optimisation
    └── Relations géographiques
```

## ✅ Vérification

```bash
# Vérifier Neo4j
curl http://localhost:7474

# Vérifier MongoDB
mongosh --eval "db.version()"

# Démarrer Django
python manage.py runserver
```
