# transport/validators.py - Validateurs métier

from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
import re

from .models import Transporteur, Commande, ParametreSysteme


class OrderValidator:
    """Validateur pour les commandes"""
    
    @staticmethod
    def validate_order_creation(client, form_data):
        """Valider la création d'une commande"""
        errors = []
        
        # Vérifier les limites du client
        if not OrderValidator.check_client_limits(client):
            errors.append("Vous avez atteint votre limite de commandes en attente.")
        
        # Vérifier le poids
        poids = form_data.get('poids', 0)
        if poids <= 0:
            errors.append("Le poids doit être supérieur à zéro.")
        elif poids > 10000:  # 10 tonnes max
            errors.append("Le poids ne peut pas dépasser 10 tonnes.")
        
        # Vérifier les adresses
        if not OrderValidator.validate_addresses(form_data):
            errors.append("Les adresses d'enlèvement et de livraison ne peuvent pas être identiques.")
        
        # Vérifier les créneaux horaires
        if not OrderValidator.validate_business_hours():
            errors.append("Les commandes ne peuvent être créées qu'en heures ouvrables.")
        
        return errors
    
    @staticmethod
    def check_client_limits(client):
        """Vérifier les limites d'un client"""
        # Limite de commandes en attente
        commandes_attente = Commande.objects.filter(
            client=client,
            statut__in=['EN_ATTENTE', 'AFFECTEE']
        ).count()
        
        limite_max = get_system_parameter('limite_commandes_attente', 10)
        return commandes_attente < limite_max
    
    @staticmethod
    def validate_addresses(form_data):
        """Valider que les adresses sont différentes"""
        addr_enlev = {
            'rue': form_data.get('enlevement-rue', '').strip(),
            'ville': form_data.get('enlevement-ville', '').strip(),
            'code_postal': form_data.get('enlevement-code_postal', '').strip()
        }
        
        addr_livr = {
            'rue': form_data.get('livraison-rue', '').strip(),
            'ville': form_data.get('livraison-ville', '').strip(),
            'code_postal': form_data.get('livraison-code_postal', '').strip()
        }
        
        # Les adresses ne doivent pas être identiques
        return not (addr_enlev == addr_livr and all(addr_enlev.values()))
    
    @staticmethod
    def validate_business_hours():
        """Vérifier si on est en heures ouvrables"""
        now = timezone.now()
        
        # Vérifier le jour de la semaine (0=lundi, 6=dimanche)
        if now.weekday() >= 5:  # Samedi ou dimanche
            return False
        
        # Vérifier l'heure (8h-18h)
        if now.hour < 8 or now.hour >= 18:
            return False
        
        return True
    
    @staticmethod
    def can_cancel_order(commande, user):
        """Vérifier si une commande peut être annulée"""
        # Vérifier les permissions
        if not (user.is_staff or (hasattr(user, 'client') and commande.client == user.client)):
            return False, "Vous n'avez pas l'autorisation d'annuler cette commande."
        
        # Vérifier le statut
        if commande.statut in ['EN_TRANSIT', 'LIVREE']:
            return False, "Cette commande ne peut plus être annulée."
        
        # Vérifier le délai
        delai_h = get_system_parameter('delai_annulation', 24)
        limite_annulation = commande.date_creation + timedelta(hours=delai_h)
        
        if timezone.now() > limite_annulation:
            return False, f"Délai d'annulation dépassé ({delai_h}h)."
        
        return True, "Annulation autorisée."


class TransporterValidator:
    """Validateur pour les transporteurs"""
    
    @staticmethod
    def validate_transporter_profile(form_data):
        """Valider un profil transporteur"""
        errors = []
        
        # Valider le matricule
        matricule = form_data.get('matricule', '').strip()
        if not TransporterValidator.validate_matricule(matricule):
            errors.append("Format de matricule invalide. Utilisez le format: ABC-123-DE")
        
        # Vérifier l'unicité du matricule
        if Transporteur.objects.filter(matricule=matricule).exists():
            errors.append("Ce matricule est déjà utilisé.")
        
        # Valider la capacité
        try:
            capacite = float(form_data.get('capacite_charge', 0))
            if capacite <= 0:
                errors.append("La capacité de charge doit être supérieure à zéro.")
            elif capacite > 50000:  # 50 tonnes max
                errors.append("La capacité de charge ne peut pas dépasser 50 tonnes.")
        except (ValueError, TypeError):
            errors.append("La capacité de charge doit être un nombre valide.")
        
        return errors
    
    @staticmethod
    def validate_matricule(matricule):
        """Valider le format du matricule"""
        # Format attendu: ABC-123-DE (3 lettres, 3 chiffres, 2 lettres)
        pattern = r'^[A-Z]{1,3}-[0-9]{1,4}-[A-Z]{1,3}$'
        return bool(re.match(pattern, matricule.upper()))
    
    @staticmethod
    def can_assign_mission(transporteur, commande):
        """Vérifier si un transporteur peut être assigné à une mission"""
        if not transporteur.disponible:
            return False, "Le transporteur n'est pas disponible."
        
        if not transporteur.actif:
            return False, "Le compte transporteur est désactivé."
        
        # Vérifier la capacité
        if transporteur.capacite_charge < commande.poids:
            return False, f"Capacité insuffisante ({transporteur.capacite_charge}kg < {commande.poids}kg)."
        
        # Vérifier les missions en cours
        missions_actives = transporteur.missiontransporteur_set.filter(
            statut__in=['ASSIGNEE', 'EN_COURS']
        ).count()
        
        limite_missions = get_system_parameter('limite_missions_transporteur', 3)
        if missions_actives >= limite_missions:
            return False, f"Le transporteur a déjà {missions_actives} missions en cours."
        
        return True, "Assignation autorisée."


class SecurityValidator:
    """Validateur pour la sécurité"""
    
    @staticmethod
    def validate_file_upload(file):
        """Valider un fichier uploadé"""
        errors = []
        
        # Vérifier la taille
        max_size = get_system_parameter('max_file_size', 5) * 1024 * 1024  # 5MB par défaut
        if file.size > max_size:
            errors.append(f"Le fichier est trop volumineux (max: {max_size//1024//1024}MB).")
        
        # Vérifier l'extension
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.pdf', '.doc', '.docx']
        file_extension = file.name.lower().split('.')[-1] if '.' in file.name else ''
        
        if f'.{file_extension}' not in allowed_extensions:
            errors.append(f"Type de fichier non autorisé. Extensions autorisées: {', '.join(allowed_extensions)}")
        
        return errors
    
    @staticmethod
    def validate_user_input(data, field_type):
        """Valider les entrées utilisateur selon le type"""
        if field_type == 'phone':
            return SecurityValidator.validate_phone(data)
        elif field_type == 'email':
            return SecurityValidator.validate_email(data)
        elif field_type == 'text':
            return SecurityValidator.validate_text(data)
        
        return True, "Valide"
    
    @staticmethod
    def validate_phone(phone):
        """Valider un numéro de téléphone"""
        # Format marocain: +212 6XX-XX-XX-XX ou 06XX-XX-XX-XX
        pattern = r'^(\+212|0)[5-7][0-9]{8}$'
        clean_phone = re.sub(r'[-\s]', '', phone)
        
        if re.match(pattern, clean_phone):
            return True, "Numéro valide"
        else:
            return False, "Format de numéro de téléphone invalide"
    
    @staticmethod
    def validate_email(email):
        """Valider un email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, email):
            return True, "Email valide"
        else:
            return False, "Format d'email invalide"
    
    @staticmethod
    def validate_text(text):
        """Valider un texte (pas de contenu malveillant)"""
        # Détecter les tentatives d'injection
        dangerous_patterns = [
            r'<script',
            r'javascript:',
            r'onclick',
            r'onerror',
            r'<iframe',
            r'sql\s*(select|insert|update|delete|drop)',
        ]
        
        text_lower = text.lower()
        for pattern in dangerous_patterns:
            if re.search(pattern, text_lower):
                return False, "Contenu potentiellement dangereux détecté"
        
        return True, "Texte valide"


class BusinessRuleValidator:
    """Validateur pour les règles métier"""
    
    @staticmethod
    def validate_mission_status_change(mission, nouveau_statut, user):
        """Valider le changement de statut d'une mission"""
        # Matrice des transitions autorisées
        transitions_autorisees = {
            'ASSIGNEE': ['EN_COURS', 'ANNULEE'],
            'EN_COURS': ['TERMINEE', 'ANNULEE'],
            'TERMINEE': [],  # Statut final
            'ANNULEE': []   # Statut final
        }
        
        statut_actuel = mission.statut
        
        # Vérifier si la transition est autorisée
        if nouveau_statut not in transitions_autorisees.get(statut_actuel, []):
            return False, f"Transition de {statut_actuel} vers {nouveau_statut} non autorisée."
        
        # Vérifier les permissions
        if not user.is_staff:
            # Seul le transporteur assigné peut changer le statut
            if not (hasattr(user, 'transporteur') and mission.transporteur == user.transporteur):
                return False, "Vous n'êtes pas autorisé à modifier cette mission."
        
        # Règles spécifiques selon le nouveau statut
        if nouveau_statut == 'TERMINEE':
            # Vérifier que la mission a bien été démarrée
            if not mission.date_debut:
                return False, "La mission doit être démarrée avant d'être terminée."
        
        return True, "Changement de statut autorisé."
    
    @staticmethod
    def validate_incident_report(mission, incident_data, user):
        """Valider le signalement d'un incident"""
        # Vérifier les permissions
        if not (user.is_staff or 
               (hasattr(user, 'transporteur') and mission.transporteur == user.transporteur)):
            return False, "Vous n'êtes pas autorisé à signaler un incident sur cette mission."
        
        # Vérifier que la mission est en cours
        if mission.statut not in ['EN_COURS', 'ASSIGNEE']:
            return False, "Un incident ne peut être signalé que sur une mission en cours."
        
        # Vérifier les données de l'incident
        if not incident_data.get('type'):
            return False, "Le type d'incident est obligatoire."
        
        if not incident_data.get('description', '').strip():
            return False, "La description de l'incident est obligatoire."
        
        description = incident_data.get('description', '')
        if len(description) < 10:
            return False, "La description doit contenir au moins 10 caractères."
        
        return True, "Signalement d'incident valide."
    
    @staticmethod
    def validate_price_estimation(poids, distance, type_marchandise):
        """Valider les paramètres pour l'estimation de prix"""
        if poids <= 0:
            return False, "Le poids doit être supérieur à zéro."
        
        if distance <= 0:
            return False, "La distance doit être supérieure à zéro."
        
        types_autorises = ['standard', 'fragile', 'perissable', 'dangereux', 'urgent']
        if type_marchandise.lower() not in types_autorises:
            return False, f"Type de marchandise non reconnu. Types autorisés: {', '.join(types_autorises)}"
        
        return True, "Paramètres valides pour l'estimation."


class DataValidator:
    """Validateur pour l'intégrité des données"""
    
    @staticmethod
    def validate_address_data(address_data):
        """Valider les données d'adresse"""
        required_fields = ['rue', 'ville', 'code_postal', 'pays']
        errors = []
        
        for field in required_fields:
            value = address_data.get(field, '').strip()
            if not value:
                errors.append(f"Le champ {field} est obligatoire.")
            elif len(value) < 2:
                errors.append(f"Le champ {field} doit contenir au moins 2 caractères.")
        
        # Valider le code postal
        code_postal = address_data.get('code_postal', '').strip()
        if code_postal and not re.match(r'^\d{5}, code_postal):
            errors.append("Le code postal doit contenir exactement 5 chiffres.")
        
        # Valider la ville (pas de chiffres)
        ville = address_data.get('ville', '').strip()
        if ville and re.search(r'\d', ville):
            errors.append("Le nom de la ville ne doit pas contenir de chiffres.")
        
        return errors
    
    @staticmethod
    def validate_coordinate_data(latitude, longitude):
        """Valider les coordonnées GPS"""
        try:
            lat = float(latitude)
            lng = float(longitude)
            
            # Vérifier les plages valides
            if not (-90 <= lat <= 90):
                return False, "La latitude doit être entre -90 et 90."
            
            if not (-180 <= lng <= 180):
                return False, "La longitude doit être entre -180 et 180."
            
            # Vérifier que c'est dans la zone du Maroc (approximatif)
            if not (27 <= lat <= 36 and -17 <= lng <= 2):
                return False, "Les coordonnées ne semblent pas être au Maroc."
            
            return True, "Coordonnées valides."
            
        except (ValueError, TypeError):
            return False, "Les coordonnées doivent être des nombres valides."
    
    @staticmethod
    def validate_date_range(date_debut, date_fin):
        """Valider une plage de dates"""
        if not date_debut or not date_fin:
            return False, "Les dates de début et de fin sont obligatoires."
        
        if date_debut > date_fin:
            return False, "La date de début ne peut pas être postérieure à la date de fin."
        
        # Vérifier que la plage n'est pas trop large
        delta = date_fin - date_debut
        if delta.days > 365:
            return False, "La plage de dates ne peut pas dépasser 365 jours."
        
        # Vérifier que les dates ne sont pas dans le futur
        today = timezone.now().date()
        if date_fin > today:
            return False, "La date de fin ne peut pas être dans le futur."
        
        return True, "Plage de dates valide."


# Fonctions utilitaires
def get_system_parameter(nom, default_value):
    """Récupérer un paramètre système avec valeur par défaut"""
    try:
        param = ParametreSysteme.objects.get(nom=nom)
        if param.type == 'INTEGER':
            return int(param.valeur)
        elif param.type == 'FLOAT':
            return float(param.valeur)
        elif param.type == 'BOOLEAN':
            return param.valeur.lower() in ['true', '1', 'yes', 'oui']
        else:
            return param.valeur
    except (ParametreSysteme.DoesNotExist, ValueError, AttributeError):
        return default_value


class ValidationMixin:
    """Mixin pour ajouter la validation aux vues"""
    
    def validate_request_data(self, request, validation_rules):
        """Valider les données de la requête selon les règles fournies"""
        errors = []
        
        for field, rules in validation_rules.items():
            value = request.POST.get(field) or request.GET.get(field)
            
            # Vérifier si le champ est requis
            if rules.get('required', False) and not value:
                errors.append(f"Le champ {field} est obligatoire.")
                continue
            
            if value:  # Si la valeur existe, appliquer les validations
                # Validation de type
                field_type = rules.get('type')
                if field_type:
                    is_valid, message = SecurityValidator.validate_user_input(value, field_type)
                    if not is_valid:
                        errors.append(f"{field}: {message}")
                
                # Validation de longueur
                min_length = rules.get('min_length')
                max_length = rules.get('max_length')
                
                if min_length and len(value) < min_length:
                    errors.append(f"{field}: minimum {min_length} caractères requis.")
                
                if max_length and len(value) > max_length:
                    errors.append(f"{field}: maximum {max_length} caractères autorisés.")
                
                # Validation personnalisée
                custom_validator = rules.get('validator')
                if custom_validator and callable(custom_validator):
                    is_valid, message = custom_validator(value)
                    if not is_valid:
                        errors.append(f"{field}: {message}")
        
        return errors
    
    def add_validation_errors(self, request, errors):
        """Ajouter les erreurs de validation aux messages"""
        if errors:
            for error in errors:
                messages.error(request, error)
            return True
        return False