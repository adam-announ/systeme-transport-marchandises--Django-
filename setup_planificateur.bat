@echo off
echo ============================================================
echo CONFIGURATION ET AMELIORATION DU SYSTEME PLANIFICATEUR
echo ============================================================
echo.

echo [1/4] Correction du schema de base de donnees...
python fix_planificateur.py
echo.

echo [2/4] Generation de donnees realistes...
python generate_planificateur_data.py
echo.

echo [3/4] Creation des utilisateurs de test...
python create_users.py
echo.

echo [4/4] Demarrage du serveur de developpement...
echo.
echo ============================================================
echo SYSTEME PLANIFICATEUR PRET !
echo ============================================================
echo.
echo Acces au systeme:
echo - URL: http://127.0.0.1:8000/
echo - Planificateur: planificateur1 / planif123
echo - Admin: admin / admin123
echo.
echo Fonctionnalites ameliorees:
echo + Planification automatique avec donnees reelles
echo + Suggestions de regroupements intelligentes
echo + Optimisation des tournees
echo + Statistiques en temps reel
echo + Notifications avancees
echo + Interface utilisateur moderne
echo.

python manage.py runserver