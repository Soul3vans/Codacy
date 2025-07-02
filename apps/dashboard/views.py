from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.contrib import messages
from .models import Archivo, EnlaceInteres
from django.http import JsonResponse

def puede_editar(user):
    """
    Permite acceso a usuarios staff, superusuarios, o moderadores/admins del modelo Perfil.
    """
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    # Comprobación de roles personalizados a través del modelo Perfil
    if hasattr(user, 'perfil'):
        return user.perfil.es_admin or user.perfil.es_moderador
    return False

def inicio(request):
    """
    Vista de la página de inicio.
    Obtiene y muestra los enlaces de interés activos.
    """
    enlaces_interes = EnlaceInteres.objects.filter(
        activo=True
    ).order_by('-es_destacado', 'orden', '-fecha_creacion')[:6]

    context = {
        'enlaces_interes': enlaces_interes,
    }
    return render(request, 'dashboard/index.html', context)

@user_passes_test(puede_editar)
def gestionar_archivos(request):
    """
    Vista para gestionar archivos subidos.
    Permite subir nuevos archivos y muestra una lista de archivos existentes.
    """
    archivos = Archivo.objects.all().order_by('-fecha_subida')

    if request.method == 'POST':
        try:
            # Crear archivo manualmente
            archivo = Archivo(
                nombre=request.POST.get('nombre'),
                archivo=request.FILES.get('archivo'),
                tipo=request.POST.get('tipo'),
                descripcion=request.POST.get('descripcion', ''),
                publico='publico' in request.POST,
                es_formulario='es_formulario' in request.POST,
                subido_por=request.user
            )

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
    """
    Elimina un archivo existente.
    """
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
    """
    Vista para editar un archivo existente.
    """
    archivo = get_object_or_404(Archivo, pk=pk)
    original_es_formulario = archivo.es_formulario

    if request.method == 'POST':
        try:
            # Actualiza el archivo manualmente
            archivo.nombre = request.POST.get('nombre')
            archivo.tipo = request.POST.get('tipo')
            archivo.descripcion = request.POST.get('descripcion', '')
            archivo.publico = 'publico' in request.POST
            nuevo_es_formulario = 'es_formulario' in request.POST
            archivo.es_formulario = nuevo_es_formulario

            updated_fields = ['nombre', 'tipo', 'descripcion', 'publico', 'es_formulario']

            # Actualiza el archivo si se sube uno nuevo
            if 'archivo' in request.FILES:
                archivo.archivo = request.FILES['archivo']
                updated_fields.append('archivo')

            if original_es_formulario != nuevo_es_formulario and 'es_formulario' not in updated_fields:
                updated_fields.append('es_formulario')

            archivo.save(update_fields=updated_fields)
            messages.success(request, 'Archivo actualizado correctamente.')
            return redirect('gestionar_archivos')
        except Exception as e:
            messages.error(request, f'Error al actualizar el archivo: {str(e)}')

    return render(request, 'blog/editar_archivo.html', {'archivo': archivo})

@login_required
def gestionar_enlaces(request):
    """
    Vista para gestionar enlaces de interés.
    Permite crear, editar y eliminar enlaces.
    """
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
    """
    Maneja las operaciones POST para enlaces.
    """
    action = request.POST.get('action')
    if action == 'eliminar':
        return eliminar_enlace(request)
    else:
        return guardar_enlace(request)

def guardar_enlace(request):
    """
    Guarda o actualiza un enlace.
    """
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
            enlace = EnlaceInteres(**datos, creado_por=request.user)
            if 'imagen' in request.FILES:
                enlace.imagen = request.FILES['imagen']
            enlace.save()
            messages.success(request, 'Enlace creado correctamente.')
    except Exception as e:
        messages.error(request, f'Error al guardar el enlace: {str(e)}')

    return redirect('gestionar_enlaces')

def eliminar_enlace(request):
    """
    Elimina un enlace.
    """
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
    """
    Vista AJAX para obtener datos de un enlace para edición.
    """
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
