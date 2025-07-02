from django.core.management.base import BaseCommand
from apps.guia.models import GuiaAutocontrol
from apps.dashboard.models import Archivo
import logging

class Command(BaseCommand):
    help = 'Lista los títulos de guías y los nombres de archivos disponibles para facilitar la relación manual.'

    def handle(self, *args, **options):
        logger = logging.getLogger('django')
        self.stdout.write('=== Guías en la base de datos ===')
        logger.info('=== Guías en la base de datos ===')
        for guia in GuiaAutocontrol.objects.all():
            msg = f'Guía {guia.pk}: "{guia.titulo_guia}" | Archivo asignado: {getattr(guia.archivo, "archivo", None)}'
            self.stdout.write(msg)
            logger.info(msg)
        self.stdout.write('\n=== Archivos en la base de datos ===')
        logger.info('=== Archivos en la base de datos ===')
        for archivo in Archivo.objects.all():
            msg = f'Archivo {archivo.pk}: "{archivo.archivo.name}"'
            self.stdout.write(msg)
            logger.info(msg)
