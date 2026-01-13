#!/usr/bin/env python3
"""
Script pour tester la clé API OpenWeather
"""
import requests
import sys

API_KEY = "445013d6287827345374205ef0b268ce"
URL = f"https://api.openweathermap.org/data/2.5/weather?q=Casablanca&appid={API_KEY}&units=metric"

print("🧪 Test de la clé API OpenWeather...")
print(f"Clé: {API_KEY}\n")

try:
    response = requests.get(URL, timeout=5)
    
    if response.status_code == 200:
        data = response.json()
        print("✅ CLÉ API ACTIVE !")
        print(f"\n📍 Ville: {data['name']}")
        print(f"🌡️  Température: {data['main']['temp']}°C")
        print(f"☁️  Météo: {data['weather'][0]['description']}")
        print(f"💨 Vent: {data['wind']['speed']} m/s")
        sys.exit(0)
    elif response.status_code == 401:
        print("⏳ CLÉ PAS ENCORE ACTIVE")
        print("Attendez 10-15 minutes et réessayez")
        print("\nPour tester à nouveau:")
        print("  python3 test_api.py")
        sys.exit(1)
    else:
        print(f"❌ Erreur: {response.status_code}")
        print(response.text)
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Erreur de connexion: {e}")
    sys.exit(1)
