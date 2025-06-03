from django import forms
from .models import Utilisateur, Commande, Livraison, Incident

class LoginForm(forms.Form):
    username = forms.CharField(label="Nom d'utilisateur")
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)

class CommandeForm(forms.ModelForm):
    class Meta:
        model = Commande
        fields = ['description', 'poids', 'montant', 'adresse_livraison']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'adresse_livraison': forms.Textarea(attrs={'rows': 3}),
        }

class AffecterCommandeForm(forms.ModelForm):
    class Meta:
        model = Livraison
        fields = ['transporteur', 'date_prevue']
        widgets = {
            'date_prevue': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class StatutLivraisonForm(forms.ModelForm):
    class Meta:
        model = Livraison
        fields = ['statut', 'date_effective']
        widgets = {
            'date_effective': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class IncidentForm(forms.ModelForm):
    class Meta:
        model = Incident
        fields = ['type_incident', 'description', 'gravite']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
