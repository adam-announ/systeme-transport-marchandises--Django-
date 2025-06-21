# transport/forms.py - Version mise à jour
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import (
    Commande, Adresse, Client, MissionTransporteur, 
    Incident, Transporteur
)

class InscriptionForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    telephone = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'form-control'}))
    adresse = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'class': 'form-control'}))
    type_compte = forms.ChoiceField(
        choices=[('client', 'Client'), ('transporteur', 'Transporteur')],
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='client'
    )
    
    # Champs spécifiques aux transporteurs
    matricule = forms.CharField(
        max_length=50, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 123-ABC-45'})
    )
    type_vehicule = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Camion 20T'})
    )
    capacite_charge = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Capacité en kg'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'telephone', 'adresse', 'type_compte']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs['class'] = 'form-control'
        self.fields['password2'].widget.attrs['class'] = 'form-control'
    
    def clean(self):
        cleaned_data = super().clean()
        type_compte = cleaned_data.get('type_compte')
        
        if type_compte == 'transporteur':
            if not cleaned_data.get('matricule'):
                raise forms.ValidationError('Le matricule est obligatoire pour les transporteurs.')
            if not cleaned_data.get('type_vehicule'):
                raise forms.ValidationError('Le type de véhicule est obligatoire pour les transporteurs.')
            if not cleaned_data.get('capacite_charge'):
                raise forms.ValidationError('La capacité de charge est obligatoire pour les transporteurs.')
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
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
    class Meta:
        model = Adresse
        fields = ['rue', 'ville', 'code_postal', 'pays']
        widgets = {
            'rue': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Numéro et nom de rue'}),
            'ville': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ville'}),
            'code_postal': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Code postal'}),
            'pays': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pays', 'value': 'Maroc'}),
        }

class CommandeForm(forms.ModelForm):
    class Meta:
        model = Commande
        fields = ['poids', 'type_marchandise', 'priorite']
        widgets = {
            'poids': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Poids en kg'}),
            'type_marchandise': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Type de marchandise'}),
            'priorite': forms.Select(attrs={'class': 'form-control'}, choices=[
                (0, 'Normale'),
                (1, 'Haute'),
                (2, 'Urgente')
            ]),
        }

class RapportForm(forms.Form):
    date_debut = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Date de début'
    )
    date_fin = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Date de fin'
    )
    format_export = forms.ChoiceField(
        choices=[('pdf', 'PDF'), ('csv', 'CSV')],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Format d\'export'
    )

class StatutLivraisonForm(forms.Form):
    STATUT_CHOICES = [
        ('EN_COURS', 'En cours'),
        ('TERMINEE', 'Terminée'),
        ('ANNULEE', 'Annulée'),
    ]
    
    statut = forms.ChoiceField(
        choices=STATUT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Nouveau statut'
    )
    commentaire = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label='Commentaire',
        required=False
    )

class IncidentForm(forms.ModelForm):
    class Meta:
        model = Incident
        fields = ['type', 'description', 'photo']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': 'Décrivez l\'incident en détail...'
            }),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'type': 'Type d\'incident',
            'description': 'Description détaillée',
            'photo': 'Photo (optionnel)'
        }

class AffectationTransporteurForm(forms.Form):
    transporteur = forms.ModelChoiceField(
        queryset=Transporteur.objects.filter(disponible=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Sélectionner un transporteur'
    )
    priorite = forms.ChoiceField(
        choices=[
            ('NORMALE', 'Normale'),
            ('HAUTE', 'Haute'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Priorité de la mission',
        initial='NORMALE'
    )
    instructions_speciales = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label='Instructions spéciales',
        required=False
    )