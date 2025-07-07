from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import RespuestaGuia, EvaluacionGuia

@receiver(post_save, sender=RespuestaGuia)
def actualizar_evaluacion(sender, instance, created, **kwargs):
    """
    Señal que se activa después de guardar una respuesta.
    Actualiza completamente la evaluación correspondiente.
    """
    try:
        evaluacion = EvaluacionGuia.objects.get(
            guia=instance.guia, 
            usuario=instance.usuario
        )
        # Actualiza todos los campos relevantes
        evaluacion.actualizar_estadisticas()
        evaluacion.actualizar_respuestas_json()
        
        # Recalcula el porcentaje basado en respuestas válidas
        respuestas_validas = RespuestaGuia.objects.filter(
            guia=instance.guia,
            usuario=instance.usuario,
            respuesta__in=['si', 'no', 'na']
        ).count()
        
        total_preguntas = instance.guia.total_preguntas
        if total_preguntas > 0:
            porcentaje = round((respuestas_validas / total_preguntas) * 100, 2)
            evaluacion.porcentaje_cumplimiento = porcentaje
            evaluacion.estado = 'completada' if porcentaje >= 100 else 'en_progreso'
            evaluacion.save()
            
    except EvaluacionGuia.DoesNotExist:
        # Si no existe la evaluación, se creará cuando el usuario visite la guía
        pass