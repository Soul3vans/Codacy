from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.utils.text import slugify
from .models import Post, Categoria, Comentario, Archivo
from .forms import PostForm, ComentarioForm, ArchivoForm

def puede_editar(user):
    """Permite acceso a usuarios staff, superusuarios, o moderadores/admins de tu modelo Perfil."""
    if not user.is_authenticated:
        return False
    
    # Comprobación de roles de Django (is_staff o is_superuser)
    if user.is_staff or user.is_superuser:
        return True
    
    # Comprobación de roles personalizados a través del modelo Perfil
    # Asegúrate de que el modelo Perfil esté accesible.
    # Si Perfil está en `usuarios.models`, necesitarías importarlo: `from usuarios.models import Perfil`
    if hasattr(user, 'perfil'):
        # Asume que `user.perfil.puede_editar` ya retorna `self.es_admin or self.es_moderador`
        # Si no lo tienes en tu modelo Perfil, puedes hacer la comprobación directa aquí:
        return user.perfil.es_admin or user.perfil.es_moderador
    
    return False # Si no cumple ninguna de las condiciones anteriores


def inicio(request):
    """Página principal del blog"""
    posts_destacados = Post.objects.filter(estado='publicado', destacado=True)[:3]
    posts_recientes = Post.objects.filter(estado='publicado')[:6]
    categorias = Categoria.objects.filter(activa=True)
    
    context = {
        'posts_destacados': posts_destacados,
        'posts_recientes': posts_recientes,
        'categorias': categorias,
    }
    return render(request, 'dashboard/index.html', context)

def lista_posts(request):
    """Lista de todos los posts publicados"""
    posts_list = Post.objects.filter(estado='publicado')
    
    # Filtro por categoría
    categoria_id = request.GET.get('categoria')
    if categoria_id:
        posts_list = posts_list.filter(categoria_id=categoria_id)
    
    # Búsqueda
    query = request.GET.get('q')
    if query:
        posts_list = posts_list.filter(
            Q(titulo__icontains=query) | Q(contenido__icontains=query)
        )
    
    paginator = Paginator(posts_list, 9)
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)
    
    categorias = Categoria.objects.filter(activa=True)
    
    context = {
        'posts': posts,
        'categorias': categorias,
        'query': query,
        'categoria_seleccionada': categoria_id,
    }
    return render(request, 'blog/lista_posts.html', context)

def detalle_post(request, slug):
    """Detalle de un post específico"""
    post = get_object_or_404(Post, slug=slug, estado='publicado')
    
    # Incrementar contador de vistas
    post.vistas += 1
    post.save(update_fields=['vistas'])
    
    # Comentarios
    comentarios = post.comentarios.filter(activo=True)
    
    # Formulario de comentarios para usuarios autenticados
    if request.method == 'POST' and request.user.is_authenticated:
        form = ComentarioForm(request.POST)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.post = post
            comentario.autor = request.user
            comentario.save()
            messages.success(request, 'Comentario agregado correctamente.')
            return redirect('post_detalle', slug=slug)
    else:
        form = ComentarioForm()
    
    # Posts relacionados
    posts_relacionados = Post.objects.filter(
        categoria=post.categoria, 
        estado='publicado'
    ).exclude(id=post.id)[:3]
    
    context = {
        'post': post,
        'comentarios': comentarios,
        'form': form,
        'posts_relacionados': posts_relacionados,
    }
    return render(request, 'blog/detalle_post.html', context)

@user_passes_test(puede_editar)
def gestionar_posts(request):
    """Panel para gestionar posts (solo admin y moderadores)"""
    posts = Post.objects.all()
    
    # Filtrar por estado
    estado = request.GET.get('estado')
    if estado:
        posts = posts.filter(estado=estado)
    
    context = {
        'posts': posts,
        'estado_seleccionado': estado,
    }
    return render(request, 'blog/gestionar_posts.html', context)

@user_passes_test(puede_editar)
def crear_post(request):
    """Crear nuevo post"""
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.autor = request.user
            post.slug = slugify(post.titulo)
            post.save()
            messages.success(request, 'Post creado correctamente.')
            return redirect('gestionar_posts')
    else:
        form = PostForm()
    
    return render(request, 'blog/crear_post.html', {'form': form})

@user_passes_test(puede_editar)
def editar_post(request, post_id):
    """Editar post existente"""
    post = get_object_or_404(Post, id=post_id)
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save()
            messages.success(request, 'Post actualizado correctamente.')
            return redirect('gestionar_posts')
    else:
        form = PostForm(instance=post)
    
    return render(request, 'blog/editar_post.html', {'form': form, 'post': post})

@user_passes_test(puede_editar)
def eliminar_post(request, post_id):
    """Eliminar un post existente"""
    post = get_object_or_404(Post, id=post_id)
    
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Post eliminado correctamente.')
        return redirect('gestionar_posts')
    
    return render(request, 'blog/confirmar_eliminar_post.html', {'post': post})

@user_passes_test(puede_editar)
def gestionar_archivos(request):
    """Gestión de archivos subidos"""
    archivos = Archivo.objects.all().order_by('-fecha_subida')
    
    if request.method == 'POST':
        form = ArchivoForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = form.save(commit=False)
            archivo.subido_por = request.user
            archivo.save()
            messages.success(request, 'Archivo subido correctamente.')
            return redirect('gestionar_archivos')
    else:
        form = ArchivoForm()
    
    context = {
        'archivos': archivos,
        'form': form,
    }
    return render(request, 'blog/gestionar_archivos.html', context)

@user_passes_test(puede_editar)
def eliminar_archivo(request, pk):
    """Eliminar un archivo existente"""
    archivo = get_object_or_404(Archivo, pk=pk)
    
    if request.method == 'POST':
        # Eliminar el archivo físico del sistema de archivos
        if archivo.archivo and archivo.archivo.name:
            try:
                archivo.archivo.delete(save=False)
            except Exception as e:
                messages.error(request, f'Error al eliminar el archivo físico: {str(e)}')
                return redirect('gestionar_archivos')
        
        # Eliminar el registro de la base de datos
        archivo_nombre = archivo.nombre or archivo.archivo.name
        archivo.delete()
        messages.success(request, f'Archivo "{archivo_nombre}" eliminado correctamente.')
        return redirect('gestionar_archivos')
    
    return render(request, 'blog/confirmar_eliminar_archivo.html', {'archivo': archivo})

@user_passes_test(puede_editar)
def editar_archivo(request, pk):
    archivo = get_object_or_404(Archivo, pk=pk)
    if request.method == 'POST':
        form = ArchivoForm(request.POST, request.FILES, instance=archivo)
        if form.is_valid():
            form.save()
            return redirect('gestionar_archivos') # Redirect to your file management page
    else:
        form = ArchivoForm(instance=archivo)
    return render(request, 'your_app_name/editar_archivo.html', {'form': form, 'archivo': archivo})