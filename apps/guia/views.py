from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from .models import GuiaAutocontrol, RespuestaGuia, EvaluacionGuia
from apps.dashboard.models import Archivo
import io
import json
import logging

logger = logging.getLogger(__name__)

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
        ).select_related('archivo')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        evaluaciones_usuario = EvaluacionGuia.objects.filter(usuario=self.request.user)

        completadas_por_guia = {
            guia.id: EvaluacionGuia.objects.filter(
                usuario=self.request.user,
                guia=guia,
                estado='completada'
            ).count()
            for guia in context['guias']
        }

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
        # --- Lógica para guardar respuestas vía AJAX ---
        try:
            # Intentar cargar los datos JSON del cuerpo de la solicitud
            data = json.loads(request.body)
            numero_pregunta = data.get('id')
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
            # Guardar o actualizar la RespuestaGuia
            # El campo 'fecha_respuesta' con auto_now=True se actualizará automáticamente
            respuesta_guia, created = RespuestaGuia.objects.update_or_create(
                evaluacion=evaluacion,
                numero_pregunta=numero_pregunta,
                defaults={
                    'respuesta': respuesta if respuesta else None, # Guardar None si la respuesta está vacía
                    'fundamentacion': fundamentacion
                }
            )
            print(f"Respuesta guardada: {respuesta_guia}")
            # Recalcular el progreso y actualizar la evaluación después de guardar la respuesta
            all_preguntas_flat = []
            if guia.contenido_procesado and 'tablas_cuestionario' in guia.contenido_procesado:
                for categoria in guia.contenido_procesado['tablas_cuestionario']:
                    for bloque in categoria.get('bloques', []):
                        for pregunta in bloque.get('preguntas', []):
                            all_preguntas_flat.append(pregunta)
            # Re-obtener las respuestas actualizadas del usuario para este cálculo
            respuestas_usuario_actualizadas = RespuestaGuia.objects.filter(
                evaluacion__guia=guia,
                evaluacion__usuario=request.user
            ).values('numero_pregunta', 'respuesta')
            respuestas_dict_actualizadas = {r['numero_pregunta']: r for r in respuestas_usuario_actualizadas}
            total_preguntas = len(all_preguntas_flat)
            # Asegúrate de usar 'id' para la clave de la pregunta si es lo que usas en tu JSON
            preguntas_respondidas = sum(1 for p in all_preguntas_flat if respuestas_dict_actualizadas.get(p.get('id', p.get('numero')), {}).get('respuesta') in ['si', 'no', 'na'])
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
            evaluacion__guia=guia,
            evaluacion__usuario=request.user
        ).values('numero_pregunta', 'respuesta', 'fundamentacion')
        respuestas_dict = {r['numero_pregunta']: r for r in respuestas_usuario}
        for categoria in guia.contenido_procesado['tablas_cuestionario']:
            cat = {
                'categoria': categoria.get('categoria', ''),
                'componente_a_evaluar': categoria.get('componente_a_evaluar', ''),
                'bloques': []
            }
            for bloque in categoria.get('bloques', []):
                blq = {'encabezado': bloque.get('encabezado', ''), 'preguntas': []}
                for pregunta in bloque.get('preguntas', []):
                    num = pregunta.get('id') # Usar 'id' como clave para la pregunta
                    pregunta_copy = pregunta.copy()
                    if num is not None and num in respuestas_dict:
                        pregunta_copy.update({
                            'user_respuesta': respuestas_dict[num]['respuesta'],
                            'user_fundamentacion': respuestas_dict[num]['fundamentacion']
                        })
                    else:
                        pregunta_copy.update({
                            'user_respuesta': None,
                            'user_fundamentacion': None
                        })
                    blq['preguntas'].append(pregunta_copy)
                    # Añadir a la lista plana para el conteo total
                    all_preguntas_flat.append(pregunta_copy)
                cat['bloques'].append(blq)
            preguntas_por_categoria.append(cat)

    total_preguntas = len(all_preguntas_flat)
    # Es crucial que aquí también uses 'id' o la clave correcta para buscar en respuestas_dict
    preguntas_respondidas = sum(1 for p in all_preguntas_flat if p.get('user_respuesta') in ['si', 'no', 'na'])
    porcentaje_completado = round((preguntas_respondidas / total_preguntas * 100)) if total_preguntas > 0 else 0
    # Asegurarse de que la evaluación siempre se obtiene/crea para el contexto
    evaluacion, created = EvaluacionGuia.objects.get_or_create(
        guia=guia,
        usuario=request.user,
        defaults={'estado': 'en_progreso'}
    )
    # Actualizar estado y porcentaje incluso en la solicitud GET si se cargó la página
    evaluacion.estado = 'completada' if porcentaje_completado == 100 else 'en_progreso'
    evaluacion.porcentaje_cumplimiento = porcentaje_completado
    evaluacion.save()
    context = {
        'guia': guia,
        'preguntas_por_categoria': preguntas_por_categoria if preguntas_por_categoria else None,
        'preguntas_planas': all_preguntas_flat, # Puedes seguir usándola para el contexto
        'evaluacion': evaluacion,
        'total_preguntas': total_preguntas,
        'preguntas_respondidas': preguntas_respondidas,
        'porcentaje_completado': porcentaje_completado,
    }
    return render(request, 'guia/detalle_guia.html', context)

@login_required
@transaction.atomic
def guardar_respuesta(request, guia_pk):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)
        guia = get_object_or_404(GuiaAutocontrol, pk=guia_pk, activa=True)
        evaluacion, created = EvaluacionGuia.objects.get_or_create(
            guia=guia,
            usuario=request.user,
            defaults={'estado': 'en_progreso'}
        )

        responses_to_process = []
        if isinstance(data, list): # Si se envían múltiples respuestas
            responses_to_process = data
        elif isinstance(data, dict): # Si se envía una sola respuesta
            responses_to_process = [data]
        else:
            return JsonResponse({'status': 'error', 'message': 'Formato de datos JSON inesperado.'}, status=400)

        for item_data in responses_to_process:
            numero_pregunta = item_data.get('numero_pregunta')
            respuesta = item_data.get('respuesta')
            fundamentacion = item_data.get('fundamentacion', '')

            if numero_pregunta is None:
                continue 

            try:
                numero_pregunta = int(numero_pregunta)
            except (ValueError, TypeError):
                continue 

            RespuestaGuia.objects.update_or_create(
                evaluacion=evaluacion,
                numero_pregunta=numero_pregunta,
                defaults={
                    'respuesta': respuesta if respuesta else None,
                    'fundamentacion': fundamentacion
                }
            )

        # Recalcular el progreso
        all_preguntas_flat = []
        if guia.contenido_procesado and 'tablas_cuestionario' in guia.contenido_procesado:
            for categoria in guia.contenido_procesado['tablas_cuestionario']:
                for bloque in categoria.get('bloques', []):
                    for pregunta in bloque.get('preguntas', []):
                        all_preguntas_flat.append(pregunta)
        
        total_preguntas = len(all_preguntas_flat)
        if total_preguntas == 0:
            return JsonResponse({
                'status': 'error',
                'message': 'No se encontraron preguntas en la guía.'
            }, status=400)
        
        respuestas_usuario = RespuestaGuia.objects.filter(
            evaluacion=evaluacion,
            respuesta__in=['si', 'no', 'na']
        ).count()
        
        porcentaje_completado = round((respuestas_usuario / total_preguntas * 100))
        
        evaluacion.estado = 'completada' if porcentaje_completado == 100 else 'en_progreso'
        evaluacion.porcentaje_cumplimiento = porcentaje_completado
        evaluacion.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Respuestas guardadas correctamente.',
            'porcentaje_completado': porcentaje_completado,
            'preguntas_respondidas': respuestas_usuario,
            'total_preguntas': total_preguntas
        })

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Formato JSON inválido.'}, status=400)
    except Exception as e:
        logger.error(f"Error en guardar_respuesta: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Error al guardar la respuesta: {str(e)}'}, status=500)
        print(f"Error en guardar_respuesta: JsonResponse: {str(e)}")

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

        # CORRECCIÓN: Filtrar RespuestaGuia a través de la relación evaluacion__guia
        respuestas_count = RespuestaGuia.objects.filter(evaluacion__guia=guia, evaluacion__usuario=request.user).count()

        if respuestas_count < total_preguntas:
            messages.warning(request, f'Faltan {total_preguntas - respuestas_count} preguntas por responder.')
            return redirect('guia:detalle', pk=guia_pk)

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
    evaluacion = get_object_or_404(EvaluacionGuia, pk=pk, usuario=request.user)
    respuestas = RespuestaGuia.objects.filter(evaluacion=evaluacion).order_by('numero_pregunta')

    stats_por_categoria = {}
    for respuesta in respuestas:
        # Acceder a la guía a través de la evaluación
        guia_actual = respuesta.evaluacion.guia
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
    evaluaciones = EvaluacionGuia.objects.filter(usuario=request.user).select_related('guia', 'guia__archivo').order_by('-fecha_inicio')
    evaluaciones_completadas = evaluaciones.filter(estado='completada')
    evaluaciones_en_progreso = evaluaciones.filter(estado='en_progreso')

    total_evaluaciones = evaluaciones.count()
    total_completadas = evaluaciones_completadas.count()
    total_en_progreso = evaluaciones_en_progreso.count()
    promedio_cumplimiento = evaluaciones_completadas.aggregate(avg_pct=Avg('porcentaje_cumplimiento'))['avg_pct'] or 0

    stats_por_estado = {
        'completada': total_completadas,
        'en_progreso': total_en_progreso,
        'pendiente': evaluaciones.filter(estado='pendiente').count() if hasattr(evaluaciones.first(), 'estado') else 0
    }

    ultimas_completadas = evaluaciones_completadas.order_by('-fecha_completada')[:5]
    mejor_evaluacion = evaluaciones_completadas.order_by('-porcentaje_cumplimiento').first()
    evaluaciones_bajo_rendimiento = evaluaciones_completadas.filter(porcentaje_cumplimiento__lt=60).order_by('porcentaje_cumplimiento')

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
def generar_pdf_guia(request, pk):
    guia = get_object_or_404(GuiaAutocontrol, pk=pk)
    usuario = request.user
    
    # Obtener la evaluación y las respuestas del usuario para esta guía
    try:
        evaluacion = EvaluacionGuia.objects.get(guia=guia, usuario=usuario)
        respuestas = RespuestaGuia.objects.filter(evaluacion=evaluacion).order_by('numero_pregunta')
    except EvaluacionGuia.DoesNotExist:
        messages.error(request, 'No se encontró una evaluación completada para esta guía y usuario.')
        return redirect('guia:detalle', pk=pk) # Redirige de nuevo a la guía

    # Recolectar preguntas y respuestas
    data_for_pdf_table = [['ID Pregunta', 'Pregunta', 'Respuesta', 'Fundamentación']]
    all_questions_map = {} # Para mapear ID de pregunta a su texto completo
    
    if guia.contenido_procesado and 'tablas_cuestionario' in guia.contenido_procesado:
        for categoria in guia.contenido_procesado['tablas_cuestionario']:
            for bloque in categoria.get('bloques', []):
                for pregunta in bloque.get('preguntas', []):
                    question_id = pregunta.get('id')
                    question_text = pregunta.get('texto')
                    if question_id:
                        all_questions_map[question_id] = question_text
    
    for respuesta in respuestas:
        question_text = all_questions_map.get(respuesta.numero_pregunta, 'Pregunta no encontrada')
        data_for_pdf_table.append([
            str(respuesta.numero_pregunta),
            Paragraph(question_text, getSampleStyleSheet()['Normal']), # Usar Paragraph para texto largo
            respuesta.get_respuesta_display() or 'Sin Responder', # Mostrar el texto de la opción
            Paragraph(respuesta.fundamentacion, getSampleStyleSheet()['Normal']) if respuesta.fundamentacion else ''
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
    
    # Ancho de columnas (ajustar según tus necesidades)
    # (ID, Pregunta, Respuesta, Fundamentación)
    col_widths = [0.8 * inch, 3.5 * inch, 0.8 * inch, 2.5 * inch]
    
    table = Table(data_for_pdf_table, colWidths=col_widths)
    table.setStyle(table_style)
    story.append(table)
    story.append(Spacer(1, 0.4 * inch))

    # Datos del Usuario
    story.append(Paragraph("<b>Elaborado por:</b>", styles['h3']))
    story.append(Paragraph(f"<b>Nombre:</b> {usuario.get_full_name() or 'N/A'}", styles['Normal']))
    story.append(Paragraph(f"<b>Cede:</b> {getattr(usuario, 'cede', 'N/A')}", styles['Normal'])) # Usar getattr para campos no estándar
    story.append(Paragraph(f"<b>Cargo:</b> {getattr(usuario, 'cargo', 'N/A')}", styles['Normal']))
    story.append(Paragraph(f"<b>Correo Electrónico:</b> {getattr(usuario, 'mail', usuario.email or 'N/A')}", styles['Normal']))
    story.append(Spacer(1, 0.4 * inch))

    # Firma
    story.append(Paragraph("<b>Firma:</b>", styles['Normal']))
    user_firma = getattr(usuario, 'firma', None)
    if user_firma and hasattr(user_firma, 'url'): # Asume que 'firma' es un ImageField o FileField
        try:
            # Asegúrate de que la ruta sea accesible por ReportLab
            # Esto puede requerir un manejo de rutas si no es directamente accesible desde el sistema de archivos
            # Por ejemplo, si está en S3, necesitarías descargarla o usar una URL accesible
            firma_path = user_firma.path # Esto funciona si la imagen está en el sistema de archivos local
            img = Image(firma_path, width=1*inch, height=0.5*inch) # Ajusta el tamaño
            story.append(img)
        except Exception as e:
            story.append(Paragraph(f"<i>Error al cargar firma: {e}</i>", styles['Normal']))
    elif user_firma: # Si 'firma' es una cadena de texto (e.g., ruta URL, o texto plano)
        story.append(Paragraph(f"<i>{user_firma}</i>", styles['Normal']))
    else:
        story.append(Paragraph("<i>(Firma no disponible)</i>", styles['Normal']))
    
    doc.build(story)
    
    # Obtener el contenido del buffer y devolverlo como HttpResponse
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Guia_{guia.titulo_guia.replace(" ", "_")}_Completada_{timezone.now().strftime("%Y%m%d")}.pdf"'
    return response
