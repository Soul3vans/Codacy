# VISTAS DE ADMINISTRACIÓN
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import logout as auth_logout, login, authenticate, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django import forms
from datetime import timedelta
from .models import Post, Archivo, Perfil
from .forms import PostForm, ArchivoForm, PerfilForm, RegistroForm, ActualizarPerfilForm
import json
import logging

logger = logging.getLogger(__name__)

def home(request):
    return render(request, 'dashboard/index.html')

@login_required
def perfil(request):
    """Vista para mostrar el perfil del usuario actual"""
    try:
        # Intenta obtener el perfil. Si no existe, lanza una excepción.
        perfil = Perfil.objects.get(user=request.user)
    except Perfil.DoesNotExist:
        # Si no existe, lo creamos.
        perfil = Perfil.objects.create(user=request.user)
    
    # Obtener estadísticas del usuario (código que ya tienes)
    # ...
    
    context = {
        'user_profile': perfil,
        # ... otras variables de contexto
    }
    return render(request, 'usuarios/perfil.html', context)

@login_required
def actualizar_perfil(request):
    """Vista para actualizar la información del perfil del usuario"""
    try:
        # Asegurarse de obtener la instancia del perfil del usuario
        user_profile = request.user.perfil
    except Perfil.DoesNotExist:
        # Si el perfil no existe por alguna razón, créalo
        user_profile = Perfil.objects.create(user=request.user)

    if request.method == 'POST':
        user_form = ActualizarPerfilForm(request.POST, user=request.user, instance=request.user)
        # Usa la instancia de perfil obtenida explícitamente
        profile_form = PerfilForm(request.POST, request.FILES, instance=user_profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                user_form.save()
                profile_form.save()
            
            messages.success(request, 'Tu perfil ha sido actualizado exitosamente.')
            
            return redirect('perfil')
        else:
            # Si el formulario no es válido, los errores se mostrarán en la plantilla
            messages.error(request, 'Hubo un error al actualizar el perfil. Por favor, revisa los campos.')
            
    else:
        user_form = ActualizarPerfilForm(user=request.user, instance=request.user)
        # Usa la instancia de perfil obtenida explícitamente
        profile_form = PerfilForm(instance=user_profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }
    return render(request, 'usuarios/editar_perfil.html', context)
        

@login_required
def cambiar_password(request):
    """Vista para cambiar la contraseña del usuario"""
    if request.method == 'POST':
        try:
            # Crear formulario con los datos POST
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                # Guardar nueva contraseña
                user = form.save()
                # Mantener la sesión activa después del cambio de contraseña
                update_session_auth_hash(request, user)
                logger.info(f"Contraseña cambiada para usuario {user.username}")
                messages.success(request, 'Tu contraseña ha sido cambiada correctamente.')
            else:
                # Mostrar errores específicos del formulario
                for field, errors in form.errors.items():
                    for error in errors:
                        if 'old_password' in field:
                            messages.error(request, 'La contraseña actual es incorrecta.')
                        elif 'new_password2' in field:
                            messages.error(request, 'Las contraseñas nuevas no coinciden.')
                        elif 'new_password1' in field:
                            messages.error(request, 'La nueva contraseña no cumple con los requisitos de seguridad.')
                        else:
                            messages.error(request, f'Error: {error}')
                            
        except Exception as e:
            logger.error(f"Error al cambiar contraseña de {request.user.username}: {e}")
            messages.error(request, 'Error al cambiar la contraseña. Por favor, intenta nuevamente.')
    
    return redirect('perfil')

# FUNCIONES AUXILIARES PARA VERIFICAR PERMISOS
def es_admin(user):
    """Verifica si el usuario es administrador"""
    if not user.is_authenticated:
        return False
    
    # Los superusers siempre son admins
    if user.is_superuser:
        return True
    
    # Verificar perfil
    return (hasattr(user, 'perfil') and 
            user.perfil and 
            user.perfil.es_admin)

def puede_editar(user):
    """Verifica si el usuario puede editar contenido"""
    if not user.is_authenticated:
        return False
    
    # Los superusers siempre pueden editar
    if user.is_superuser:
        return True
    
    # Verificar perfil
    return (hasattr(user, 'perfil') and 
            user.perfil and 
            user.perfil.puede_editar)

def es_moderador_o_admin(user):
    """Verifica si el usuario es moderador o admin"""
    if not user.is_authenticated:
        return False
    
    # Los superusers siempre son admins
    if user.is_superuser:
        return True
    
    # Verificar perfil
    return (hasattr(user, 'perfil') and 
            user.perfil and 
            (user.perfil.es_moderador or user.perfil.es_admin))

def asegurar_perfil_superuser(sender, instance, created, **kwargs):
    """Signal para crear perfil automáticamente para superusers"""
    if created and instance.is_superuser:
        perfil, created = Perfil.objects.get_or_create(
            user=instance,
            defaults={
                'es_admin': True,
                'puede_editar': True,
                'es_moderador': False
            }
        )

def login_view(request):
    """Vista personalizada para login"""
    if request.user.is_authenticated:
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
                        # La sesion no expirara hasta que se acabe la cooke
                        request.session.set_expiry(settings.SESSION_COOKIE_AGE)
                    else:
                        # La sesion expirara cuando cierren el navegador
                        request.session.set_expiry(0)

                    # Actualizar last_activity al hacer login
                    perfil, created = Perfil.objects.get_or_create(user=user)
                    perfil.last_activity = timezone.now()
                    perfil.save()
                    
                    logger.info(f"Usuario {username} inició sesión correctamente")
                    messages.success(request, f'¡Bienvenido {user.first_name or user.username}!')
                    
                    # Redirigir a la página solicitada o al inicio
                    next_page = request.GET.get('next', 'inicio')
                    return redirect(next_page)
                else:
                    messages.error(request, 'Tu cuenta está desactivada.')
            else:
                messages.error(request, 'Nombre de usuario o contraseña incorrectos.')
        else:
            messages.error(request, 'Por favor, completa todos los campos.')
    
    context = {
        'title': 'Iniciar Sesión'
    }
    return render(request, 'registration/login.html', context)

def logout_view(request):
    """Vista para cerrar sesión"""
    username = request.user.username if request.user.is_authenticated else 'Usuario anónimo'
    auth_logout(request)
    logger.info(f"Usuario {username} cerró sesión")
    messages.success(request, 'Has cerrado sesión correctamente.')
    return redirect('inicio')

def registro(request):
    """Vista para registro de nuevos usuarios"""
    if request.method == 'POST':
        try:
            form = RegistroForm(request.POST, request.FILES)
            if form.is_valid():
                with transaction.atomic():
                    # Crear el usuario
                    user = form.save()
                    
                    # Crear perfil automáticamente
                    #Perfil.objects.create(user=user)
                    
                    # Autenticar y hacer login automáticamente
                    username = form.cleaned_data.get('username')
                    password = form.cleaned_data.get('password1')
                    user = authenticate(username=username, password=password)
                    
                    if user is not None:
                        login(request, user)
                        logger.info(f"Usuario {username} registrado y autenticado correctamente")
                        messages.success(request, f'¡Bienvenido {user.first_name}! Tu cuenta ha sido creada exitosamente.')
                        return redirect('inicio')
                    else:
                        logger.error(f"Error al autenticar usuario recién registrado: {username}")
                        messages.success(request, 'Tu cuenta ha sido creada exitosamente. Por favor, inicia sesión.')
                        return redirect('login')
            else:
                # Mostrar errores del formulario
                for field, errors in form.errors.items():
                    for error in errors:
                        if field == 'username':
                            if 'already exists' in str(error):
                                messages.error(request, 'Este nombre de usuario ya existe. Por favor, elige otro.')
                            else:
                                messages.error(request, f'Error en nombre de usuario: {error}')
                        elif field == 'email':
                            messages.error(request, f'Error en correo electrónico: {error}')
                        elif field == 'password2':
                            messages.error(request, 'Las contraseñas no coinciden.')
                        elif field == 'password1':
                            messages.error(request, f'Error en contraseña: {error}')
                        else:
                            messages.error(request, f'Error en {field}: {error}')
                            
        except Exception as e:
            logger.error(f"Error durante el registro: {e}")
            messages.error(request, 'Error al crear la cuenta. Por favor, intenta nuevamente.')
            form = RegistroForm()
    else:
        form = RegistroForm()
    
    context = {
        'form': form,
        'title': 'Registro de Usuario'
    }
    return render(request, 'registration/registro.html', context)

# VISTAS DE ADMINISTRACIÓN
@login_required
@user_passes_test(es_admin)
def panel_admin(request):
    """Panel principal de administración"""
    try:
        # Estadísticas generales
        total_usuarios = User.objects.count()
        usuarios_activos = User.objects.filter(is_active=True).count()
        
        # Manejar Post de forma segura
        total_posts = 0
        posts_publicados = 0
        posts_recientes = []
        
        try:
            total_posts = Post.objects.count()
            posts_publicados = Post.objects.filter(publicado=True).count()
            posts_recientes = Post.objects.select_related('usuario').order_by('-fecha_creacion')[:10]
        except:
            # Si el modelo Post no existe o hay algún error
            pass
        
        # Obtener todos los usuarios con sus perfiles para la tabla
        usuarios = User.objects.select_related('perfil').order_by('-date_joined')
        
        # Contar usuarios por rol
        administradores_count = User.objects.filter(perfil__es_admin=True).count()
        moderadores_count = User.objects.filter(perfil__es_moderador=True).count()
        usuarios_activos_count = User.objects.filter(is_active=True).count()
        
        # Usuarios recientes (últimos 10)
        usuarios_recientes = User.objects.select_related('perfil').order_by('-date_joined')[:10]
        
        # Actividad reciente basada en usuarios nuevos
        actividad_reciente = []
        for usuario in usuarios_recientes[:5]:
            actividad_reciente.append({
                'descripcion': f'Nuevo usuario registrado: {usuario.username}',
                'detalle': f'{usuario.get_full_name() or usuario.username} se registró en el sistema',
                'fecha': usuario.date_joined,
                'usuario': usuario
            })
        
        context = {
            'title': 'Panel de Administración',
            'total_usuarios': total_usuarios,
            'usuarios_activos': usuarios_activos,
            'total_posts': total_posts,
            'posts_publicados': posts_publicados,
            'usuarios_recientes': usuarios_recientes,
            'posts_recientes': posts_recientes,
            'usuarios': usuarios,
            'administradores_count': administradores_count,
            'moderadores_count': moderadores_count,
            'usuarios_activos_count': usuarios_activos_count,
            'actividad_reciente': actividad_reciente,
        }
        return render(request, 'usuarios/admin_panel.html', context)
        
    except Exception as e:
        logger.error(f"Error en panel admin: {e}")
        messages.error(request, 'Error al cargar el panel de administración.')
        return redirect('inicio')

@login_required
@user_passes_test(es_admin)
def gestionar_usuarios(request):
    """Vista para gestionar usuarios"""
    try:
        # Filtros de búsqueda
        search_query = request.GET.get('search', '')
        status_filter = request.GET.get('status', 'all')
        
        # Consulta base
        usuarios = User.objects.select_related('perfil').all()
        
        # Aplicar filtros
        if search_query:
            usuarios = usuarios.filter(
                Q(username__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        
        if status_filter == 'active':
            usuarios = usuarios.filter(is_active=True)
        elif status_filter == 'inactive':
            usuarios = usuarios.filter(is_active=False)
        elif status_filter == 'admin':
            usuarios = usuarios.filter(perfil__es_admin=True)
        elif status_filter == 'moderator':
            usuarios = usuarios.filter(perfil__es_moderador=True)
        
        # Añadir estado de sesión en tiempo real
        online_threshold_minutes = 5
        online_threshold = timezone.now() - timedelta(minutes=online_threshold_minutes)
        logger.info(f"View: Online threshold set to: {online_threshold}")
        
        for user in usuarios:
            # Asegurar que el usuario tenga perfil y last_activity
            if hasattr(user, 'perfil') and user.perfil and user.perfil.last_activity:
                logger.info(f"View: Checking user {user.username}. Last activity: {user.perfil.last_activity}")
                if user.perfil.last_activity > online_threshold:
                    user.estado_sesion = 'Activo'
                    logger.info(f"View: User {user.username} is considered Active.")
                else:
                    user.estado_sesion = 'Inactivo'
                    logger.info(f"View: User {user.username} is considered Inactive.")
            else:
                user.estado_sesion = 'Inactivo'
                logger.info(f"View: User {user.username} has no profile or last_activity. Set Inactive.")
        
        # Paginación
        paginator = Paginator(usuarios, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'title': 'Gestionar Usuarios',
            'usuarios': page_obj,
            'search_query': search_query,
            'status_filter': status_filter,
            'total_usuarios': usuarios.count(),
        }
        return render(request, 'admin/gestionar_usuarios.html', context)
        
    except Exception as e:
        logger.error(f"Error en gestionar usuarios: {e}")
        messages.error(request, 'Error al cargar la gestión de usuarios.')
        return redirect('panel_admin')

@login_required
@user_passes_test(es_admin)
@require_http_methods(["POST"])
def cambiar_estado_usuario_view(request, user_id):
    """Cambiar estado activo/inactivo de un usuario"""
    try:
        usuario = get_object_or_404(User, id=user_id)
        
        # No permitir desactivar al propio admin
        if usuario == request.user:
            messages.error(request, 'No puedes desactivar tu propia cuenta.')
            return redirect('gestionar_usuarios')
        
        # Cambiar estado
        usuario.is_active = not usuario.is_active
        usuario.save()
        
        estado = 'activado' if usuario.is_active else 'desactivado'
        logger.info(f"Usuario {usuario.username} fue {estado} por {request.user.username}")
        messages.success(request, f'Usuario {usuario.username} ha sido {estado}.')
        
    except Exception as e:
        logger.error(f"Error al cambiar estado de usuario: {e}")
        messages.error(request, 'Error al cambiar el estado del usuario.')
    
    return redirect('gestionar_usuarios')

@login_required
@user_passes_test(es_admin)
@require_http_methods(["POST"])
def cambiar_rol_usuario_view(request, user_id):
    """Cambiar rol de un usuario"""
    try:
        usuario = get_object_or_404(User, id=user_id)
        
        # No permitir cambiar el rol del propio admin
        if usuario == request.user:
            messages.error(request, 'No puedes cambiar tu propio rol.')
            return redirect('panel_admin')
        
        # Obtener o crear perfil
        perfil, created = Perfil.objects.get_or_create(user=usuario)
        
        # Obtener el nuevo rol del POST
        nuevo_rol = request.POST.get('rol', 'usuario')
        
        # Resetear todos los permisos
        perfil.es_admin = False
        perfil.es_moderador = False
        perfil.puede_editar = False
        
        # Asignar el nuevo rol
        if nuevo_rol == 'administrador':
            perfil.es_admin = True
            perfil.puede_editar = True
        elif nuevo_rol == 'moderador':
            perfil.es_moderador = True
            perfil.puede_editar = True
        elif nuevo_rol == 'usuario':
            # Los permisos ya están en False
            pass
        
        perfil.save()
        
        logger.info(f"Rol de {usuario.username} cambiado a {nuevo_rol} por {request.user.username}")
        messages.success(request, f'Rol de {usuario.username} cambiado a {nuevo_rol} correctamente.')
        
    except Exception as e:
        logger.error(f"Error al cambiar rol: {e}")
        messages.error(request, 'Error al cambiar el rol del usuario.')
    
    return redirect('panel_admin')

@login_required
@user_passes_test(es_admin)
@require_http_methods(["POST"])
def eliminar_usuario(request, user_id):
    """Eliminar un usuario del sistema"""
    try:
        usuario = get_object_or_404(User, id=user_id)
        
        # No permitir eliminar al propio admin
        if usuario == request.user:
            messages.error(request, "No puedes eliminar tu propia cuenta.")
            return redirect('gestionar_usuarios')
        
        username = usuario.username
        usuario.delete()
        
        logger.info(f"Usuario {username} eliminado por {request.user.username}")
        messages.success(request, f'Usuario {username} eliminado correctamente.')
        
    except Exception as e:
        logger.error(f"Error al eliminar usuario: {e}")
        messages.error(request, 'Error al eliminar el usuario.')
    
    return redirect('gestionar_usuarios')

@login_required
@user_passes_test(es_admin)
def debug_user_info(request, user_id):
    """Ver detalles de un usuario específico"""
    try:
        usuario = get_object_or_404(User, id=user_id)
        
        # Estadísticas del usuario
        posts_count = 0
        posts_publicados = 0
        
        try:
            posts_count = Post.objects.filter(usuario=usuario).count()
            posts_publicados = Post.objects.filter(usuario=usuario, publicado=True).count()
        except:
            # Si el modelo Post no existe
            pass
        
        # Calcular estado de sesión
        estado_sesion = 'Inactivo'
        if hasattr(usuario, 'perfil') and usuario.perfil and usuario.perfil.last_activity:
            online_threshold = timezone.now() - timedelta(minutes=5)
            if usuario.perfil.last_activity > online_threshold:
                estado_sesion = 'Activo'
        
        context = {
            'title': f'Usuario: {usuario.username}',
            'usuario': usuario,
            'posts_count': posts_count,
            'posts_publicados': posts_publicados,
            'estado_sesion': estado_sesion,
        }
        return render(request, 'admin/ver_usuario.html', context)
        
    except Exception as e:
        logger.error(f"Error al ver usuario: {e}")
        messages.error(request, 'Error al cargar los detalles del usuario.')
        return redirect('gestionar_usuarios')
