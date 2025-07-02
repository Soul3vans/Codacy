"""Modelo para las Guías de Autocontrol con serialización JSON segura"""
from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from docx import Document
from apps.dashboard.models import Archivo
import re
import logging
import PyPDF2
import mimetypes

User = get_user_model()
logger = logging.getLogger(__name__)

class GuiaAutocontrol(models.Model):
    """
    Modelo que extiende de Archivo para las Guías de Autocontrol.
    Permite la extracción, limpieza y estructuración de cuestionarios desde PDF/DOCX.
    """
    archivo = models.OneToOneField(
        Archivo,
        on_delete=models.CASCADE,
        related_name='guia_autocontrol',
        limit_choices_to={'es_formulario': True}
    )
    titulo_guia = models.CharField(max_length=300, blank=True)
    componente = models.CharField(max_length=200, blank=True)
    proposito = models.TextField(blank=True)
    contenido_procesado = models.JSONField(default=dict, blank=True)
    activa = models.BooleanField(default=True)
    fecha_procesamiento = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Guía de Autocontrol'
        verbose_name_plural = 'Guías de Autocontrol'
        ordering = ['-fecha_procesamiento']

    def __str__(self):
        return f"Guía: {self.titulo_guia or self.archivo.nombre}"

    def get_absolute_url(self):
        return reverse('guia:detalle', kwargs={'pk': self.pk})

    def _limpiar_texto(self, texto):
        """Limpia el texto eliminando caracteres no deseados y normalizando espacios."""
        if not isinstance(texto, str):
            return str(texto)
        texto = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', texto)
        texto = re.sub(r'\s+', ' ', texto)
        try:
            texto = texto.encode('utf-8').decode('utf-8')
        except UnicodeEncodeError:
            texto = texto.encode('ascii', 'ignore').decode('ascii')
        return texto.strip()

    def _procesar_estructura_para_json(self, estructura):
        """Procesa una estructura (lista o diccionario) para asegurar compatibilidad JSON."""
        if isinstance(estructura, list):
            return [self._procesar_estructura_para_json(item) for item in estructura]
        elif isinstance(estructura, dict):
            return {k: self._procesar_estructura_para_json(v) for k, v in estructura.items()}
        else:
            return self._limpiar_texto(str(estructura))

    def _crear_contenido_procesado_seguro(self, error=None):
        """Helper para crear un diccionario seguro para contenido_procesado."""
        return {'error': error} if error else {}
    
    def _parsear_tabla_docx(self, path):
        doc = Document(path)
        tablas_cuestionario = []
        componente_actual = None
        dentro_tabla_cuestionario = False
        componentes_procesados = set()
        bloque = False

        # Inicializa un contador para las preguntas
        contador_preguntas = 0

        for tabla in doc.tables:
            for fila in tabla.rows:
                celdas = [self._limpiar_texto(cell.text) if cell.text else "" for cell in fila.cells]
                #Descomentar para debug---> print(f"Celdas: {celdas}")  # Impresión de depuración

                if not any(celdas):
                    #Descomentar para debug---> print("Fila vacía, continuando...")
                    continue

                if any("ASPECTOS A VERIFICAR" in c.upper() for c in celdas if c):
                    dentro_tabla_cuestionario = True
                    #Descomentar para debug---> print("Entrando a tabla de cuestionario")
                    continue

                if not dentro_tabla_cuestionario:
                    #Descomentar para debug---> print("Fuera de tabla de cuestionario, continuando...")
                    continue

                if celdas and "Elaborado y aprobado" in celdas[0]:
                    #Descomentar para debug---> print("Tabla 'Elaborado y aprobado' encontrada, terminando...")
                    break

                if len(celdas) >= 3 and len(set(c for c in celdas if c)) == 1:
                    componente_texto = self._limpiar_texto(celdas[0])
                    if componente_texto and componente_texto not in componentes_procesados:
                        componente_actual = {
                            "componente_a_evaluar": componente_texto,
                            "bloques": []
                        }
                        tablas_cuestionario.append(componente_actual)
                        componentes_procesados.add(componente_texto)
                        bloque = None
                        #Descomentar para debug---> print(f"Componente detectado: {componente_texto}")
                        continue

                # Detectar encabezado
                encabezado_detectado = False
                for celda in celdas:
                    if celda and re.search(r":\s*$", celda):
                        encabezado_texto = self._limpiar_texto(celda)
                        if componente_actual:
                            bloque = {
                                "encabezado": encabezado_texto,
                                "preguntas": []
                            }
                            componente_actual["bloques"].append(bloque)
                            #Descomentar para debug--> print(f"Encabezado detectado y añadido: {encabezado_texto}")
                        encabezado_detectado = True
                        break  # Solo un encabezado por fila

                # Detectar preguntas si no hubo encabezado en la misma fila
                if not encabezado_detectado and len(celdas) > 1:
                    if re.match(r"^\d+\.?\s*.+", celdas[1]):
                        numero_pregunta = int(re.search(r"^\d+", celdas[1]).group())
                        texto_pregunta = re.sub(r"^\d+\.?\s*", "", celdas[1]).strip()
                    else:
                        numero_pregunta = None
                        texto_pregunta = celdas[1].strip()

                    if not bloque and componente_actual:
                        bloque = {
                            "encabezado": "",
                            "preguntas": []
                        }
                        componente_actual["bloques"].append(bloque)

                    # Añadir la pregunta al bloque actual con un identificador único
                    if componente_actual and bloque:
                        contador_preguntas += 1
                        bloque["preguntas"].append({
                            "numero_pregunta": contador_preguntas,  # Identificador único
                            "texto": texto_pregunta
                        })
                        #Descomentar para debug--> print(f"[Debug]:preguntas: {bloque}")

        return tablas_cuestionario

    def extraer_contenido_archivo(self):
        """
        Extrae y procesa el contenido del archivo asociado (PDF/DOCX).
        Limpia y estructura componente, propósito y cuestionario.
        """
        if not self.archivo or not self.archivo.archivo:
            raise ValueError("No hay un archivo asociado a esta Guía de Autocontrol.")

        file_path = self.archivo.archivo.path
        mime, _ = mimetypes.guess_type(file_path)
        full_text = ""

        try:
            if mime == 'application/pdf' or file_path.lower().endswith('.pdf'):
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    full_text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
                tablas_cuestionario = self._parsear_tabla_pdf(file_path)
            elif mime == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' or file_path.lower().endswith('.docx'):
                doc = Document(file_path)
                full_text = "\n".join(para.text for para in doc.paragraphs)
                for table in doc.tables:
                    for row in table.rows:
                        row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                        if row_text:
                            full_text += row_text + "\n"
                tablas_cuestionario = self._parsear_tabla_docx(file_path)
            else:
                raise ValueError("Tipo de archivo no soportado para extracción automática.")

            comp_match = re.search(r'COMPONENTE\s+«?([A-ZÁÉÍÓÚÜÑ\s]+)»?', full_text, re.IGNORECASE)
            self.componente = comp_match.group(1).strip() if comp_match else ""

            prop_match = re.search(r'Propósito:\s*([\s\S]*?)(?=Principales fuentes de información para el autocontrol|$)', full_text, re.IGNORECASE)
            if prop_match:
                proposito = prop_match.group(1).strip()
                proposito = re.sub(r'(?<![.!?])\n(?!\n)', ' ', proposito)
                proposito = re.sub(r'\s{2,}', ' ', proposito)
                proposito = re.sub(r'\n\s*\n', '\n', proposito)
                proposito = re.sub(r'(\s*\.\s*)+', '. ', proposito)
                proposito = proposito.replace('•', '')
                lineas = [l.strip() for l in proposito.split('\n') if l.strip() and not re.fullmatch(r'\d+', l.strip())]
                buffer = ''
                parrafos = []
                for line in lineas:
                    line = re.sub(r'^[0-9]+[\s\.-·]*', '', line)
                    if re.match(r'^[A-ZÁÉÍÓÚÜÑ\s]+:$', line):
                        continue
                    elif re.match(r'^(-|\*|•|·|[a-zA-Z]\))', line) or line.startswith(''):
                        continue
                    else:
                        if buffer:
                            buffer += ' '
                        buffer += line
                        if line.endswith('.'):
                            parrafos.append(buffer.strip())
                            buffer = ''
                if buffer:
                    parrafos.append(buffer.strip())
                self.proposito = " ".join(parrafos)

            self.contenido_procesado = {
                "componente": self.componente,
                "proposito": self.proposito,
                "tablas_cuestionario": tablas_cuestionario if tablas_cuestionario else []
            }
            self.save()

        except Exception as e:
            logger.error(f"Error al extraer contenido del archivo {self.archivo.nombre}: {e}")
            raise

class EvaluacionGuia(models.Model):
    """
    Modelo para registrar la evaluación general de un usuario sobre una Guía de Autocontrol.
    """
    ESTADO_CHOICES = [
        ('no_iniciada', 'No Iniciada'),
        ('en_progreso', 'En Progreso'),
        ('completada', 'Completada'),
        ('revisada', 'Revisada'),
    ]

    guia = models.ForeignKey(GuiaAutocontrol, on_delete=models.CASCADE, related_name='evaluaciones', verbose_name='Guía')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='evaluaciones_guias', verbose_name='Usuario')
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_completado = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='no_iniciada')
    porcentaje_cumplimiento = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name='Porcentaje de Cumplimiento')
    comentarios = models.TextField(blank=True, verbose_name='Observaciones Generales')

    class Meta:
        unique_together = ('guia', 'usuario')
        verbose_name = 'Evaluación de Guía'
        verbose_name_plural = 'Evaluaciones de Guías'
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f"Evaluación de {self.guia.titulo_guia} por {self.usuario.username}"

    def calcular_porcentaje_cumplimiento(self):
        """
        Calcula el porcentaje de cumplimiento basado en las respuestas del usuario.
        """
        #Descomentar para debug--> print(f"DEBUG: Entering EvaluacionGuia.calcular_porcentaje_cumplimiento for PK: {self.pk}")
        if not self.guia:
            #Descomentar para debug--> print(f"ERROR: EvaluacionGuia (PK: {self.pk}) tiene guia=None. No se puede calcular el cumplimiento.")
            self.porcentaje_cumplimiento = 0.00
            self.estado = 'no_iniciada'
            self.save() # Ensure save is called
            return
        print(f"DEBUG: EvaluacionGuia.guia is present: {self.guia.pk}")

        respuestas = RespuestaGuia.objects.filter(evaluacion=self)
        
        # Aplanar la lista de preguntas desde la estructura anidada de contenido_procesado
        all_preguntas_from_guia = []
        if self.guia.contenido_procesado and 'tablas_cuestionario' in self.guia.contenido_procesado:
            for categoria in self.guia.contenido_procesado['tablas_cuestionario']:
                for bloque in categoria.get('bloques', []):
                    for pregunta in bloque.get('preguntas', []):
                        all_preguntas_from_guia.append(pregunta)

        total_actual_preguntas = len(all_preguntas_from_guia)

        if total_actual_preguntas == 0:
            self.porcentaje_cumplimiento = 0.00
            self.estado = 'no_iniciada' # O 'en_progreso' si hay preguntas pero ninguna respondida
            self.save()
            return

        preguntas_respondidas = respuestas.filter(respuesta__in=['si', 'no', 'na']).count()
        
        porcentaje_completado = (preguntas_respondidas / total_actual_preguntas) * 100
        self.porcentaje_cumplimiento = round(porcentaje_completado, 2) # Redondear a 2 decimales
        self.estado = 'completada' if self.porcentaje_cumplimiento == 100 else 'en_progreso'
        self.save()

    def obtener_estadisticas_por_categoria(self):
        """
        Obtiene estadísticas de respuestas por categoría.
        """
        if not self.guia.contenido_procesado.get('tablas_cuestionario'):
            return {}

        estadisticas = {}
        for categoria in self.guia.contenido_procesado['tablas_cuestionario']:
            nombre_categoria = categoria['componente_a_evaluar']
            preguntas_categoria = []
            for bloque in categoria.get('bloques', []):
                preguntas_categoria.extend(bloque.get('preguntas', []))

            # Usar 'id' para los números de pregunta si es lo que usas en tu JSON
            numeros_preguntas = [p.get('id') for p in preguntas_categoria if p.get('id') is not None]
            respuestas_categoria = self.respuestas.filter(numero_pregunta__in=numeros_preguntas)

            total = respuestas_categoria.count()
            si_count = respuestas_categoria.filter(respuesta='si').count()
            no_count = respuestas_categoria.filter(respuesta='no').count()
            na_count = respuestas_categoria.filter(respuesta='na').count()

            estadisticas[nombre_categoria] = {
                'total': total,
                'si': si_count,
                'no': no_count,
                'na': na_count,
            }

        return estadisticas

class RespuestaGuia(models.Model):
    """
    Modelo para registrar la respuesta a una pregunta específica de una evaluación de Guía.
    """
    evaluacion = models.ForeignKey(EvaluacionGuia, on_delete=models.CASCADE, related_name='respuestas')
    numero_pregunta = models.IntegerField(verbose_name='Número de Pregunta')

    RESPUESTA_CHOICES = [
        ('si', 'Sí'),
        ('no', 'No'),
        ('na', 'No Aplica'),
        (None, 'Sin Responder')
    ]

    respuesta = models.CharField(
        max_length=3,
        choices=RESPUESTA_CHOICES,
        blank=True,
        null=True,
        verbose_name='Respuesta'
    )
    fundamentacion = models.TextField(blank=True, verbose_name='Fundamentación')
    fecha_respuesta = models.DateTimeField(auto_now=True, verbose_name='Fecha de Respuesta')

    class Meta:
        unique_together = ('evaluacion', 'numero_pregunta')
        verbose_name = 'Respuesta de Guía'
        ordering = ['evaluacion__guia__titulo_guia', 'numero_pregunta']
 
    def __str__(self):
        try:
            guia_title = "Guía Desconocida"
            usuario_username = "Usuario Desconocido"
            if hasattr(self, 'evaluacion') and self.evaluacion:
                if hasattr(self.evaluacion, 'guia') and self.evaluacion.guia:
                    guia_title = self.evaluacion.guia.titulo_guia
                if hasattr(self.evaluacion, 'usuario') and self.evaluacion.usuario:
                    usuario_username = self.evaluacion.usuario.username
            return f"Resp. a P{self.numero_pregunta} ({guia_title}) por {usuario_username}"
        except Exception as e:
            return f"Resp. a P{self.numero_pregunta} (Error al obtener info: {type(e).__name__})"
 
 
    def save(self, *args, **kwargs):
        #Descomentar para debug--> print(f"DEBUG: Entering RespuestaGuia.save for PK: {self.pk if self.pk else 'New'}, Evaluacion ID: {self.evaluacion.pk if self.evaluacion else 'None'}")
        super().save(*args, **kwargs)
        # Asegurarse de que la evaluación exista y sea válida antes de llamar acalcular_porcentaje_cumplimiento
        if self.evaluacion:
            #Descomentar para debug--> print(f"DEBUG: Calling calcular_porcentaje_cumplimiento for Evaluacion ID: {self.evaluacion.pk}")
            self.evaluacion.calcular_porcentaje_cumplimiento()
        else:
            print(f"WARNING: RespuestaGuia (PK: {self.pk if self.pk else 'New'})has no associated evaluation when saving. Skipping percentage calculation.")

 
