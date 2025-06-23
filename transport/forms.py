# transport/forms.py - Formulaires optimisés

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Commande, Adresse, Client, Transporteur, Incident

class InscriptionForm(UserCreationForm):
    """Formulaire d'inscription unifié"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Prénom'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom'})
    )
    telephone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+212 6XX-XX-XX-XX'})
    )
    adresse = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Adresse complète'})
    )
    type_compte = forms.ChoiceField(
        choices=[('client', 'Client'), ('transporteur', 'Transporteur')],
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='client'
    )
    
    # Champs spécifiques transporteur
    matricule = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: 123-ABC-45',
            'data-transporteur': 'true'
        })
    )
    type_vehicule = forms.ChoiceField(
        choices=Transporteur.TYPES_VEHICULES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'data-transporteur': 'true'
        })
    )
    capacite_charge = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Capacité en kg',
            'data-transporteur': 'true'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom d\'utilisateur'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Mot de passe'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirmer mot de passe'})
    
    def clean(self):
        cleaned_data = super().clean()
        type_compte = cleaned_data.get('type_compte')
        
        if type_compte == 'transporteur':
            required_fields = ['matricule', 'type_vehicule', 'capacite_charge']
            for field in required_fields:
                if not cleaned_data.get(field):
                    raise forms.ValidationError(f'Le champ {field} est obligatoire pour les transporteurs.')
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            
            if self.cleaned_data['type_compte'] == 'client':
                Client.objects.create(
                    user=user,
                    telephone=self.cleaned_data['telephone'],
                    adresse=self.cleaned_data['adresse']
                )
            else:  # transporteur
                Transporteur.objects.create(
                    user=user,
                    matricule=self.cleaned_data['matricule'],
                    type_vehicule=self.cleaned_data['type_vehicule'],
                    capacite_charge=self.cleaned_data['capacite_charge']
                )
        
        return user

class AdresseForm(forms.ModelForm):
    """Formulaire pour les adresses"""
    class Meta:
        model = Adresse
        fields = ['rue', 'ville', 'code_postal', 'pays']
        widgets = {
            'rue': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Numéro et nom de rue',
                'required': True
            }),
            'ville': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ville',
                'required': True,
                'list': 'villes-maroc'
            }),
            'code_postal': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Code postal (5 chiffres)',
                'pattern': '[0-9]{5}',
                'maxlength': '5'
            }),
            'pays': forms.TextInput(attrs={
                'class': 'form-control',
                'value': 'Maroc',
                'readonly': True
            }),
        }
    
    def clean_code_postal(self):
        code_postal = self.cleaned_data.get('code_postal')
        if code_postal and not code_postal.isdigit():
            raise forms.ValidationError('Le code postal doit contenir uniquement des chiffres.')
        if code_postal and len(code_postal) != 5:
            raise forms.ValidationError('Le code postal doit contenir exactement 5 chiffres.')
        return code_postal

class CommandeForm(forms.ModelForm):
    """Formulaire pour créer une commande"""
    class Meta:
        model = Commande
        fields = ['poids', 'type_marchandise', 'priorite', 'instructions_speciales']
        widgets = {
            'poids': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Poids en kg',
                'min': '0.1',
                'step': '0.1',
                'required': True
            }),
            'type_marchandise': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Électroménager, Documents, Mobilier...',
                'required': True,
                'list': 'types-marchandises'
            }),
            'priorite': forms.Select(attrs={
                'class': 'form-control'
            }),
            'instructions_speciales': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Instructions spéciales pour la livraison (optionnel)'
            }),
        }
    
    def clean_poids(self):
        poids = self.cleaned_data.get('poids')
        if poids and poids <= 0:
            raise forms.ValidationError('Le poids doit être supérieur à zéro.')
        if poids and poids > 50000:  # 50 tonnes max
            raise forms.ValidationError('Le poids ne peut pas dépasser 50 tonnes.')
        return poids

class IncidentForm(forms.ModelForm):
    """Formulaire pour signaler un incident"""
    class Meta:
        model = Incident
        fields = ['type', 'description', 'photo']
        widgets = {
            'type': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Décrivez l\'incident en détail...',
                'required': True,
                'minlength': '10'
            }),
            'photo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }
        labels = {
            'type': 'Type d\'incident',
            'description': 'Description détaillée',
            'photo': 'Photo (optionnel)'
        }
    
    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description and len(description) < 10:
            raise forms.ValidationError('La description doit contenir au moins 10 caractères.')
        return description

class StatutMissionForm(forms.Form):
    """Formulaire pour mettre à jour le statut d'une mission"""
    STATUT_CHOICES = [
        ('EN_COURS', 'Démarrer la mission'),
        ('TERMINEE', 'Mission terminée'),
        ('ANNULEE', 'Annuler la mission'),
    ]
    
    statut = forms.ChoiceField(
        choices=STATUT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Nouveau statut'
    )
    commentaire = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Commentaire (optionnel)'
        }),
        label='Commentaire',
        required=False
    )

class RapportForm(forms.Form):
    """Formulaire pour générer des rapports"""
    date_debut = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'required': True
        }),
        label='Date de début'
    )
    date_fin = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'required': True
        }),
        label='Date de fin'
    )
    format_export = forms.ChoiceField(
        choices=[
            ('csv', 'CSV (Excel)'),
            ('pdf', 'PDF'),
            ('html', 'Aperçu HTML')
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Format d\'export',
        initial='csv'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        
        if date_debut and date_fin:
            if date_debut > date_fin:
                raise forms.ValidationError('La date de début ne peut pas être postérieure à la date de fin.')
            
            # Limiter la plage à 1 an
            if (date_fin - date_debut).days > 365:
                raise forms.ValidationError('La plage de dates ne peut pas dépasser 365 jours.')
        
        return cleaned_data

class AffectationForm(forms.Form):
    """Formulaire pour affecter une commande à un transporteur"""
    transporteur = forms.ModelChoiceField(
        queryset=Transporteur.objects.none(),  # Sera défini dans __init__
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Sélectionner un transporteur',
        empty_label='Choisir un transporteur...'
    )
    priorite_mission = forms.ChoiceField(
        choices=[
            ('NORMALE', 'Normale'),
            ('HAUTE', 'Haute'),
            ('URGENTE', 'Urgente'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Priorité de la mission',
        initial='NORMALE'
    )
    instructions = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Instructions spéciales pour le transporteur (optionnel)'
        }),
        label='Instructions spéciales',
        required=False
    )
    
    def __init__(self, commande=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if commande:
            # Filtrer les transporteurs disponibles et capables
            self.fields['transporteur'].queryset = Transporteur.objects.filter(
                disponible=True,
                actif=True,
                capacite_charge__gte=commande.poids
            ).select_related('user')

class FiltreCommandesForm(forms.Form):
    """Formulaire pour filtrer les commandes"""
    statut = forms.ChoiceField(
        choices=[('', 'Tous les statuts')] + Commande.STATUT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )
    date_debut = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        required=False,
        label='Du'
    )
    date_fin = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        required=False,
        label='Au'
    )
    ville = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filtrer par ville...'
        }),
        required=False
    )

# Widgets personnalisés pour améliorer l'UX
class DatePickerWidget(forms.DateInput):
    """Widget pour sélection de date avec calendrier"""
    def __init__(self, attrs=None):
        default_attrs = {'class': 'form-control', 'type': 'date'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)

class AutocompleteWidget(forms.TextInput):
    """Widget avec autocomplétion"""
    def __init__(self, datalist_id, attrs=None):
        default_attrs = {'class': 'form-control', 'list': datalist_id}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)