# setup_google_maps.py

import os
import subprocess
import sys

def install_requirements():
    """Installer les dépendances Google Maps"""
    print("Installation des dépendances Google Maps...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements_maps.txt"])
        print("✅ Dépendances installées avec succès")
    except subprocess.CalledProcessError:
        print("❌ Erreur lors de l'installation des dépendances")
        return False
    return True

def setup_api_key():
    """Configuration de la clé API"""
    print("\n🔑 Configuration de la clé API Google Maps")
    print("Pour obtenir votre clé API:")
    print("1. Allez sur https://console.cloud.google.com/")
    print("2. Créez un projet ou sélectionnez un projet existant")
    print("3. Activez les APIs suivantes:")
    print("   - Maps JavaScript API")
    print("   - Geocoding API") 
    print("   - Directions API")
    print("   - Distance Matrix API")
    print("4. Créez une clé API dans 'APIs & Services' > 'Credentials'")
    
    api_key = input("\nEntrez votre clé API Google Maps: ").strip()
    
    if api_key:
        # Mettre à jour le fichier .env
        env_file = ".env"
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                content = f.read()
            
            if "GOOGLE_MAPS_API_KEY=" in content:
                content = content.replace("GOOGLE_MAPS_API_KEY=YOUR_GOOGLE_MAPS_API_KEY_HERE", f"GOOGLE_MAPS_API_KEY={api_key}")
            else:
                content += f"\nGOOGLE_MAPS_API_KEY={api_key}"
            
            with open(env_file, 'w') as f:
                f.write(content)
            
            print("✅ Clé API configurée dans .env")
        else:
            print("❌ Fichier .env non trouvé")
    else:
        print("⚠️ Clé API non fournie - vous devrez la configurer manuellement dans .env")

def main():
    print("🚀 Configuration Google Maps pour le système de transport")
    print("=" * 60)
    
    # Installation des dépendances
    if not install_requirements():
        return
    
    # Configuration de la clé API
    setup_api_key()
    
    print("\n✅ Configuration terminée!")
    print("\nPour tester:")
    print("1. Démarrez le serveur Django: python manage.py runserver")
    print("2. Allez sur http://localhost:8000/maps/")
    print("3. Testez l'optimisation de tournées")

if __name__ == "__main__":
    main()