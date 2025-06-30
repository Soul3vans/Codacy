import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'infoweb.settings')
django.setup()
from docx import Document

from django.core.management.base import BaseCommand
from docx import Document

class Command(BaseCommand):
    help = 'Imprime todas las tablas del archivo DOCX'

    def handle(self, *args, **kwargs):
        ruta = 'media/archivos/1-GA_AMBIENTE_DE_CONTROL_AP_14.5.25.0.docx'
        doc = Document(ruta)
        for i, tabla in enumerate(doc.tables):
            print(f"\n--- Tabla {i+1} ---")
            for fila_idx, fila in enumerate(tabla.rows):
                celdas = [cell.text.strip() for cell in fila.cells]
                for col_idx, celda in enumerate(celdas):
                    print(f"Fila {fila_idx}, Columna {col_idx}: '{celda}'")
                print(" | ".join(celdas))