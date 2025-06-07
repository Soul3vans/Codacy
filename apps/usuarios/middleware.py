# your_app/middleware.py (create this file if it doesn't exist)

from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class LastActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            user = request.user
            logger.debug(f"Middleware: User {user.username} is authenticated.")

            # Ensure profile exists, this is crucial
            if not hasattr(user, 'perfil') or user.perfil is None:
                from .models import Perfil # Import inside to avoid circular dependency
                logger.debug(f"Middleware: Creating profile for {user.username}.")
                Perfil.objects.create(user=user)
                user.refresh_from_db() # Reload user object to get new profile

            current_time = timezone.now()
            old_last_activity = user.perfil.last_activity

            # Optional: Add a debounce to avoid writing to DB too often (e.g., every 5 seconds)
            # This could be why it's not updating if you're testing rapidly
            update_needed = True
            if old_last_activity:
                if (current_time - old_last_activity).total_seconds() < 5: # 5 seconds debounce
                    update_needed = False

            if update_needed:
                user.perfil.last_activity = current_time
                user.perfil.save(update_fields=['last_activity'])
                logger.info(f"Middleware: Updated last_activity for {user.username} to {current_time}.")
            else:
                logger.debug(f"Middleware: last_activity for {user.username} not updated (debounce). Current: {old_last_activity}")

        response = self.get_response(request)
        return response