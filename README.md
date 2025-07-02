# Système de Transport de Marchandises

Un système complet de gestion de transport de marchandises développé avec Django, offrant une solution complète pour la gestion des commandes, l'optimisation des itinéraires, et le suivi en temps réel.

## 🚀 Fonctionnalités

### 👤 Gestion des Rôles
- **Client** : Créer et suivre des commandes
- **Transporteur** : Gérer les missions et véhicules
- **Planificateur** : Optimiser les itinéraires et affecter les transporteurs
- **Administrateur** : Gestion complète du système

### 📦 Gestion des Commandes
- Création de commandes avec géolocalisation
- Suivi en temps réel des livraisons
- Génération automatique de bons de livraison
- Historique complet des transports

### 🗺️ Optimisation d'Itinéraires
- Intégration avec Google Maps API
- Calcul automatique des distances et temps
- Prise en compte des conditions météorologiques
- Optimisation des tournées multiples

### 📊 Tableau de Bord
- Statistiques en temps réel
- Rapports détaillés
- Notifications système
- Journal d'activité

## 🛠️ Technologies Utilisées

- **Backend** : Django 5.2, Django REST Framework
- **Frontend** : Bootstrap 5, JavaScript ES6
- **Base de données** : SQLite (développement)
- **APIs externes** : 
  - Google Maps API (géolocalisation et itinéraires)
  - OpenWeather API (conditions météorologiques)
  - OpenRoute Service (alternative gratuite)

## 📋 Prérequis

- Python 3.11+
- pip (gestionnaire de paquets Python)
- Clés API (optionnelles pour les fonctionnalités avancées)

## 🚀 Installation

1. **Cloner le projet**
```bash
git clone <url-du-projet>
cd transport_system
```

2. **Créer un environnement virtuel**
```bash
python -m venv env
env\Scripts\activate  # Windows
# ou
source env/bin/activate  # Linux/Mac
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Configurer les variables d'environnement**
Modifier le fichier `.env` avec vos clés API :
```env
GOOGLE_MAPS_API_KEY=votre_cle_google_maps
OPENWEATHER_API_KEY=votre_cle_openweather
OPENROUTE_API_KEY=votre_cle_openroute
```

5. **Appliquer les migrations**
```bash
python manage.py migrate
```

6. **Créer les données d'exemple**
```bash
python create_sample_data.py
```

7. **Démarrer le serveur**
```bash
python manage.py runserver
```

## 👥 Comptes de Test

Après avoir exécuté le script de données d'exemple :

| Rôle | Utilisateur | Mot de passe |
|------|-------------|--------------|
| Admin | admin | admin123 |
| Client | client1 | test123 |
| Client | client2 | test123 |
| Transporteur | transporteur1 | test123 |
| Transporteur | transporteur2 | test123 |
| Planificateur | planificateur1 | test123 |

## 🌐 URLs Principales

- **Connexion** : http://localhost:8000/auth/login/
- **Client** : http://localhost:8000/client/dashboard/
- **Transporteur** : http://localhost:8000/transporteur/dashboard/
- **Planificateur** : http://localhost:8000/planificateur/dashboard/
- **Admin** : http://localhost:8000/admin-panel/dashboard/
- **Admin Django** : http://localhost:8000/admin/

## 📱 APIs REST

### Authentification
- `POST /auth/api/login/` - Connexion API

### Client
- `GET /client/api/commandes/` - Liste des commandes
- `GET /client/api/suivi/{id}/` - Suivi d'une commande

### Planificateur
- `POST /planificateur/api/optimiser/` - Optimiser un itinéraire
- `GET /planificateur/api/transporteurs/` - Transporteurs disponibles

### Transporteur
- `GET /transporteur/api/missions/` - Missions du transporteur
- `POST /transporteur/api/position/` - Mettre à jour la position
- `POST /transporteur/api/livraison/` - Confirmer une livraison

### Admin
- `GET /admin-panel/api/statistiques/` - Statistiques système

## 🏗️ Architecture

```
transport_system/
├── core/                    # Modèles de base
├── authentication/          # Gestion des utilisateurs
├── client/                  # Interface client
├── transporteur/           # Interface transporteur
├── planificateur/          # Interface planificateur
├── admin_panel/            # Interface administrateur
├── templates/              # Templates HTML
├── static/                 # Fichiers statiques (CSS, JS)
└── transport_system/       # Configuration Django
```

## 🔧 Configuration des APIs

### Google Maps API
1. Créer un projet sur Google Cloud Console
2. Activer les APIs : Maps JavaScript API, Directions API, Geocoding API
3. Créer une clé API et l'ajouter dans `.env`

### OpenWeather API
1. S'inscrire sur openweathermap.org
2. Obtenir une clé API gratuite
3. L'ajouter dans `.env`

### OpenRoute Service
1. S'inscrire sur openrouteservice.org
2. Obtenir une clé API gratuite
3. L'ajouter dans `.env`

## 🚀 Déploiement

### Production avec PostgreSQL
1. Installer PostgreSQL
2. Modifier `settings.py` pour utiliser PostgreSQL
3. Configurer les variables d'environnement de production
4. Utiliser un serveur web (Nginx + Gunicorn)

### Docker (optionnel)
```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

## 🧪 Tests

```bash
python manage.py test
```

## 📝 Fonctionnalités Avancées

- **Géofencing** : Alertes automatiques lors d'arrivée/départ
- **Tracking temps réel** : Suivi GPS des véhicules
- **Optimisation multi-critères** : Distance, temps, coût, météo
- **Notifications push** : Alertes en temps réel
- **Rapports avancés** : Analytics et KPIs
- **API mobile** : Support pour applications mobiles

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/nouvelle-fonctionnalite`)
3. Commit les changements (`git commit -am 'Ajout nouvelle fonctionnalité'`)
4. Push vers la branche (`git push origin feature/nouvelle-fonctionnalite`)
5. Créer une Pull Request

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 📞 Support

Pour toute question ou support :
- Email : support@transport-system.com
- Documentation : [Wiki du projet]
- Issues : [GitHub Issues]

---

**Développé avec ❤️ pour optimiser la logistique de transport**