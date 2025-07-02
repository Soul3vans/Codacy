from django.core.management.base import BaseCommand
from apps.guia.models import GuiaAutocontrol

class Command(BaseCommand):
    help = 'Prueba la extracción de contenido de una guía específica'

    def add_arguments(self, parser):
        parser.add_argument('guia_id', type=int, help='ID de la guía a procesar')

    def handle(self, *args, **options):
        try:
            guia = GuiaAutocontrol.objects.get(pk=options['guia_id'])
            self.stdout.write(f"Procesando guía: {guia.titulo_guia}")
            
            # Limpiar contenido previo
            guia.contenido_procesado = {}
            guia.save()
            
            # Procesar
            guia.extraer_contenido_archivo()
            
            if guia.contenido_procesado and 'tablas_cuestionario' in guia.contenido_procesado:
                # --- MODIFICATION START ---
                all_preguntas = []
                for tabla in guia.contenido_procesado['tablas_cuestionario']:
                    if 'preguntas' in tabla:
                        all_preguntas.extend(tabla['preguntas'])
                
                self.stdout.write(
                    self.style.SUCCESS(f'Éxito: {len(all_preguntas)} preguntas extraídas')
                )
                
                # Mostrar algunas preguntas (utilizando all_preguntas)
                for i, pregunta in enumerate(all_preguntas[:5]):
                    self.stdout.write(f"Pregunta {pregunta.get('numero', i+1)}: {pregunta.get('texto', '')[:100]}...")
                # --- MODIFICATION END ---
            else:
                self.stdout.write(
                    self.style.ERROR('No se pudo procesar el contenido o la estructura de preguntas es incorrecta.')
                )
                
        except GuiaAutocontrol.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Guía con ID {options["guia_id"]} no encontrada')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {e}')
            )
