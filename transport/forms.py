# transport/forms.py
from django import forms
from .models import Commande, Adresse

class AdresseForm(forms.ModelForm):
    class Meta:
        model = Adresse
        fields = ['rue', 'ville', 'code_postal', 'pays']
        widgets = {
            'rue': forms.TextInput(attrs={'class': 'form-control'}),
            'ville': forms.TextInput(attrs={'class': 'form-control'}),
            'code_postal': forms.TextInput(attrs={'class': 'form-control'}),
            'pays': forms.TextInput(attrs={'class': 'form-control'}),
        }

class CommandeForm(forms.ModelForm):
    class Meta:
        model = Commande
        fields = ['poids', 'type_marchandise']
        widgets = {
            'poids': forms.NumberInput(attrs={'class': 'form-control'}),
            'type_marchandise': forms.TextInput(attrs={'class': 'form-control'}),
        }