from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction
from .models import Perfil
from .forms import RegistroForm, PerfilForm

def es_admin(user):
    """Verifica si el usuario es administrador"""
    return user.is_authenticated and hasattr(user, 'perfil') and user.perfil.es_admin()

def puede_editar(user):
    """Verifica si el usuario puede editar contenido"""
    return user.is_authenticated and hasattr(user, 'perfil') and user.perfil.puede_editar()

def registro(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                # Crear perfil automáticamente
                Perfil.objects.create(user=user, rol='usuario')
                username = form.cleaned_data.get('username')
                messages.success(request, f'Cuenta creada para {username}. ¡Ya puedes iniciar sesión!')
                return redirect('login')
    else:
        form = RegistroForm()
    return render(request, 'registration/registro.html', {'form': form})

@login_required
def perfil(request):
    perfil, created = Perfil.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('perfil')
    else:
        form = PerfilForm(instance=perfil)
    return render(request, 'usuarios/perfil.html', {'form': form, 'perfil': perfil})

@user_passes_test(es_admin)
def panel_admin(request):
    """Panel de administración para gestionar usuarios"""
    usuarios = User.objects.select_related('perfil').all()
    return render(request, 'usuarios/admin_panel.html', {'usuarios': usuarios})

@user_passes_test(es_admin)
def cambiar_rol(request, user_id):
    """Permite al admin cambiar el rol de un usuario"""
    usuario = get_object_or_404(User, id=user_id)
    perfil, created = Perfil.objects.get_or_create(user=usuario)
    
    if request.method == 'POST':
        nuevo_rol = request.POST.get('rol')
        if nuevo_rol in ['usuario', 'moderador', 'administrador']:
            perfil.rol = nuevo_rol
            perfil.save()
            messages.success(request, f'Rol de {usuario.username} cambiado a {nuevo_rol}.')
        else:
            messages.error(request, 'Rol inválido.')
    
    return redirect('panel_admin')

