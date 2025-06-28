@echo off
echo Installation des améliorations du système de transport...
echo.

echo [1/4] Activation de l'environnement virtuel...
call env\Scripts\activate.bat

echo [2/4] Installation des nouvelles dépendances...
pip install djangorestframework==3.14.0
pip install django-cors-headers==4.3.1
pip install django-filter==23.3
pip install markdown==3.5.1

echo [3/4] Migration de la base de données...
python manage.py makemigrations
python manage.py migrate

echo [4/4] Création des données de test améliorées...
python create_users.py

echo.
echo ✅ Installation terminée avec succès!
echo.
echo 🚀 Démarrage du serveur...
python manage.py runserver

pause