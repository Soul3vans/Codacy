"""Vistas para las guias"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Count, Q
from .models import GuiaAutocontrol, RespuestaGuia, EvaluacionGuia
from .forms import RespuestaGuiaForm, EvaluacionGuiaForm
from apps.dashboard.models import Archivo
from docx import Document


class GuiaListView(LoginRequiredMixin, ListView):
    """
    Vista para listar todas las guías de autocontrol disponibles
    """
    model = GuiaAutocontrol
    template_name = 'guia/lista_guias.html'
    context_object_name = 'guias'
    paginate_by = 10
    
    def get_queryset(self):
        return GuiaAutocontrol.objects.filter(
            activa=True,
            archivo__es_formulario=True
        ).select_related('archivo')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener evaluaciones del usuario actual
        evaluaciones_usuario = EvaluacionGuia.objects.filter(usuario=self.request.user)
        
        # Cuenta de evaluaciones completadas del usuario actual por guía
        completadas_por_guia = {}
        for guia in context['guias']:
            completadas_por_guia[guia.id] = EvaluacionGuia.objects.filter(
                usuario=self.request.user,
                guia=guia,
                estado='completada'
            ).count()
        
        context.update({
            'completadas_por_guia': completadas_por_guia,
            'evaluaciones_en_progreso': evaluaciones_usuario.filter(estado='en_progreso').count(),
            'evaluaciones_completadas': evaluaciones_usuario.filter(estado='completada').count(),
            'total_evaluaciones_usuario': evaluaciones_usuario.count(),
            'guias_pendientes': context['guias'].count() - evaluaciones_usuario.count(),
        })
        
        return context


@login_required
def detalle_guia(request, pk):
    guia = get_object_or_404(GuiaAutocontrol, pk=pk)

    if request.method == 'POST':
        # Lógica para guardar respuestas y generar reporte
        pass  # Mantén tu lógica actual aquí

    # --- ADAPTACIÓN PARA ESTRUCTURA POR CATEGORÍA/BLOQUES ---
    preguntas_por_categoria = []
    if guia.contenido_procesado and 'tablas_cuestionario' in guia.contenido_procesado:
        respuestas_usuario = RespuestaGuia.objects.filter(
            evaluacion__guia=guia,
            evaluacion__usuario=request.user
        ).values('numero_pregunta', 'respuesta', 'fundamentacion')
        respuestas_dict = {r['numero_pregunta']: {'respuesta': r['respuesta'], 'fundamentacion': r['fundamentacion']} for r in respuestas_usuario}

        for categoria in guia.contenido_procesado['tablas_cuestionario']:
            cat = {
                'categoria': categoria.get('categoria', ''),
                'componente_a_evaluar': categoria.get('componente_a_evaluar', ''),
                'bloques': []
            }
            for bloque in categoria.get('bloques', []):
                blq = {'encabezado': bloque.get('encabezado', ''), 'preguntas': []}
                for pregunta in bloque.get('preguntas', []):
                    num = pregunta.get('numero_pregunta')
                    pregunta = pregunta.copy()
                    if num is not None and num in respuestas_dict:
                        pregunta['user_respuesta'] = respuestas_dict[num]['respuesta']
                        pregunta['user_fundamentacion'] = respuestas_dict[num]['fundamentacion']
                    else:
                        pregunta['user_respuesta'] = None
                        pregunta['user_fundamentacion'] = None
                    blq['preguntas'].append(pregunta)
                cat['bloques'].append(blq)
            preguntas_por_categoria.append(cat)

    # --- ADAPTACIÓN PARA ESTRUCTURA PLANA ---
    preguntas_planas = []
    all_preguntas_flat = []
    if guia.contenido_procesado and 'preguntas' in guia.contenido_procesado:
        for pregunta in guia.contenido_procesado['preguntas']:
            all_preguntas_flat.append(pregunta)
            preguntas_planas.append(pregunta)

    # Obtener respuestas del usuario
    respuestas_usuario = RespuestaGuia.objects.filter(
        evaluacion__guia=guia,
        evaluacion__usuario=request.user
    ).values('numero_pregunta', 'respuesta', 'fundamentacion')
    respuestas_dict = {r['numero_pregunta']: {'respuesta': r['respuesta'], 'fundamentacion': r['fundamentacion']} for r in respuestas_usuario}

    # Asociar respuestas a cada pregunta
    for pregunta in preguntas_planas:
        num = pregunta.get('numero')
        if num is not None and num in respuestas_dict:
            pregunta['user_respuesta'] = respuestas_dict[num]['respuesta']
            pregunta['user_fundamentacion'] = respuestas_dict[num]['fundamentacion']
        else:
            pregunta['user_respuesta'] = None
            pregunta['user_fundamentacion'] = None

    # Calcular progreso
    total_preguntas = len(all_preguntas_flat)
    preguntas_respondidas = sum(1 for p in all_preguntas_flat if p.get('user_respuesta') in ['si', 'no', 'na'])
    porcentaje_completado = round((preguntas_respondidas / total_preguntas * 100)) if total_preguntas > 0 else 0

    evaluacion, created = EvaluacionGuia.objects.get_or_create(
        guia=guia,
        usuario=request.user,
        defaults={'estado': 'en_progreso'}
    )
    if porcentaje_completado == 100:
        evaluacion.estado = 'completada'
    else:
        evaluacion.estado = 'en_progreso'
    evaluacion.porcentaje_cumplimiento = porcentaje_completado
    evaluacion.save()

    context = {
        'guia': guia,
        'preguntas_por_categoria': preguntas_por_categoria if preguntas_por_categoria else None,
        'preguntas_planas': preguntas_planas,
        'evaluacion': evaluacion,
        'total_preguntas': total_preguntas,
        'preguntas_respondidas': preguntas_respondidas,
        'porcentaje_completado': porcentaje_completado,
    }

    return render(request, 'guia/detalle_guia.html', context)


@login_required
def guardar_respuesta(request, guia_pk):
    """
    Vista para guardar una respuesta individual vía AJAX
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    guia = get_object_or_404(GuiaAutocontrol, pk=guia_pk, activa=True)
    
    try:
        numero_pregunta = int(request.POST.get('numero_pregunta'))
        respuesta = request.POST.get('respuesta')
        fundamento = request.POST.get('fundamento', '')
        
        # Validar la respuesta
        if respuesta not in ['si', 'no', 'na']:
            return JsonResponse({'success': False, 'error': 'Respuesta inválida'})
        
        # Guardar o actualizar la respuesta
        respuesta_obj, created = RespuestaGuia.objects.update_or_create(
            guia=guia,
            usuario=request.user,
            numero_pregunta=numero_pregunta,
            defaults={
                'respuesta': respuesta,
                'fundamento': fundamento
            }
        )
        
        # Actualizar el porcentaje de la evaluación
        evaluacion = EvaluacionGuia.objects.get(guia=guia, usuario=request.user)
        porcentaje = evaluacion.calcular_porcentaje_cumplimiento()
        
        return JsonResponse({
            'success': True,
            'message': 'Respuesta guardada correctamente',
            'porcentaje_cumplimiento': porcentaje
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def completar_evaluacion(request, guia_pk):
    """
    Vista para marcar una evaluación como completada
    """
    guia = get_object_or_404(GuiaAutocontrol, pk=guia_pk, activa=True)
    
    try:
        evaluacion = EvaluacionGuia.objects.get(guia=guia, usuario=request.user)
        
        # Verificar que todas las preguntas estén respondidas
        total_preguntas = len(guia.contenido_procesado.get('preguntas', []))
        respuestas_count = RespuestaGuia.objects.filter(
            guia=guia,
            usuario=request.user
        ).count()
        
        if respuestas_count < total_preguntas:
            messages.warning(
                request,
                f'Faltan {total_preguntas - respuestas_count} preguntas por responder.'
            )
            return redirect('guia:detalle', pk=guia_pk)
        
        # Completar la evaluación
        evaluacion.estado = 'completada'
        evaluacion.fecha_completada = timezone.now()
        evaluacion.calcular_porcentaje_cumplimiento()
        
        if request.method == 'POST':
            evaluacion.observaciones_generales = request.POST.get('observaciones_generales', '')
        
        evaluacion.save()
        
        messages.success(request, 'Evaluación completada exitosamente.')
        return redirect('guia:resumen_evaluacion', pk=evaluacion.pk)
        
    except EvaluacionGuia.DoesNotExist:
        messages.error(request, 'No se encontró la evaluación.')
        return redirect('guia:detalle', pk=guia_pk)


@login_required
def resumen_evaluacion(request, pk):
    """
    Vista para mostrar el resumen de una evaluación completada
    """
    evaluacion = get_object_or_404(
        EvaluacionGuia,
        pk=pk,
        usuario=request.user
    )
    
    # Obtener todas las respuestas
    respuestas = RespuestaGuia.objects.filter(
        guia=evaluacion.guia,
        usuario=request.user
    ).order_by('numero_pregunta')
    
    # Estadísticas por categoría
    stats_por_categoria = {}
    for respuesta in respuestas:
        # Buscar la pregunta correspondiente
        pregunta_info = None
        for p in evaluacion.guia.contenido_procesado.get('preguntas', []):
            if p['numero'] == respuesta.numero_pregunta:
                pregunta_info = p
                break
        
        if pregunta_info:
            categoria = pregunta_info.get('categoria', 'General')
            if categoria not in stats_por_categoria:
                stats_por_categoria[categoria] = {'si': 0, 'no': 0, 'na': 0, 'total': 0}
            
            stats_por_categoria[categoria][respuesta.respuesta] += 1
            stats_por_categoria[categoria]['total'] += 1
    
    # Calcular porcentajes por categoría
    for categoria, stats in stats_por_categoria.items():
        if stats['total'] > 0:
            stats['porcentaje_si'] = (stats['si'] / stats['total']) * 100
            stats['porcentaje_no'] = (stats['no'] / stats['total']) * 100
            stats['porcentaje_na'] = (stats['na'] / stats['total']) * 100
    
    context = {
        'evaluacion': evaluacion,
        'respuestas': respuestas,
        'stats_por_categoria': stats_por_categoria,
        'total_si': respuestas.filter(respuesta='si').count(),
        'total_no': respuestas.filter(respuesta='no').count(),
        'total_na': respuestas.filter(respuesta='na').count(),
    }
    
    return render(request, 'guia/resumen_evaluacion.html', context)


@login_required
def mis_evaluaciones(request):
    """
    Vista para mostrar todas las evaluaciones del usuario
    """
    evaluaciones = EvaluacionGuia.objects.filter(
        usuario=request.user
    ).select_related('guia', 'guia__archivo').order_by('-fecha_inicio')
    
    # Calcular estadísticas del usuario
    evaluaciones_completadas = evaluaciones.filter(estado='completada')
    evaluaciones_en_progreso = evaluaciones.filter(estado='en_progreso')
    
    # Estadísticas generales
    total_evaluaciones = evaluaciones.count()
    total_completadas = evaluaciones_completadas.count()
    total_en_progreso = evaluaciones_en_progreso.count()
    
    # Promedio de cumplimiento de evaluaciones completadas
    promedio_cumplimiento = evaluaciones_completadas.aggregate(
        avg_pct=Avg('porcentaje_cumplimiento')
    )['avg_pct'] or 0
    
    # Evaluaciones por estado
    stats_por_estado = {
        'completada': total_completadas,
        'en_progreso': total_en_progreso,
        'pendiente': evaluaciones.filter(estado='pendiente').count() if hasattr(evaluaciones.first(), 'estado') else 0
    }
    
    # Últimas evaluaciones completadas (para mostrar progreso reciente)
    ultimas_completadas = evaluaciones_completadas.order_by('-fecha_completada')[:5]
    
    # Evaluaciones con mejor y peor rendimiento
    mejor_evaluacion = evaluaciones_completadas.order_by('-porcentaje_cumplimiento').first()
    evaluaciones_bajo_rendimiento = evaluaciones_completadas.filter(
        porcentaje_cumplimiento__lt=60
    ).order_by('porcentaje_cumplimiento')
    
    # Paginar resultados
    paginator = Paginator(evaluaciones, 10)
    page = request.GET.get('page')
    evaluaciones_paginadas = paginator.get_page(page)
    
    context = {
        'evaluaciones': evaluaciones_paginadas,
        'total_evaluaciones': total_evaluaciones,
        'total_completadas': total_completadas,
        'total_en_progreso': total_en_progreso,
        'promedio_cumplimiento': round(promedio_cumplimiento, 1),
        'stats_por_estado': stats_por_estado,
        'ultimas_completadas': ultimas_completadas,
        'mejor_evaluacion': mejor_evaluacion,
        'evaluaciones_bajo_rendimiento': evaluaciones_bajo_rendimiento,
        'porcentaje_completadas': round((total_completadas / total_evaluaciones * 100), 1) if total_evaluaciones > 0 else 0,
    }
    
    return render(request, 'guia/mis_evaluaciones.html', context)


@login_required
def procesar_archivo_guia(request, archivo_id):
    """
    Vista para procesar un archivo y crear una GuiaAutocontrol
    """
    archivo = get_object_or_404(Archivo, id=archivo_id, es_formulario=True)
    
    # Verificar si ya existe una guía para este archivo
    guia_existente = GuiaAutocontrol.objects.filter(archivo=archivo).first()
    
    if guia_existente:
        messages.info(request, 'Ya existe una guía para este archivo.')
        return redirect('guia:detalle', pk=guia_existente.pk)
    
    try:
        # Crear nueva guía
        guia = GuiaAutocontrol.objects.create(
            archivo=archivo,
            titulo_guia=archivo.nombre,
            activa=True
        )
        
        # Procesar el contenido del archivo
        guia.extraer_contenido_archivo()
        
        messages.success(request, 'Guía creada y procesada exitosamente.')
        return redirect('guia:detalle', pk=guia.pk)
        
    except Exception as e:
        messages.error(request, f'Error al procesar el archivo: {str(e)}')
        return redirect('guia:lista')


def crear_guias_desde_archivos():
    """
    Función utilitaria para crear guías desde todos los archivos marcados como formulario
    """
    archivos_formulario = Archivo.objects.filter(es_formulario=True)
    
    for archivo in archivos_formulario:
        guia_existente = GuiaAutocontrol.objects.filter(archivo=archivo).first()
        
        if not guia_existente:
            try:
                guia = GuiaAutocontrol.objects.create(
                    archivo=archivo,
                    titulo_guia=archivo.nombre,
                    activa=True
                )
                guia.extraer_contenido_archivo()
                print(f"Guía creada para: {archivo.nombre}")
                
            except Exception as e:
                print(f"Error al crear guía para {archivo.nombre}: {e}")


@login_required
def archivo_guia_view(request):
    archivos = Archivo.objects.all().order_by('-fecha_subida')
    return render(request, 'guia/archivo_guia.html', {'archivos': archivos})
