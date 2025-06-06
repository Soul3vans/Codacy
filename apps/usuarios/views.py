from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import logout as auth_logout
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.db.models import Q, Count
from django.utils import timezone
from .models import Post, Archivo, Perfil
from .forms import PostForm, ArchivoForm, PerfilForm
import json

# Decoradores para verificar permisos
def es_admin(user):
    """Verifica si el usuario es administrador"""
    return user.is_authenticated and hasattr(user, 'perfil') and user.perfil.es_admin

def puede_editar(user):
    """Verifica si el usuario puede editar contenido"""
    return user.is_authenticated and hasattr(user, 'perfil') and user.perfil.puede_editar

def es_moderador_o_admin(user):
    """Verifica si el usuario es moderador o admin"""
    return user.is_authenticated and hasattr(user, 'perfil') and (user.perfil.es_moderador or user.perfil.es_admin)

@login_required
def perfil_view(request):
    """Vista para mostrar el perfil del usuario"""
    try:
        perfil = request.user.perfil
    except:
        # Si no existe perfil, crear uno básico
        perfil = Perfil.objects.create(user=request.user)
    
    # Estadísticas del usuario
    total_posts = Post.objects.filter(autor=request.user).count()
    posts_publicados = Post.objects.filter(autor=request.user, publicado=True).count()
    
    context = {
        'perfil': perfil,
        'total_posts': total_posts,
        'posts_publicados': posts_publicados,
    }
    return render(request, 'perfil.html', context)

@login_required
def editar_perfil_view(request):
    """Vista para editar el perfil del usuario"""
    try:
        perfil = request.user.perfil
    except:
        perfil = Perfil.objects.create(user=request.user)
    
    if request.method == 'POST':
        form = PerfilForm(request.POST, request.FILES, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('perfil')
    else:
        form = PerfilForm(instance=perfil)
    
    return render(request, 'editar_perfil.html', {'form': form})

@login_required
@user_passes_test(puede_editar)
def gestionar_posts_view(request):
    """Vista para gestionar posts del usuario"""
    posts = Post.objects.filter(autor=request.user).order_by('-fecha_creacion')
    
    # Paginación
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    posts_paginados = paginator.get_page(page_number)
    
    context = {
        'posts': posts_paginados,
        'total_posts': posts.count(),
    }
    return render(request, 'gestionar_posts.html', context)

@login_required
@user_passes_test(puede_editar)
def crear_post_view(request):
    """Vista para crear un nuevo post"""
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.autor = request.user
            post.fecha_creacion = timezone.now()
            post.save()
            
            messages.success(request, 'Post creado correctamente.')
            
            if post.publicado:
                messages.info(request, 'El post ha sido publicado.')
            else:
                messages.info(request, 'El post se ha guardado como borrador.')
            
            return redirect('gestionar_posts')
    else:
        form = PostForm()
    
    return render(request, 'crear_post.html', {'form': form})

@login_required
@user_passes_test(puede_editar)
def editar_post_view(request, post_id):
    """Vista para editar un post existente"""
    post = get_object_or_404(Post, id=post_id, autor=request.user)
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save()
            messages.success(request, 'Post actualizado correctamente.')
            return redirect('gestionar_posts')
    else:
        form = PostForm(instance=post)
    
    return render(request, 'editar_post.html', {'form': form, 'post': post})

@login_required
@user_passes_test(puede_editar)
def eliminar_post_view(request, post_id):
    """Vista para eliminar un post"""
    post = get_object_or_404(Post, id=post_id, autor=request.user)
    
    if request.method == 'POST':
        titulo = post.titulo
        post.delete()
        messages.success(request, f'Post "{titulo}" eliminado correctamente.')
        return redirect('gestionar_posts')
    
    return render(request, 'confirmar_eliminar_post.html', {'post': post})

@login_required
@user_passes_test(puede_editar)
def gestionar_archivos_view(request):
    """Vista para gestionar archivos del usuario"""
    if request.method == 'POST':
        form = ArchivoForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = form.save(commit=False)
            archivo.usuario = request.user
            archivo.fecha_subida = timezone.now()
            archivo.save()
            messages.success(request, 'Archivo subido correctamente.')
            return redirect('gestionar_archivos')
    else:
        form = ArchivoForm()
    
    archivos = Archivo.objects.filter(usuario=request.user).order_by('-fecha_subida')
    
    # Paginación
    paginator = Paginator(archivos, 12)
    page_number = request.GET.get('page')
    archivos_paginados = paginator.get_page(page_number)
    
    context = {
        'archivos': archivos_paginados,
        'form': form,
        'total_archivos': archivos.count(),
    }
    return render(request, 'gestionar_archivos.html', context)

@login_required
@user_passes_test(puede_editar)
def eliminar_archivo_view(request, archivo_id):
    """Vista para eliminar un archivo (AJAX)"""
    if request.method == 'POST':
        archivo = get_object_or_404(Archivo, id=archivo_id, usuario=request.user)
        nombre = archivo.nombre
        archivo.delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Archivo "{nombre}" eliminado correctamente.'
            })
        else:
            messages.success(request, f'Archivo "{nombre}" eliminado correctamente.')
            return redirect('gestionar_archivos')
    
    return JsonResponse({'success': False, 'message': 'Método no permitido.'})

@login_required
@user_passes_test(es_admin)
def panel_admin_view(request):
    """Vista del panel de administración"""
    # Estadísticas generales
    total_usuarios = User.objects.count()
    usuarios_activos = User.objects.filter(is_active=True).count()
    total_posts = Post.objects.count()
    posts_publicados = Post.objects.filter(publicado=True).count()
    total_archivos = Archivo.objects.count()
    
    # Contar roles
    moderadores = User.objects.filter(perfil__es_moderador=True).count()
    administradores = User.objects.filter(perfil__es_admin=True).count()
    
    # Usuarios recientes
    usuarios_recientes = User.objects.select_related('perfil').order_by('-date_joined')[:10]
    
    # Posts recientes
    posts_recientes = Post.objects.select_related('autor').order_by('-fecha_creacion')[:5]
    
    # Búsqueda de usuarios
    buscar = request.GET.get('buscar', '')
    usuarios = User.objects.select_related('perfil').all()
    
    if buscar:
        usuarios = usuarios.filter(
            Q(username__icontains=buscar) | 
            Q(email__icontains=buscar) |
            Q(first_name__icontains=buscar) |
            Q(last_name__icontains=buscar)
        )
    
    usuarios = usuarios.order_by('-date_joined')
    
    # Paginación de usuarios
    paginator = Paginator(usuarios, 15)
    page_number = request.GET.get('page')
    usuarios_paginados = paginator.get_page(page_number)
    
    context = {
        'total_usuarios': total_usuarios,
        'usuarios_activos': usuarios_activos,
        'total_posts': total_posts,
        'posts_publicados': posts_publicados,
        'total_archivos': total_archivos,
        'moderadores': moderadores,
        'administradores': administradores,
        'usuarios': usuarios_paginados,
        'usuarios_recientes': usuarios_recientes,
        'posts_recientes': posts_recientes,
        'buscar': buscar,
    }
    return render(request, 'panel_admin.html', context)

@login_required
@user_passes_test(es_admin)
def cambiar_rol_usuario_view(request, user_id):
    """Vista para cambiar el rol de un usuario (AJAX)"""
    if request.method == 'POST':
        usuario = get_object_or_404(User, id=user_id)
        data = json.loads(request.body)
        nuevo_rol = data.get('rol')
        
        try:
            perfil = usuario.perfil
        except:
            perfil = Perfil.objects.create(user=usuario)
        
        # Resetear roles
        perfil.es_admin = False
        perfil.es_moderador = False
        
        # Asignar nuevo rol
        if nuevo_rol == 'admin':
            perfil.es_admin = True
            perfil.es_moderador = True  # Los admins también son moderadores
        elif nuevo_rol == 'moderador':
            perfil.es_moderador = True
        
        perfil.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Rol de {usuario.username} actualizado correctamente.'
        })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido.'})

@login_required
@user_passes_test(es_admin)
def cambiar_estado_usuario_view(request, user_id):
    """Vista para activar/desactivar un usuario (AJAX)"""
    if request.method == 'POST':
        usuario = get_object_or_404(User, id=user_id)
        
        # No permitir desactivar al propio admin
        if usuario == request.user:
            return JsonResponse({
                'success': False,
                'message': 'No puedes desactivar tu propia cuenta.'
            })
        
        usuario.is_active = not usuario.is_active
        usuario.save()
        
        estado = 'activado' if usuario.is_active else 'desactivado'
        
        return JsonResponse({
            'success': True,
            'message': f'Usuario {usuario.username} {estado} correctamente.',
            'nuevo_estado': usuario.is_active
        })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido.'})

def logout_view(request):
    """Vista para cerrar sesión"""
    if request.method == 'POST':
        username = request.user.username if request.user.is_authenticated else 'Usuario'
        auth_logout(request)
        messages.success(request, f'Sesión cerrada correctamente. ¡Hasta pronto, {username}!')
        return redirect('home')
    
    return render(request, 'logout.html')

# Vista adicional para el home (en caso de que no exista)
def home_view(request):
    """Vista principal del sitio"""
    posts_recientes = Post.objects.filter(publicado=True).order_by('-fecha_creacion')[:6]
    total_posts = Post.objects.filter(publicado=True).count()
    total_usuarios = User.objects.filter(is_active=True).count()
    
    context = {
        'posts_recientes': posts_recientes,
        'total_posts': total_posts,
        'total_usuarios': total_usuarios,
    }
    return render(request, 'home.html', context)