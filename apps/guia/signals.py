from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import RespuestaGuia, EvaluacionGuia

@receiver(post_save, sender=RespuestaGuia)
def actualizar_evaluacion(sender, instance, created, **kwargs):
    """
    Señal que se activa después de guardar una respuesta.
    Actualiza la evaluación correspondiente y el campo respuestas_json.
    """
    evaluacion = EvaluacionGuia.objects.get(guia=instance.guia, usuario=instance.usuario)
    # Recalcula y guarda el porcentaje y estado
    total_respuestas = RespuestaGuia.objects.filter(guia=instance.guia, usuario=instance.usuario, respuesta__in=['si', 'no', 'na']).count()
    total_preguntas = instance.guia.total_preguntas
    porcentaje = round((total_respuestas / total_preguntas) * 100, 2) if total_preguntas else 0
    evaluacion.porcentaje_cumplimiento = porcentaje
    evaluacion.estado = 'completada' if porcentaje >= 100 else 'en_progreso'
    evaluacion.save()
    # Actualiza el campo respuestas_json agrupado
    evaluacion.actualizar_respuestas_json()
