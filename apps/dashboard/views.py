from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.utils.text import slugify
from .models import Post, Archivo, EnlaceInteres
from .forms import PostForm, ComentarioForm
from django.http import JsonResponse

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
    """Vista de la página de inicio"""
    
    # Obtener publicaciones recientes 
    posts_recientes = Post.objects.filter(
        estado='publicado'  
    ).order_by('-fecha_publicacion')[:6] 
    
    # Obtener enlaces de interés activos
    enlaces_interes = EnlaceInteres.objects.filter(
        activo=True
    ).order_by('-es_destacado', 'orden', '-fecha_creacion')[:6]
    
    context = {
        'posts_recientes': posts_recientes,
        'enlaces_interes': enlaces_interes,
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
    
    
    context = {
        'posts': posts,
        'query': query,
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
        try:
            # Crear archivo manualmente
            archivo = Archivo()
            archivo.nombre = request.POST.get('nombre')
            archivo.archivo = request.FILES.get('archivo')
            archivo.tipo = request.POST.get('tipo')
            archivo.descripcion = request.POST.get('descripcion', '')
            archivo.publico = 'publico' in request.POST
            archivo.es_formulario = 'es_formulario' in request.POST
            archivo.subido_por = request.user
            
            # Validar campos requeridos
            if not archivo.nombre or not archivo.archivo or not archivo.tipo:
                messages.error(request, 'Por favor completa todos los campos obligatorios.')
            else:
                archivo.save()
                messages.success(request, 'Archivo subido correctamente.')
                return redirect('gestionar_archivos')
                
        except Exception as e:
            messages.error(request, f'Error al subir el archivo: {str(e)}')
    
    context = {
        'archivos': archivos,
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

    # Store the original value of es_formulario
    original_es_formulario = archivo.es_formulario

    if request.method == 'POST':
        try:
            # Update archivo manually
            archivo.nombre = request.POST.get('nombre')
            archivo.tipo = request.POST.get('tipo')
            archivo.descripcion = request.POST.get('descripcion', '')
            archivo.publico = 'publico' in request.POST
            # Get the new value for es_formulario
            nuevo_es_formulario = 'es_formulario' in request.POST
            archivo.es_formulario = nuevo_es_formulario

            # List to hold fields that have changed
            updated_fields = ['nombre', 'tipo', 'descripcion', 'publico', 'es_formulario']

            # Only update the file if a new one was uploaded
            if 'archivo' in request.FILES:
                archivo.archivo = request.FILES['archivo']
                updated_fields.append('archivo') # Add 'archivo' to updated_fields if changed

            # If es_formulario state has changed, ensure it's in update_fields
            if original_es_formulario != nuevo_es_formulario:
                if 'es_formulario' not in updated_fields:
                    updated_fields.append('es_formulario')

            # Save the instance with specific updated fields
            # This ensures `update_fields` is properly populated for the signal
            archivo.save(update_fields=updated_fields) # Pass the list of updated fields

            messages.success(request, 'Archivo actualizado correctamente.')
            return redirect('gestionar_archivos')
        except Exception as e:
            messages.error(request, f'Error al actualizar el archivo: {str(e)}')

    return render(request, 'blog/editar_archivo.html', {'archivo': archivo})

@login_required
def gestionar_enlaces(request):
    """Vista para gestionar enlaces de interés"""
    
    # Verificar permisos
    if not hasattr(request.user, 'perfil') or not request.user.perfil.puede_editar:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('inicio')
    
    if request.method == 'POST':
        return manejar_enlace_post(request)
    
    # Obtener enlaces con paginación
    enlaces_list = EnlaceInteres.objects.all().order_by('-fecha_creacion')
    paginator = Paginator(enlaces_list, 10)  # 10 enlaces por página
    page_number = request.GET.get('page')
    enlaces = paginator.get_page(page_number)
    
    context = {
        'enlaces': enlaces,
    }
    
    return render(request, 'blog/gestionar_enlaces.html', context)

def manejar_enlace_post(request):
    """Maneja las operaciones POST para enlaces"""
    
    action = request.POST.get('action')
    
    if action == 'eliminar':
        return eliminar_enlace(request)
    else:
        return guardar_enlace(request)

def guardar_enlace(request):
    """Guarda o actualiza un enlace"""
    try:
        enlace_id = request.POST.get('enlace_id')
        
        # Datos del formulario
        datos = {
            'titulo': request.POST.get('titulo'),
            'url': request.POST.get('url'),
            'descripcion': request.POST.get('descripcion', ''),
            'categoria': request.POST.get('categoria', ''),
            'activo': 'activo' in request.POST,
            'es_destacado': 'es_destacado' in request.POST,
        }
        
        if enlace_id:
            # Actualizar enlace existente
            enlace = get_object_or_404(EnlaceInteres, id=enlace_id)
            for key, value in datos.items():
                setattr(enlace, key, value)
            
            # Manejar imagen si se subió una nueva
            if 'imagen' in request.FILES:
                enlace.imagen = request.FILES['imagen']
                
            enlace.save()
            messages.success(request, 'Enlace actualizado correctamente.')
        else:
            # Crear nuevo enlace
            enlace = EnlaceInteres(**datos)
            enlace.creado_por = request.user
            
            # Manejar imagen
            if 'imagen' in request.FILES:
                enlace.imagen = request.FILES['imagen']
                
            enlace.save()
            messages.success(request, 'Enlace creado correctamente.')
            
    except Exception as e:
        messages.error(request, f'Error al guardar el enlace: {str(e)}')
    
    return redirect('gestionar_enlaces')

def eliminar_enlace(request):
    """Elimina un enlace"""
    try:
        enlace_id = request.POST.get('enlace_id')
        enlace = get_object_or_404(EnlaceInteres, id=enlace_id)
        titulo = enlace.titulo
        enlace.delete()
        messages.success(request, f'Enlace "{titulo}" eliminado correctamente.')
    except Exception as e:
        messages.error(request, f'Error al eliminar el enlace: {str(e)}')
    
    return redirect('gestionar_enlaces')

@login_required
def obtener_enlace_ajax(request, enlace_id):
    """Vista AJAX para obtener datos de un enlace para edición"""
    try:
        enlace = get_object_or_404(EnlaceInteres, id=enlace_id)
        data = {
            'id': enlace.id,
            'titulo': enlace.titulo,
            'url': enlace.url,
            'descripcion': enlace.descripcion,
            'categoria': enlace.categoria,
            'activo': enlace.activo,
            'es_destacado': enlace.es_destacado,
            'imagen_url': enlace.imagen.url if enlace.imagen else None,
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)