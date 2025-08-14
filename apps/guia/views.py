"Views para las guias"
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from .models import GuiaAutocontrol, RespuestaGuia, EvaluacionGuia
from apps.dashboard.models import Archivo
from .tasks import generar_pdf_guia_async
import io
import json
import logging
import os
from django.conf import settings

logger = logging.getLogger(__name__)
User = get_user_model()

class GuiaListView(LoginRequiredMixin, ListView):
    """
    Vista para listar todas las guías de autocontrol disponibles.
    """
    model = GuiaAutocontrol
    template_name = 'guia/lista_guias.html'
    context_object_name = 'guias'
    paginate_by = 10

    def get_queryset(self):
        return GuiaAutocontrol.objects.filter(
            activa=True,
            archivo__es_formulario=True
        ).select_related('archivo').prefetch_related('evaluaciones')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        guias = list(context['guias'])
        usuario = self.request.user
        # Obtener todas las evaluaciones del usuario de una sola vez
        evaluaciones_usuario = EvaluacionGuia.objects.filter(
            usuario=usuario,
            guia__in=guias
        ).select_related('guia')
        # Crear un diccionario para acceso rápido
        evaluaciones_por_guia = {e.guia_id: e for e in evaluaciones_usuario}
         # Asignar las evaluaciones a cada guía
        for guia in guias:
            guia.evaluacion_usuario = evaluaciones_por_guia.get(guia.id)
            
        # Ordenar: primero no completadas, luego completadas
        def is_completed(guia):
            ev = evaluaciones_por_guia.get(guia.id)
            return 1 if ev and ev.estado == 'completada' else 0
        guias.sort(key=is_completed)
        # Guías completadas: aquellas con evaluación en estado 'completada'
        guias_completadas = [guia for guia in guias if evaluaciones_por_guia.get(guia.id) and evaluaciones_por_guia[guia.id].estado == 'completada']
        # Guías en progreso: evaluación en 'en_progreso'
        guias_en_progreso = [guia for guia in guias if evaluaciones_por_guia.get(guia.id) and evaluaciones_por_guia[guia.id].estado == 'en_progreso']
        # Guías pendientes: aquellas sin evaluación o con estado 'no_iniciada'
        guias_pendientes = [guia for guia in guias if not evaluaciones_por_guia.get(guia.id) or evaluaciones_por_guia[guia.id].estado == 'no_iniciada']

        context.update({
            'guias': guias,
            'guias_completadas': guias_completadas,
            'guias_en_progreso': guias_en_progreso,
            'guias_pendientes': guias_pendientes,
            'total_guias': len(guias),
            'total_completadas': len(guias_completadas),
            'total_en_progreso': len(guias_en_progreso),
            'total_pendientes': len(guias_pendientes),
        })
        return context

@login_required
def detalle_guia(request, pk):
    guia = get_object_or_404(GuiaAutocontrol, pk=pk)

    if request.method == 'POST':
        # --- Lógica para guardar respuestas vía AJAX ---
        try:
            # Intentar cargar los datos JSON del cuerpo de la solicitud
            data = json.loads(request.body)
            numero_pregunta = data.get('numero_pregunta')
            respuesta = data.get('respuesta')
            fundamentacion = data.get('fundamentacion', '')
            
            # Validaciones básicas
            if numero_pregunta is None:
                return JsonResponse({'status': 'error', 'message': 'Número de pregunta es requerido.'}, status=400)

            # Obtener o crear la EvaluaciónGuia para el usuario y la guía actual
            evaluacion, created = EvaluacionGuia.objects.get_or_create(
                guia=guia,
                usuario=request.user,
                defaults={'estado': 'en_progreso'}
            )
            # Guardar o actualizar en RespuestaGuia
            respuesta_guia, created = RespuestaGuia.objects.update_or_create(
                guia=guia,
                usuario=request.user,
                numero_pregunta=numero_pregunta,
                defaults={
                    'respuesta': respuesta if respuesta else None,
                    'fundamentacion': fundamentacion
                }
            )
            # Recalcular el progreso y actualizar la evaluación después de guardar la respuesta
            all_preguntas_flat = []
            if guia.contenido_procesado and 'tablas_cuestionario' in guia.contenido_procesado:
                for categoria in guia.contenido_procesado['tablas_cuestionario']:
                    for bloque in categoria.get('bloques', []):
                        for pregunta in bloque.get('preguntas', []):
                            all_preguntas_flat.append(pregunta)
            respuestas_usuario_actualizadas = RespuestaGuia.objects.filter(
                guia=guia,
                usuario=request.user
            ).values('numero_pregunta', 'respuesta')
            respuestas_dict_actualizadas = {r['numero_pregunta']: r for r in respuestas_usuario_actualizadas}
            total_preguntas = len(all_preguntas_flat)
            preguntas_respondidas = sum(1 for p in all_preguntas_flat if respuestas_dict_actualizadas.get(p.get('numero_pregunta'), {}).get('respuesta') in ['si', 'no', 'na'])
            porcentaje_completado = round((preguntas_respondidas / total_preguntas * 100)) if total_preguntas > 0 else 0
            evaluacion.estado = 'completada' if porcentaje_completado == 100 else 'en_progreso'
            evaluacion.porcentaje_cumplimiento = porcentaje_completado
            evaluacion.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Respuesta guardada exitosamente.',
                'porcentaje_completado': porcentaje_completado,
                'preguntas_respondidas': preguntas_respondidas,
                'total_preguntas': total_preguntas
            })
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Formato JSON inválido.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error al guardar la respuesta: {str(e)}'}, status=500)

    # --- Lógica GET (existente) para mostrar la guía ---
    preguntas_por_categoria = []
    all_preguntas_flat = []
    if guia.contenido_procesado and 'tablas_cuestionario' in guia.contenido_procesado:
        respuestas_usuario = RespuestaGuia.objects.filter(
            guia=guia,
            usuario=request.user
        ).values('numero_pregunta', 'respuesta', 'fundamentacion')
        # Forzar a string para el mapeo correcto
        respuestas_dict = {str(r['numero_pregunta']): r for r in respuestas_usuario}
        # Recorre las categorías y bloques para armar la estructura de preguntas y respuestas del usuario
        for categoria in guia.contenido_procesado['tablas_cuestionario']:
            cat = {
                'categoria': categoria.get('categoria', ''),
                'componente_a_evaluar': categoria.get('componente_a_evaluar', ''),
                'bloques': []
            }
            for bloque in categoria.get('bloques', []):
                blq = {'encabezado': bloque.get('encabezado', ''), 'preguntas': []}
                for pregunta in bloque.get('preguntas', []):
                    num = str(pregunta.get('numero_pregunta'))  # Forzar a string para coincidir con el diccionario
                    pregunta_copy = pregunta.copy()
                    # Si el usuario ya respondió esta pregunta, agrega la respuesta y fundamentación
                    if num is not None and num in respuestas_dict:
                        pregunta_copy.update({
                            'user_respuesta': respuestas_dict[num]['respuesta'],
                            'user_fundamentacion': respuestas_dict[num]['fundamentacion']
                        })
                    else:
                        # Si no hay respuesta, deja los campos en None
                        pregunta_copy.update({
                            'user_respuesta': None,
                            'user_fundamentacion': None
                        })
                    blq['preguntas'].append(pregunta_copy)
                    all_preguntas_flat.append(pregunta_copy)
                cat['bloques'].append(blq)
            preguntas_por_categoria.append(cat)

    total_preguntas = len(all_preguntas_flat)
    preguntas_respondidas = sum(1 for p in all_preguntas_flat if p.get('user_respuesta') in ['si', 'no', 'na'])
    porcentaje_completado = round((preguntas_respondidas / total_preguntas * 100)) if total_preguntas > 0 else 0
    evaluacion, created = EvaluacionGuia.objects.get_or_create(
        guia=guia,
        usuario=request.user,
        defaults={'estado': 'en_progreso'}
    )
    evaluacion.estado = 'completada' if porcentaje_completado == 100 else 'en_progreso'
    evaluacion.porcentaje_cumplimiento = porcentaje_completado
    evaluacion.save()
    context = {
        'guia': guia,
        'preguntas_por_categoria': preguntas_por_categoria if preguntas_por_categoria else None,
        'preguntas_planas': all_preguntas_flat,
        'evaluacion': evaluacion,
        'total_preguntas': total_preguntas,
        'preguntas_respondidas': preguntas_respondidas,
        'porcentaje_completado': porcentaje_completado,
    }
    return render(request, 'guia/detalle_guia.html', context)

@login_required
@transaction.atomic
def guardar_respuesta(request, guia_pk):
    # Solo permite método POST
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

    try:
        # Carga el JSON recibido y obtiene la guía y el usuario
        data = json.loads(request.body)
        guia = get_object_or_404(GuiaAutocontrol, pk=guia_pk, activa=True)
        usuario = request.user

        # Permite recibir una lista de respuestas o una sola
        responses_to_process = data if isinstance(data, list) else [data]

        # Guarda o actualiza cada respuesta recibida
        for item in responses_to_process:
            numero_pregunta = item.get('numero_pregunta')
            respuesta = item.get('respuesta')
            fundamentacion = item.get('fundamentacion', '')

            RespuestaGuia.objects.update_or_create(
                guia=guia,
                usuario=usuario,
                numero_pregunta=numero_pregunta,
                defaults={
                    'respuesta': respuesta,
                    'fundamentacion': fundamentacion
                }
            )

        # Obtiene o crea la evaluación del usuario para la guía
        evaluacion, _ = EvaluacionGuia.objects.get_or_create(
            guia=guia,
            usuario=usuario,
            defaults={'estado': 'en_progreso'}
        )
        # Calcula el total de preguntas y cuántas ha respondido el usuario
        total_preguntas = guia.total_preguntas
        respuestas_usuario = RespuestaGuia.objects.filter(
            guia=guia,
            usuario=usuario,
            respuesta__in=['si', 'no', 'na']
        ).count()
        porcentaje_completado = round((respuestas_usuario / total_preguntas * 100)) if total_preguntas else 0

        # Actualiza el estado y porcentaje de la evaluación
        evaluacion.estado = 'completada' if porcentaje_completado == 100 else 'en_progreso'
        evaluacion.porcentaje_cumplimiento = porcentaje_completado
        evaluacion.save()
        # Actualiza campos denormalizados y estadísticas
        evaluacion.actualizar_estadisticas()

        # Devuelve respuesta JSON con el progreso actualizado
        return JsonResponse({
            'status': 'success',
            'message': 'Respuestas guardadas correctamente.',
            'porcentaje_completado': porcentaje_completado,
            'preguntas_respondidas': respuestas_usuario,
            'total_preguntas': total_preguntas
        })

    except Exception as e:
        # Loguea y responde con error si algo falla
        logger.error(f"Error en guardar_respuesta: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Error al guardar la respuesta: {str(e)}'}, status=500)

@login_required
def completar_evaluacion(request, guia_pk):
    guia = get_object_or_404(GuiaAutocontrol, pk=guia_pk, activa=True)
    try:
        evaluacion = EvaluacionGuia.objects.get(guia=guia, usuario=request.user)
        # Acceder a todas las preguntas de la guía para el conteo total
        all_preguntas_from_guia = []
        if guia.contenido_procesado and 'tablas_cuestionario' in guia.contenido_procesado:
            for categoria in guia.contenido_procesado['tablas_cuestionario']:
                for bloque in categoria.get('bloques', []):
                    for pregunta in bloque.get('preguntas', []):
                        all_preguntas_from_guia.append(pregunta)
        total_preguntas = len(all_preguntas_from_guia)

        # Filtrar RespuestaGuia por guia y usuario
        respuestas_count = RespuestaGuia.objects.filter(guia=guia, usuario=request.user).count()

        if respuestas_count < total_preguntas:
            messages.warning(request, f'Faltan {total_preguntas - respuestas_count} preguntas por responder.')
            return redirect('guia:detalle', pk=guia_pk)

        evaluacion.estado = 'completada'
        evaluacion.fecha_completado = timezone.now()
        evaluacion.porcentaje_cumplimiento = 100 # Asigna directamente el 100% al completar
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
    evaluacion = get_object_or_404(EvaluacionGuia, pk=pk, usuario=request.user)
    respuestas = RespuestaGuia.objects.filter(guia=evaluacion.guia, usuario=request.user).order_by('numero_pregunta')

    stats_por_categoria = {}
    for respuesta in respuestas:
        guia_actual = evaluacion.guia
        pregunta_info = next((p for categoria_data in guia_actual.contenido_procesado.get('tablas_cuestionario', [])
                              for bloque in categoria_data.get('bloques', [])
                              for p in bloque.get('preguntas', []) if p.get('id') == respuesta.numero_pregunta), None)
        if pregunta_info:
            categoria = next((cat['componente_a_evaluar'] for cat in guia_actual.contenido_procesado.get('tablas_cuestionario', [])
                              for bloque in cat.get('bloques', [])
                              if pregunta_info in bloque.get('preguntas', [])), 'General')
            if categoria not in stats_por_categoria:
                stats_por_categoria[categoria] = {'si': 0, 'no': 0, 'na': 0, 'total': 0}
            stats_por_categoria[categoria][respuesta.respuesta] += 1
            stats_por_categoria[categoria]['total'] += 1

    for categoria, stats in stats_por_categoria.items():
        if stats['total'] > 0:
            stats.update({
                'porcentaje_si': (stats['si'] / stats['total']) * 100,
                'porcentaje_no': (stats['no'] / stats['total']) * 100,
                'porcentaje_na': (stats['na'] / stats['total']) * 100
            })

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
    evaluaciones = EvaluacionGuia.objects.filter(usuario=request.user).select_related('guia', 'guia__archivo')
    # Ordenar: primero no completadas, luego completadas
    def is_completed(ev):
        return 1 if ev.estado == 'completada' else 0
    evaluaciones = sorted(evaluaciones, key=is_completed)
    evaluaciones_completadas = [e for e in evaluaciones if e.estado == 'completada']
    evaluaciones_en_progreso = [e for e in evaluaciones if e.estado == 'en_progreso']

    total_evaluaciones = len(evaluaciones)
    total_completadas = len(evaluaciones_completadas)
    total_en_progreso = len(evaluaciones_en_progreso)
    promedio_cumplimiento = sum(e.porcentaje_cumplimiento for e in evaluaciones_completadas) / total_completadas if total_completadas > 0 else 0

    stats_por_estado = {
        'completada': total_completadas,
        'en_progreso': total_en_progreso,
        'pendiente': len([e for e in evaluaciones if hasattr(e, 'estado') and e.estado == 'pendiente'])
    }

    ultimas_completadas = sorted(evaluaciones_completadas, key=lambda e: e.fecha_completado or e.fecha_inicio, reverse=True)[:5]
    mejor_evaluacion = max(evaluaciones_completadas, key=lambda e: getattr(e, 'respuestas_si', 0), default=None)
    evaluaciones_bajo_rendimiento = sorted([e for e in evaluaciones_completadas if e.porcentaje_cumplimiento < 60], key=lambda e: e.porcentaje_cumplimiento)

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
    archivo = get_object_or_404(Archivo, id=archivo_id, es_formulario=True)
    guia_existente = GuiaAutocontrol.objects.filter(archivo=archivo).first()
    if guia_existente:
        messages.info(request, 'Ya existe una guía para este archivo.')
        return redirect('guia:detalle', pk=guia_existente.pk)

    try:
        guia = GuiaAutocontrol.objects.create(archivo=archivo, titulo_guia=archivo.nombre, activa=True)
        guia.extraer_contenido_archivo()
        messages.success(request, 'Guía creada y procesada exitosamente.')
        return redirect('guia:detalle', pk=guia.pk)
    except Exception as e:
        messages.error(request, f'Error al procesar el archivo: {str(e)}')
        return redirect('guia:lista')

def crear_guias_desde_archivos():
    archivos_formulario = Archivo.objects.filter(es_formulario=True)
    for archivo in archivos_formulario:
        guia_existente = GuiaAutocontrol.objects.filter(archivo=archivo).first()
        if not guia_existente:
            try:
                guia = GuiaAutocontrol.objects.create(archivo=archivo, titulo_guia=archivo.nombre, activa=True)
                guia.extraer_contenido_archivo()
                #Descomentar para debug--> print(f"Guía creada para: {archivo.nombre}")
            except Exception as e:
                print(f"Error al crear guía para {archivo.nombre}: {e}")

@login_required
def archivo_guia_view(request):
    archivos = Archivo.objects.all().order_by('-fecha_subida')
    return render(request, 'guia/archivo_guia.html', {'archivos': archivos})

@login_required
@user_passes_test(lambda u: u.is_staff)
def lista_resumen_usuarios(request):
    """
    Vista principal para que el administrador obtenga una lista de todos los usuarios
    con un resumen de sus guías respondidas.
    """
    total_guias = GuiaAutocontrol.objects.count()
    
    usuarios = User.objects.annotate(
        total_evaluaciones=Count('evaluaciones_guias'),
        completadas=Count('evaluaciones_guias', filter=Q(evaluaciones_guias__estado='completada')),
        en_progreso=Count('evaluaciones_guias', filter=Q(evaluaciones_guias__estado='en_progreso')),
    )

    # Calcular las guías que faltan por completar para cada usuario
    for usuario in usuarios:
        usuario.pendientes = total_guias - usuario.total_evaluaciones

    context = {
        'usuarios': usuarios,
    }
    
    return render(request, 'guia/lista_resumen_usuarios.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def resumen_usuario_guias_detalle(request, user_id):
    """
    Vista detallada para mostrar el resumen de cada guía de un usuario específico.
    """
    usuario_a_revisar = get_object_or_404(User, pk=user_id)
    
    # Obtener todas las guías
    guias_existentes = GuiaAutocontrol.objects.all()
    
    # Obtener las evaluaciones de un usuario
    evaluaciones_usuario = {evaluacion.guia_id: evaluacion for evaluacion in EvaluacionGuia.objects.filter(usuario=usuario_a_revisar)}
    
    # Preparar el resumen de guías para el template
    resumen_guias = []
    for guia in guias_existentes:
        evaluacion = evaluaciones_usuario.get(guia.id)
        
        if evaluacion:
            estado = evaluacion.get_estado_display()
            if estado == 'Completada':
                # Si la guía está completada, obtenemos las estadísticas
                estadisticas = {
                    'total_preguntas': guia.total_preguntas,
                    'si': evaluacion.respuestas_si,
                    'no': evaluacion.respuestas_no,
                    'na': evaluacion.respuestas_na,
                    'pendientes': guia.total_preguntas - (evaluacion.respuestas_si + evaluacion.respuestas_no + evaluacion.respuestas_na)
                }
            else:
                estadisticas = {
                    'total_preguntas': guia.total_preguntas,
                    'si': evaluacion.respuestas_si,
                    'no': evaluacion.respuestas_no,
                    'na': evaluacion.respuestas_na,
                    'pendientes': guia.total_preguntas - (evaluacion.respuestas_si + evaluacion.respuestas_no + evaluacion.respuestas_na)
                }
        else:
            estado = 'Sin Empezar'
            estadisticas = None
            
        resumen_guias.append({
            'titulo': guia.titulo_guia,
            'componente': guia.componente,
            'estado': estado,
            'estadisticas': estadisticas,
        })
    
    context = {
        'usuario_a_revisar': usuario_a_revisar,
        'resumen_guias': resumen_guias,
    }
    
    return render(request, 'guia/resumen_usuario_guias_detalle.html', context)

@login_required
def generar_pdf_guia(request, pk):
    guia = get_object_or_404(GuiaAutocontrol, pk=pk)
    usuario = request.user
    
    # Obtener la evaluación y las respuestas del usuario para esta guía
    try:
        evaluacion = EvaluacionGuia.objects.get(guia=guia, usuario=usuario)
        respuestas = RespuestaGuia.objects.filter(guia=guia, usuario=usuario).order_by('numero_pregunta').only('numero_pregunta', 'respuesta', 'fundamentacion')
    except EvaluacionGuia.DoesNotExist:
        messages.error(request, 'No se encontró una evaluación completada para esta guía y usuario.')
        return redirect('guia:detalle', pk=pk)

    # Recolectar preguntas y respuestas
    data_for_pdf_table = [['ID Pregunta', 'Respuesta', 'Fundamentación']]
    for respuesta in respuestas:
        data_for_pdf_table.append([
            str(respuesta.numero_pregunta),
            respuesta.get_respuesta_display() or 'Sin Responder',
            respuesta.fundamentacion or ''
        ])

    # Crear el documento PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    
    story = []

    # Título de la Guía
    story.append(Paragraph(f"<b>Guía de Autocontrol: {guia.titulo_guia}</b>", styles['h1']))
    story.append(Spacer(1, 0.2 * inch))

    # Componente
    story.append(Paragraph(f"<b>Componente:</b> {guia.componente}", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))

    # Tabla de Respuestas
    # Estilos de tabla
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F2F2F2')), # Encabezado gris claro
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey), # Cuadrícula ligera
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('WORDWRAP', (1,1), (1,-1), 'LTR') # Para que el texto de la pregunta se ajuste
    ])
    
    # Ancho de columnas
    # (ID, Respuesta, Fundamentación)
    col_widths = [0.8 * inch, 0.8 * inch, 3.5 * inch]

    table = Table(data_for_pdf_table, colWidths=col_widths)
    table.setStyle(table_style)
    story.append(table)
    story.append(Spacer(1, 0.4 * inch))

    # Datos del Usuario
    story.append(Paragraph("<b>Elaborado por:</b>", styles['h3']))
    story.append(Paragraph(f"<b>Nombre:</b> {usuario.get_full_name() or 'N/A'}", styles['Normal']))
    story.append(Paragraph(f"<b>Cede:</b> {getattr(usuario, 'cede', usuario.perfil.get_cede_display() or 'N/A')}", styles['Normal'])) # Usar getattr para campos no estándar
    story.append(Paragraph(f"<b>Cargo:</b> {getattr(usuario, 'cargo', usuario.perfil.cargo or 'N/A')}", styles['Normal']))
    story.append(Paragraph(f"<b>Correo Electrónico:</b> {getattr(usuario, 'mail', usuario.email or 'N/A')}", styles['Normal']))
    story.append(Spacer(1, 0.4 * inch))

    # Firma
    story.append(Paragraph("<b>Firma:</b>", styles['Normal']))
    user_firma = getattr(usuario.perfil, 'firma_digital', None) if hasattr(usuario, 'perfil') else None
    temp_img_path = None
    if user_firma and hasattr(user_firma, 'path') and hasattr(user_firma, 'url'):
        try:
            from PIL import Image as PILImage
            if os.path.exists(user_firma.path):
                # Redimensionar y comprimir la imagen antes de insertarla
                pil_img = PILImage.open(user_firma.path)
                pil_img = pil_img.convert('RGB')
                max_width, max_height = 300, 150
                pil_img.thumbnail((max_width, max_height))
                temp_img_path = user_firma.path + '_temp_opt.jpg'
                pil_img.save(temp_img_path, format='JPEG', quality=70)
                img = Image(temp_img_path, width=1*inch, height=0.5*inch)
                story.append(img)
                # No eliminar aquí
            else:
                story.append(Paragraph(f"<i>Archivo de firma no encontrado en: {user_firma.path}</i>", styles['Normal']))
        except Exception as e:
            story.append(Paragraph(f"<i>Error al cargar firma: {e}</i>", styles['Normal']))
    elif user_firma and isinstance(user_firma, str) and (user_firma.startswith('http') or user_firma.startswith('/media/')):
        story.append(Paragraph(f"<i>Firma (URL): {user_firma}</i>", styles['Normal']))
    elif user_firma:
        story.append(Paragraph(f"<i>{user_firma}</i>", styles['Normal']))
    else:
        story.append(Paragraph("<i>(Firma no disponible)</i>", styles['Normal']))
    
    doc.build(story)
    
    # Obtener el contenido del buffer y devolverlo como HttpResponse
    pdf = buffer.getvalue()
    buffer.close()
    # Eliminar el archivo temporal si existe
    if temp_img_path and os.path.exists(temp_img_path):
        os.remove(temp_img_path)

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Guia_{guia.titulo_guia.replace(" ", "_")}_Completada_{timezone.now().strftime("%Y%m%d")}.pdf"'
    return response

@login_required
def generar_pdf_guia_async_view(request, pk):
    guia = get_object_or_404(GuiaAutocontrol, pk=pk)
    usuario = request.user
    output_dir = os.path.join(settings.MEDIA_ROOT, 'pdfs_temp')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f'guia_{guia.pk}_user_{usuario.pk}.pdf')
    # Lanza la tarea asíncrona
    task = generar_pdf_guia_async.delay(guia.pk, usuario.pk, output_path)
    # Devuelve el estado y la URL de descarga
    return JsonResponse({'status': 'processing', 'task_id': task.id, 'download_url': f'/media/pdfs_temp/guia_{guia.pk}_user_{usuario.pk}.pdf'})
