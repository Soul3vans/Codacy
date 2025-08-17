from celery import shared_task
from .models import GuiaAutocontrol, EvaluacionGuia, RespuestaGuia
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
import io, os

# Funciones de ayuda para refactorizar
def _crear_tabla_respuestas(respuestas):
    """Crea y estiliza la tabla de respuestas para el PDF."""
    data_for_pdf_table = [['ID Pregunta', 'Respuesta', 'Fundamentación']]
    for respuesta in respuestas:
        data_for_pdf_table.append([
            str(respuesta.numero_pregunta),
            respuesta.get_respuesta_display() or 'Sin Responder',
            Paragraph(respuesta.fundamentacion or '', getSampleStyleSheet()['Normal']) # Usar Paragraph para el word-wrap
        ])

    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F2F2F2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ])
    col_widths = [0.8 * inch, 0.8 * inch, 3.5 * inch]
    table = Table(data_for_pdf_table, colWidths=col_widths)
    table.setStyle(table_style)
    return table

def _obtener_datos_usuario(usuario):
    """Obtiene los datos del perfil del usuario."""
    styles = getSampleStyleSheet()
    story = [
        Paragraph("<b>Elaborado por:</b>", styles['h3']),
        Paragraph(f"<b>Nombre:</b> {usuario.get_full_name() or 'N/A'}", styles['Normal']),
        Paragraph(f"<b>Cede:</b> {getattr(usuario, 'cede', getattr(usuario.perfil, 'get_cede_display', lambda: 'N/A')())}", styles['Normal']),
        Paragraph(f"<b>Cargo:</b> {getattr(usuario, 'cargo', getattr(usuario.perfil, 'cargo', 'N/A'))}", styles['Normal']),
        Paragraph(f"<b>Correo Electrónico:</b> {getattr(usuario, 'mail', getattr(usuario, 'email', 'N/A'))}", styles['Normal']),
    ]
    return story

def _manejar_firma_usuario(usuario, story, styles):
    """Añade la firma del usuario al PDF, con manejo de errores."""
    story.append(Spacer(1, 0.4 * inch))
    story.append(Paragraph("<b>Firma:</b>", styles['Normal']))
    user_firma = getattr(getattr(usuario, 'perfil', None), 'firma_digital', None)
    
    if not user_firma:
        story.append(Paragraph("<i>(Firma no disponible)</i>", styles['Normal']))
        return

    try:
        from PIL import Image as PILImage
        if os.path.exists(user_firma.path):
            pil_img = PILImage.open(user_firma.path).convert('RGB')
            pil_img.thumbnail((300, 150))
            temp_img_path = user_firma.path + '_temp_opt.jpg'
            pil_img.save(temp_img_path, format='JPEG', quality=70)
            story.append(Image(temp_img_path, width=1*inch, height=0.5*inch))
            os.remove(temp_img_path)
        else:
            story.append(Paragraph(f"<i>Archivo de firma no encontrado en: {user_firma.path}</i>", styles['Normal']))
    except Exception as e:
        story.append(Paragraph(f"<i>Error al cargar firma: {e}</i>", styles['Normal']))
        
@shared_task
def generar_pdf_guia_async(guia_id, usuario_id, output_path):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    guia = GuiaAutocontrol.objects.get(pk=guia_id)
    usuario = User.objects.get(pk=usuario_id)
    evaluacion = EvaluacionGuia.objects.get(guia=guia, usuario=usuario)
    respuestas = RespuestaGuia.objects.filter(guia=guia, usuario=usuario).order_by('numero_pregunta')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Secciones principales del PDF
    story.append(Paragraph(f"<b>Guía de Autocontrol: {guia.titulo_guia}</b>", styles['h1']))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(f"<b>Componente:</b> {guia.componente}", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))

    # Añadir la tabla de respuestas (ahora en una función separada)
    story.append(_crear_tabla_respuestas(respuestas))
    story.append(Spacer(1, 0.4 * inch))

    # Añadir los datos del usuario (ahora en una función separada)
    story.extend(_obtener_datos_usuario(usuario))
    story.append(Spacer(1, 0.4 * inch))

    # Añadir la firma del usuario (ahora en una función separada)
    _manejar_firma_usuario(usuario, story, styles)

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()

    with open(output_path, 'wb') as f:
        f.write(pdf)

    return output_path