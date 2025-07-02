from django.utils import timezone
from .models import Perfil
import logging

logger = logging.getLogger(__name__)
class UpdateLastActivityMiddleware:
    """Middleware para actualizar la última actividad del usuario"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Actualizar last_activity si el usuario está autenticado
        if request.user.is_authenticated:
            try:
                perfil, created = Perfil.objects.get_or_create(user=request.user)
                perfil.last_activity = timezone.now()
                perfil.save(update_fields=['last_activity'])
            except Exception as e:
                logger.error(f"Error al actualizar last_activity: {e}")
        
        return response