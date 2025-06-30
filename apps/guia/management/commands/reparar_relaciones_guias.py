from django.core.management.base import BaseCommand
from apps.guia.models import GuiaAutocontrol
from apps.dashboard.models import Archivo
import os
from django.conf import settings
import logging

class Command(BaseCommand):
    help = 'Verifica y repara la relación entre guías y archivos físicos en media/archivos/'

    def handle(self, *args, **options):
        logger = logging.getLogger('django')
        guias = GuiaAutocontrol.objects.all()
        archivos = Archivo.objects.all()
        archivos_dict = {os.path.basename(a.archivo.name): a for a in archivos if a.archivo}
        reparadas = 0
        for guia in guias:
            if not guia.archivo or not getattr(guia.archivo, 'archivo', None):
                # Buscar archivo físico por nombre similar al título de la guía
                nombre_base = guia.titulo_guia.split(':')[0].strip().replace(' ', '_')
                for filename, archivo_obj in archivos_dict.items():
                    if nombre_base.lower() in filename.lower():
                        guia.archivo = archivo_obj
                        guia.save()
                        self.stdout.write(self.style.SUCCESS(f'Relación reparada: Guía {guia.pk} -> Archivo {filename}'))
                        logger.info(f'Relación reparada: Guía {guia.pk} -> Archivo {filename}')
                        reparadas += 1
                        break
        if reparadas == 0:
            self.stdout.write(self.style.WARNING('No se reparó ninguna relación. Revisa los nombres de archivos y guías.'))
            logger.warning('No se reparó ninguna relación. Revisa los nombres de archivos y guías.')
        else:
            self.stdout.write(self.style.SUCCESS(f'Relaciones reparadas: {reparadas}'))
            logger.info(f'Relaciones reparadas: {reparadas}')
