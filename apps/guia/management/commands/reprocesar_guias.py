from django.core.management.base import BaseCommand
from apps.guia.models import GuiaAutocontrol
import logging

class Command(BaseCommand):
    help = 'Reprocesa el contenido de todas las guías de autocontrol o una guía específica por ID'

    def add_arguments(self, parser):
        parser.add_argument(
            'guia_id',
            nargs='?',
            type=int,
            help='ID de la guía a reprocesar (opcional, si no se indica se reprocesan todas)'
        )

    def handle(self, *args, **options):
        logger = logging.getLogger('django')
        guia_id = options.get('guia_id')
        if guia_id:
            guias = GuiaAutocontrol.objects.filter(pk=guia_id)
            if not guias.exists():
                self.stdout.write(self.style.ERROR(f'No existe la guía con ID {guia_id}'))
                return
        else:
            guias = GuiaAutocontrol.objects.all()
        total = guias.count()
        self.stdout.write(self.style.NOTICE(f'Reprocesando {total} guía(s)...'))
        logger.info(f'Reprocesando {total} guía(s)...')
        for guia in guias:
            self.stdout.write(f"[DEBUG] Entrando a extraer_contenido_archivo para la guía: {guia.pk}")
            try:
                guia.extraer_contenido_archivo()
                guia.save()
                self.stdout.write(self.style.SUCCESS(f'Guía {guia.pk} procesada'))
                logger.info(f'Guía {guia.pk} procesada')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error procesando guía {guia.pk}: {e}'))
                logger.error(f'Error procesando guía {guia.pk}: {e}')
        self.stdout.write(self.style.SUCCESS('¡Reprocesamiento completado!'))
        logger.info('¡Reprocesamiento completado!')
