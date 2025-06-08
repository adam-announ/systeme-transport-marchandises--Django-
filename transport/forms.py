# transport/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Commande, Adresse, Client

class InscriptionForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    telephone = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'form-control'}))
    adresse = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'telephone', 'adresse']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs['class'] = 'form-control'
        self.fields['password2'].widget.attrs['class'] = 'form-control'
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            Client.objects.create(
                user=user,
                telephone=self.cleaned_data['telephone'],
                adresse=self.cleaned_data['adresse']
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
            'pays': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pays'}),
        }

class CommandeForm(forms.ModelForm):
    class Meta:
        model = Commande
        fields = ['poids', 'type_marchandise']
        widgets = {
            'poids': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Poids en kg'}),
            'type_marchandise': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Type de marchandise'}),
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