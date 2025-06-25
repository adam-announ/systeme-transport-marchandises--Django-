import os
import django
import sys

# Configuration Django
sys.path.append('c:\\Users\\HP\\Desktop\\transport_system')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'transport_system.settings')
django.setup()

from utilisateurs.models import User

# Supprimer tous les utilisateurs existants
User.objects.all().delete()
print("Tous les anciens comptes supprimes")

# Créer un nouveau compte admin
admin_user = User.objects.create(
    username='admin',
    email='admin@transport.com',
    password='admin123',
    role='admin',
    first_name='Admin',
    last_name='System',
    phone='+212600000001',
    is_active=True
)

print("\nNouveau compte admin cree avec succes!")
print("="*50)
print("COMPTE ADMINISTRATEUR")
print("="*50)
print(f"Username: {admin_user.username}")
print(f"Password: admin123")
print(f"Email: {admin_user.email}")
print(f"Nom: {admin_user.first_name} {admin_user.last_name}")
print("="*50)
print("Connexion: http://127.0.0.1:8000/login/")
print("="*50)