# VISTAS DE ADMINISTRACIÓN
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import logout as auth_logout, login, authenticate, update_session_auth_hash
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
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
from .models import Post, Archivo, Perfil
from .forms import PostForm, ArchivoForm, PerfilForm, ActualizarPerfilForm
import json
import logging

logger = logging.getLogger(__name__)

def home(request):
    return render(request, 'dashboard/index.html')

# VISTA DE PERFIL CORREGIDA - ELIMINAR DUPLICADOS
@login_required
def perfil(request):
    """Vista para mostrar el perfil del usuario actual"""
    try:
        # Asegurarse de que existe el perfil
        if not hasattr(request.user, 'perfil'):
            Perfil.objects.create(user=request.user)
        
        # Obtener estadísticas del usuario
        posts_count = 0
        posts_publicados = 0
        
        if hasattr(request.user, 'post_set'):
            posts_count = request.user.post_set.count()
            posts_publicados = request.user.post_set.filter(publicado=True).count()
        
        context = {
            'user': request.user,
            'posts_count': posts_count,
            'posts_publicados': posts_publicados,
            'perfil': request.user.perfil,
        }
        
        return render(request, 'usuarios/perfil.html', context)
        
    except Exception as e:
        logger.error(f"Error al cargar perfil de usuario {request.user.username}: {e}")
        messages.error(request, 'Error al cargar el perfil. Por favor, intenta nuevamente.')
        return redirect('home')  # Cambiar 'inicio' por 'home' si es necesario

@login_required
def actualizar_perfil(request):
    """Vista para actualizar la información del perfil del usuario"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                user = request.user
                
                # Obtener datos del formulario
                first_name = request.POST.get('first_name', '').strip()
                last_name = request.POST.get('last_name', '').strip()
                email = request.POST.get('email', '').strip()
                
                # Validaciones básicas
                if not first_name:
                    messages.error(request, 'El nombre es obligatorio.')
                    return redirect('perfil')
                
                if not last_name:
                    messages.error(request, 'Los apellidos son obligatorios.')
                    return redirect('perfil')
                
                if not email:
                    messages.error(request, 'El correo electrónico es obligatorio.')
                    return redirect('perfil')
                
                # Validar formato de email
                from django.core.validators import validate_email
                try:
                    validate_email(email)
                except ValidationError:
                    messages.error(request, 'Por favor ingresa un correo electrónico válido.')
                    return redirect('perfil')
                
                # Validar que el email no esté en uso por otro usuario
                if User.objects.filter(email=email).exclude(id=user.id).exists():
                    messages.error(request, 'Este correo electrónico ya está en uso por otro usuario.')
                    return redirect('perfil')
                
                # Validar longitud de campos
                if len(first_name) > 30:
                    messages.error(request, 'El nombre no puede tener más de 30 caracteres.')
                    return redirect('perfil')
                
                if len(last_name) > 30:
                    messages.error(request, 'Los apellidos no pueden tener más de 30 caracteres.')
                    return redirect('perfil')
                
                # Actualizar información del usuario
                user.first_name = first_name
                user.last_name = last_name
                user.email = email
                user.save()
                
                # Asegurarse de que existe el perfil
                if not hasattr(user, 'perfil'):
                    Perfil.objects.create(user=user)
                
                logger.info(f"Perfil actualizado para usuario {user.username}")
                messages.success(request, 'Tu perfil ha sido actualizado correctamente.')
                
        except ValidationError as e:
            logger.error(f"Error de validación al actualizar perfil: {e}")
            messages.error(request, f'Error de validación: {e}')
        except Exception as e:
            logger.error(f"Error al actualizar perfil de {request.user.username}: {e}")
            messages.error(request, 'Error al actualizar el perfil. Por favor, intenta nuevamente.')
    
    return redirect('perfil')

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
    return (user.is_authenticated and 
            hasattr(user, 'perfil') and 
            user.perfil.es_admin)

def puede_editar(user):
    """Verifica si el usuario puede editar contenido"""
    return (user.is_authenticated and 
            hasattr(user, 'perfil') and 
            user.perfil.puede_editar)

def es_moderador_o_admin(user):
    """Verifica si el usuario es moderador o admin"""
    return (user.is_authenticated and 
            hasattr(user, 'perfil') and 
            (user.perfil.es_moderador or user.perfil.es_admin))

# FORMULARIO PERSONALIZADO DE REGISTRO
class RegistroForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True, label='Nombre')
    last_name = forms.CharField(max_length=30, required=True, label='Apellidos')

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizar los widgets y clases CSS
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            
        # Personalizar labels y help texts
        self.fields['username'].help_text = 'Requerido. 150 caracteres o menos. Solo letras, dígitos y @/./+/-/_'
        self.fields['password1'].help_text = 'Tu contraseña debe tener al menos 8 caracteres.'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
            # Crear perfil automáticamente
            Perfil.objects.get_or_create(user=user)
        return user

def login_view(request):
    """Vista personalizada para login"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    logger.info(f"Usuario {username} inició sesión correctamente")
                    messages.success(request, f'¡Bienvenido {user.first_name or user.username}!')
                    
                    # Redirigir a la página solicitada o al home
                    next_page = request.GET.get('next', 'home')
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
    return redirect('home')

def registro(request):
    """Vista para registro de nuevos usuarios"""
    if request.method == 'POST':
        try:
            form = RegistroForm(request.POST)
            if form.is_valid():
                with transaction.atomic():
                    # Crear el usuario
                    user = form.save()
                    
                    # Autenticar y hacer login automáticamente
                    username = form.cleaned_data.get('username')
                    password = form.cleaned_data.get('password1')
                    user = authenticate(username=username, password=password)
                    
                    if user is not None:
                        login(request, user)
                        logger.info(f"Usuario {username} registrado y autenticado correctamente")
                        messages.success(request, f'¡Bienvenido {user.first_name}! Tu cuenta ha sido creada exitosamente.')
                        return redirect('home')  # Redirigir al inicio después del registro
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
        total_posts = Post.objects.count() if 'Post' in globals() else 0
        posts_publicados = Post.objects.filter(publicado=True).count() if 'Post' in globals() else 0
        
        # Obtener todos los usuarios con sus perfiles para la tabla
        usuarios = User.objects.select_related('perfil').order_by('-date_joined')
        
        # Contar usuarios por rol
        administradores_count = User.objects.filter(perfil__es_admin=True).count()
        moderadores_count = User.objects.filter(perfil__es_moderador=True).count()
        usuarios_activos_count = User.objects.filter(is_active=True).count()
        
        # Usuarios recientes (últimos 10)
        usuarios_recientes = User.objects.select_related('perfil').order_by('-date_joined')[:10]
        
        # Posts recientes si existen
        posts_recientes = []
        if 'Post' in globals():
            posts_recientes = Post.objects.select_related('usuario').order_by('-fecha_creacion')[:10]
        
        # Actividad reciente simulada (puedes implementar un modelo de log más tarde)
        actividad_reciente = []
        # Ejemplo de actividad reciente basada en usuarios nuevos
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
            'usuarios': usuarios,  # Para la tabla principal
            'administradores_count': administradores_count,
            'moderadores_count': moderadores_count,
            'usuarios_activos_count': usuarios_activos_count,
            'actividad_reciente': actividad_reciente,
        }
        
        return render(request, 'usuarios/admin_panel.html', context)
        
    except Exception as e:
        logger.error(f"Error en panel admin: {e}")
        messages.error(request, 'Error al cargar el panel de administración.')
        return redirect('home')

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
def debug_user_info(request, user_id):
    """Ver detalles de un usuario específico"""
    try:
        usuario = get_object_or_404(User, id=user_id)
        
        # Estadísticas del usuario
        posts_count = 0
        posts_publicados = 0
        
        if 'Post' in globals():
            posts_count = Post.objects.filter(usuario=usuario).count()
            posts_publicados = Post.objects.filter(usuario=usuario, publicado=True).count()
        
        context = {
            'title': f'Usuario: {usuario.username}',
            'usuario': usuario,
            'posts_count': posts_count,
            'posts_publicados': posts_publicados,
        }
        
        return render(request, 'admin/ver_usuario.html', context)
        
    except Exception as e:
        logger.error(f"Error al ver usuario: {e}")
        messages.error(request, 'Error al cargar los detalles del usuario.')
        return redirect('gestionar_usuarios')

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
        
        # **Añadir estado de sesión en tiempo real**
        # Define un estado para "online"
        online_threshold_minutes = 5 # <--- Adjust this as needed for testing
        online_threshold = timezone.now() - timedelta(minutes=online_threshold_minutes)
        logger.info(f"View: Online threshold set to: {online_threshold}")

        for user in usuarios:
            # Ensure user has a profile and last_activity
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
def eliminar_usuario(request, user_id):
    usuario = get_object_or_404(User, id=user_id)
    if usuario == request.user:
        messages.error(request, "No puedes eliminar tu propia cuenta.")
    else:
        usuario.delete()
        messages.success(request, f'Usuario {usuario.username} eliminado correctamente.')
    return redirect('panel_admin')  # Ajusta el nombre de la URL del panel admin

@login_required
@user_passes_test(es_admin)
def debug_user_info(request, user_id):
    """Ver detalles de un usuario específico"""
    try:
        usuario = get_object_or_404(User, id=user_id)
        
        # Estadísticas del usuario
        posts_count = 0
        posts_publicados = 0
        
        if 'Post' in globals():
            posts_count = Post.objects.filter(usuario=usuario).count()
            posts_publicados = Post.objects.filter(usuario=usuario, publicado=True).count()
        
        context = {
            'title': f'Usuario: {usuario.username}',
            'usuario': usuario,
            'posts_count': posts_count,
            'posts_publicados': posts_publicados,
        }
        
        return render(request, 'admin/ver_usuario.html', context)
        
    except Exception as e:
        logger.error(f"Error al ver usuario: {e}")
        messages.error(request, 'Error al cargar los detalles del usuario.')
        return redirect('gestionar_usuarios')