"""
Vues pour l'authentification
"""

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from core.models import User

def login_view(request):
    """Page de connexion"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            # Redirection selon le rôle
            if user.role == 'client':
                return redirect('client:dashboard')
            elif user.role == 'admin':
                return redirect('admin_panel:dashboard')
            elif user.role == 'planificateur':
                return redirect('planificateur:dashboard')
            elif user.role == 'transporteur':
                return redirect('transporteur:dashboard')
        else:
            messages.error(request, 'Identifiants incorrects')
    
    return render(request, 'auth/login.html')

def register_view(request):
    """Page d'inscription"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role', 'client')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Ce nom d\'utilisateur existe déjà')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Cet email est déjà utilisé')
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role=role
            )
            messages.success(request, 'Compte créé avec succès')
            return redirect('auth:login')
    
    return render(request, 'auth/register.html')

@login_required
def logout_view(request):
    """Déconnexion"""
    logout(request)
    return redirect('auth:login')

@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    """API de connexion"""
    username = request.data.get('username')
    password = request.data.get('password')
    
    user = authenticate(username=username, password=password)
    if user:
        login(request, user)
        return Response({
            'success': True,
            'user': {
                'id': str(user.id),
                'username': user.username,
                'role': user.role,
                'email': user.email
            }
        })
    
    return Response({
        'success': False,
        'message': 'Identifiants incorrects'
    }, status=status.HTTP_401_UNAUTHORIZED)