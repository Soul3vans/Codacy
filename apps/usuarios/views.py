"""VISTAS DE ADMINISTRACION"""
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import logout as auth_logout, login, authenticate, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from .models import Perfil, PasswordResetAudit
from .forms import PerfilForm, RegistroForm, ActualizarPerfilForm
import logging
import secrets

logger = logging.getLogger(__name__)

def get_user_session_status(user):
    """Determina si un usuario está activo basado en su última actividad."""
    if hasattr(user, 'perfil') and user.perfil and user.perfil.last_activity:
        online_threshold = timezone.now() - timedelta(minutes=5)
        if user.perfil.last_activity > online_threshold:
            return 'Activo'
    return 'Inactivo'

@login_required
def perfil(request):
    """Vista para mostrar el perfil del usuario actual."""
    try:
        perfil = request.user.perfil
    except Perfil.DoesNotExist:
        perfil = Perfil.objects.create(user=request.user)

    return render(request, 'usuarios/perfil.html', {'user_profile': perfil})

@login_required
def actualizar_perfil(request):
    """Vista para actualizar la información del perfil del usuario."""
    try:
        user_profile = request.user.perfil
    except Perfil.DoesNotExist:
        user_profile = Perfil.objects.create(user=request.user)

    if request.method == 'POST':
        user_form = ActualizarPerfilForm(request.POST, user=request.user, instance=request.user)
        profile_form = PerfilForm(request.POST, request.FILES, instance=user_profile)

        if user_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                user_form.save()
                profile_form.save()
            messages.success(request, 'Tu perfil ha sido actualizado exitosamente.')
            return redirect('perfil')
        else:
            messages.error(request, 'Hubo un error al actualizar el perfil. Por favor, revisa los campos.')
    else:
        user_form = ActualizarPerfilForm(user=request.user, instance=request.user)
        profile_form = PerfilForm(instance=user_profile)

    return render(request, 'usuarios/editar_perfil.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })

def es_admin(user):
    """Verifica si el usuario es administrador."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return hasattr(user, 'perfil') and user.perfil and user.perfil.es_admin

def puede_editar(user):
    """Verifica si el usuario puede editar contenido."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return hasattr(user, 'perfil') and user.perfil and user.perfil.puede_editar

def es_moderador_o_admin(user):
    """Verifica si el usuario es moderador o admin."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return (hasattr(user, 'perfil') and user.perfil and
            (user.perfil.es_moderador or user.perfil.es_admin))

def asegurar_perfil_superuser(sender, instance, created, **kwargs):
    """Signal para crear perfil automáticamente para superusers."""
    if created and instance.is_superuser:
        Perfil.objects.get_or_create(
            user=instance,
            defaults={
                'es_admin': True,
                'puede_editar': True,
                'es_moderador': False
            }
        )

def login_view(request):
    """Vista personalizada para login."""
    if request.user.is_authenticated:
        messages.success(request, 'Bienvenido.')
        return redirect('inicio')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')

        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    if remember_me:
                        request.session.set_expiry(settings.SESSION_COOKIE_AGE)
                    else:
                        request.session.set_expiry(0)

                    perfil, created = Perfil.objects.get_or_create(user=user)
                    perfil.last_activity = timezone.now()
                    perfil.save()

                    messages.success(request, f'¡Bienvenido {user.first_name or user.username}!')
                    next_page = request.GET.get('next', 'inicio')
                    return redirect(next_page)
                else:
                    messages.error(request, 'Tu cuenta está desactivada.')
            else:
                messages.error(request, 'Nombre de usuario o contraseña incorrectos.')
        else:
            messages.error(request, 'Por favor, completa todos los campos.')
    return render(request, 'registration/login.html', {'title': 'Iniciar Sesión'})

def logout_view(request):
    """Vista para cerrar sesión."""
    username = request.user.username if request.user.is_authenticated else 'Usuario anónimo'
    auth_logout(request)
    messages.success(request, 'Has cerrado sesión correctamente.')
    return redirect('inicio')


def registro(request):
    """Vista para registro de nuevos usuarios."""
    if request.method == 'POST':
        form = RegistroForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                username = form.cleaned_data.get('username')
                password = form.cleaned_data.get('password1')
                user = authenticate(username=username, password=password)
                if user is not None:
                    login(request, user)
                    messages.success(request, f'¡Bienvenido {user.first_name}! Tu cuenta ha sido creada exitosamente.')
                    return redirect('inicio')
                else:
                    messages.success(request, 'Tu cuenta ha sido creada exitosamente. Por favor, inicia sesión.')
                    return redirect('login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    if field == 'username' and 'already exists' in str(error):
                        messages.error(request, 'Este nombre de usuario ya existe. Por favor, elige otro.')
                    else:
                        messages.error(request, f'Error en {field}: {error}')
    else:
        form = RegistroForm()

    return render(request, 'registration/registro.html', {
        'form': form,
        'title': 'Registro de Usuario'
    })

@login_required
@user_passes_test(es_admin)
def panel_admin(request):
    """Panel principal de administración."""
    try:
        total_usuarios = User.objects.count()
        usuarios_activos = User.objects.filter(is_active=True).count()
        usuarios = User.objects.select_related('perfil').order_by('-date_joined')
        administradores_count = User.objects.filter(perfil__es_admin=True).count()
        moderadores_count = User.objects.filter(perfil__es_moderador=True).count()
        usuarios_recientes = User.objects.select_related('perfil').order_by('-date_joined')[:10]

        actividad_reciente = [{
            'descripcion': f'Nuevo usuario registrado: {usuario.username}',
            'detalle': f'{usuario.get_full_name() or usuario.username} se registró en el sistema',
            'fecha': usuario.date_joined,
            'usuario': usuario
        } for usuario in usuarios_recientes[:5]]

        return render(request, 'usuarios/admin_panel.html', {
            'title': 'Panel de Administración',
            'total_usuarios': total_usuarios,
            'usuarios_activos': usuarios_activos,
            'usuarios_recientes': usuarios_recientes,
            'usuarios': usuarios,
            'administradores_count': administradores_count,
            'moderadores_count': moderadores_count,
            'usuarios_activos_count': usuarios_activos,
            'actividad_reciente': actividad_reciente,
        })
    except Exception as e:
        logger.error(f"Error en panel admin: {e}")
        messages.error(request, 'Error al cargar el panel de administración.')
        return redirect('inicio')

@login_required
@user_passes_test(es_admin)
def gestionar_usuarios(request):
    """Vista para gestionar usuarios."""
    try:
        search_query = request.GET.get('search', '')
        status_filter = request.GET.get('status', 'all')

        usuarios = User.objects.select_related('perfil').all()

        if search_query:
            usuarios = usuarios.filter(
                Q(username__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )

        if status_filter != 'all':
            filter_mapping = {
                'active': {'is_active': True},
                'inactive': {'is_active': False},
                'admin': {'perfil__es_admin': True},
                'moderator': {'perfil__es_moderador': True}
            }
            usuarios = usuarios.filter(**filter_mapping.get(status_filter, {}))

        online_threshold = timezone.now() - timedelta(minutes=5)
        for user in usuarios:
            user.estado_sesion = get_user_session_status(user)

        paginator = Paginator(usuarios, 20)
        page_obj = paginator.get_page(request.GET.get('page'))

        return render(request, 'admin/gestionar_usuarios.html', {
            'title': 'Gestionar Usuarios',
            'usuarios': page_obj,
            'search_query': search_query,
            'status_filter': status_filter,
            'total_usuarios': usuarios.count(),
        })
    except Exception as e:
        logger.error(f"Error en gestionar usuarios: {e}")
        messages.error(request, 'Error al cargar la gestión de usuarios.')
        return redirect('panel_admin')

@login_required
@user_passes_test(es_admin)
@require_http_methods(["POST"])
def cambiar_estado_usuario_view(request, user_id):
    """Cambiar estado activo/inactivo de un usuario."""
    try:
        usuario = get_object_or_404(User, id=user_id)
        if usuario == request.user:
            messages.error(request, 'No puedes desactivar tu propia cuenta.')
            return redirect('gestionar_usuarios')

        usuario.is_active = not usuario.is_active
        usuario.save()
        estado = 'activado' if usuario.is_active else 'desactivado'
        messages.success(request, f'Usuario {usuario.username} ha sido {estado}.')
    except Exception as e:
        logger.error(f"Error al cambiar estado de usuario: {e}")
        messages.error(request, 'Error al cambiar el estado del usuario.')

    return redirect('gestionar_usuarios')

@login_required
@user_passes_test(es_admin)
@require_http_methods(["POST"])
def cambiar_rol_usuario_view(request, user_id):
    """Cambiar rol de un usuario."""
    try:
        usuario = get_object_or_404(User, id=user_id)
        if usuario == request.user:
            messages.error(request, 'No puedes cambiar tu propio rol.')
            return redirect('panel_admin')

        perfil, created = Perfil.objects.get_or_create(user=usuario)
        nuevo_rol = request.POST.get('rol', 'usuario')

        perfil.es_admin = False
        perfil.es_moderador = False
        perfil.puede_editar = False

        if nuevo_rol == 'administrador':
            perfil.es_admin = True
            perfil.puede_editar = True
        elif nuevo_rol == 'moderador':
            perfil.es_moderador = True
            perfil.puede_editar = True

        perfil.save()
        messages.success(request, f'Rol de {usuario.username} cambiado a {nuevo_rol} correctamente.')
    except Exception as e:
        logger.error(f"Error al cambiar rol: {e}")
        messages.error(request, 'Error al cambiar el rol del usuario.')

    return redirect('panel_admin')

@login_required
@user_passes_test(es_admin)
@require_http_methods(["POST"])
def eliminar_usuario(request, user_id):
    """Eliminar un usuario del sistema."""
    try:
        usuario = get_object_or_404(User, id=user_id)
        if usuario == request.user:
            messages.error(request, "No puedes eliminar tu propia cuenta.")
            return redirect('gestionar_usuarios')

        username = usuario.username
        usuario.delete()
        messages.success(request, f'Usuario {username} eliminado correctamente.')
    except Exception as e:
        logger.error(f"Error al eliminar usuario: {e}")
        messages.error(request, 'Error al eliminar el usuario.')

    return redirect('gestionar_usuarios')

@login_required
@user_passes_test(es_admin)
def debug_user_info(request, user_id):
    """Ver detalles de un usuario específico."""
    try:
        usuario = get_object_or_404(User, id=user_id)
        estado_sesion = get_user_session_status(usuario)

        return render(request, 'admin/ver_usuario.html', {
            'title': f'Usuario: {usuario.username}',
            'usuario': usuario,
            'estado_sesion': estado_sesion,
        })
    except Exception as e:
        logger.error(f"Error al ver usuario: {e}")
        messages.error(request, 'Error al cargar los detalles del usuario.')
        return redirect('gestionar_usuarios')

def password_reset_request(request):
    if request.method == "POST":
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            profile = user.profile
            # Generar un código único y su expiración
            recovery_code = secrets.token_urlsafe(32)
            code_expiry = timezone.now() + timedelta(minutes=30)  # 30 minutos de validez

            # Guardar el código y expiración en el perfil
            profile.recovery_code = recovery_code
            profile.recovery_code_expiry = code_expiry
            profile.recovery_code_used = False
            profile.save()

            # Registrar auditoría
            PasswordResetAudit.objects.create(
                user=user,
                action='request',
                ip=request.META.get('REMOTE_ADDR'),
                timestamp=timezone.now(),
            )

            # Enviar el código por correo electrónico
            send_mail(
                'Recuperación de Contraseña',
                f'Tu código de recuperación es: {recovery_code}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            messages.success(request, "Se ha enviado un código de recuperación a tu correo.")
            return redirect('password_reset_confirm', uidb64=user.id, token=recovery_code)
        except User.DoesNotExist:
            return render(request, 'password_reset_request.html', {'error_message': 'El correo electrónico no está registrado.'})

    return render(request, 'registration/password_reset_request.html')

def password_reset_confirm(request, uidb64, token):
    try:
        user = User.objects.get(id=uidb64)
        profile = user.profile
        # Verificar código, expiración y si ya fue usado
        if (profile.recovery_code == token and
            not profile.recovery_code_used and
            profile.recovery_code_expiry and
            timezone.now() < profile.recovery_code_expiry):

            if request.method == "POST":
                new_password = request.POST.get('new_password')
                user.set_password(new_password)
                user.save()
                # Marcar el código como usado
                profile.recovery_code_used = True
                profile.save()
                # Registrar auditoría
                PasswordResetAudit.objects.create(
                    user=user,
                    action='reset',
                    ip=request.META.get('REMOTE_ADDR'),
                    timestamp=timezone.now(),
                )
                messages.success(request, "Contraseña restablecida correctamente.")
                return redirect('login')
            return render(request, 'password_reset_confirm.html', {'valid': True})
        else:
            messages.error(request, "El código es inválido, ya fue usado o ha expirado.")
            return render(request, 'password_reset_confirm.html', {'valid': False})
    except User.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
        return redirect('password_reset_request')