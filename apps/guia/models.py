"""Modelo para las Guías de Autocontrol con serialización JSON segura"""
from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
import re, json, logging
from docx import Document
from decimal import Decimal
from django.conf import settings
from apps.dashboard.models import Archivo

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

    # --- Utilidades de limpieza y serialización ---
    def _sanitizar_para_json(self, texto):
        """
        Sanitiza texto para asegurar compatibilidad con JSON.
        Elimina caracteres de control y normaliza espacios.
        """
        if not isinstance(texto, str):
            return str(texto)
        texto_limpio = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', texto)
        texto_limpio = re.sub(r'\s+', ' ', texto_limpio)
        try:
            texto_limpio = texto_limpio.encode('utf-8').decode('utf-8')
        except UnicodeEncodeError:
            texto_limpio = texto_limpio.encode('ascii', 'ignore').decode('ascii')
        return texto_limpio.strip()

    def _procesar_lista_para_json(self, lista):
        """
        Procesa una lista para asegurar compatibilidad JSON.
        """
        lista_procesada = []
        for item in lista:
            if isinstance(item, str):
                lista_procesada.append(self._sanitizar_para_json(item))
            elif isinstance(item, (int, float, bool)):
                lista_procesada.append(item)
            elif isinstance(item, dict):
                lista_procesada.append(self._procesar_dict_para_json(item))
            elif isinstance(item, list):
                lista_procesada.append(self._procesar_lista_para_json(item))
            elif item is None:
                lista_procesada.append(None)
            else:
                lista_procesada.append(self._sanitizar_para_json(str(item)))
        return lista_procesada

    def _procesar_dict_para_json(self, diccionario):
        """
        Procesa un diccionario para asegurar compatibilidad JSON.
        """
        diccionario_procesado = {}
        for k, v in diccionario.items():
            if isinstance(v, str):
                diccionario_procesado[k] = self._sanitizar_para_json(v)
            elif isinstance(v, (int, float, bool)):
                diccionario_procesado[k] = v
            elif isinstance(v, list):
                diccionario_procesado[k] = self._procesar_lista_para_json(v)
            elif isinstance(v, dict):
                diccionario_procesado[k] = self._procesar_dict_para_json(v)
            elif v is None:
                diccionario_procesado[k] = None
            else:
                diccionario_procesado[k] = self._sanitizar_para_json(str(v))
        return diccionario_procesado

    def _crear_contenido_procesado_seguro(self, error=None):
        """
        Helper para crear un diccionario seguro para contenido_procesado.
        """
        safe_content = {'error': error} if error else {}
        return safe_content

    def _clean_and_correct_text(self, text):
        """
        Limpieza básica y corrección de palabras.
        """
        text = re.sub(r'\n\s*\n', '\n', text)
        text = re.sub(r'\s([,\.!\?;:])', r'\1', text)
        text = re.sub(r'([([{])\s+', r'\1', text)
        text = re.sub(r'\s([)\]}])', r'\1', text)
        text = re.sub(r'(?<!•)\s+', ' ', text).strip()
        return text

    def _parsear_tabla_docx(self, path):
        def limpiar_texto(texto):
            if not texto:
                return ""
            texto = re.sub(r"\s+", " ", texto)
            texto = re.sub(r"\f|\n|Página \d+", "", texto)
            return texto.strip()

        doc = Document(path)
        tablas_cuestionario = []
        componente_actual = None
        dentro_tabla_cuestionario = False
        componentes_procesados = set()

        # Inicializa un contador para las preguntas
        contador_preguntas = 0

        for tabla in doc.tables:
            for fila in tabla.rows:
                celdas = [limpiar_texto(cell.text) if cell.text else "" for cell in fila.cells]

                print(f"Celdas: {celdas}")  # Impresión de depuración

                if not any(celdas):
                    print("Fila vacía, continuando...")
                    continue

                if any("ASPECTOS A VERIFICAR" in c.upper() for c in celdas if c):
                    dentro_tabla_cuestionario = True
                    print("Entrando a tabla de cuestionario")
                    continue

                if not dentro_tabla_cuestionario:
                    print("Fuera de tabla de cuestionario, continuando...")
                    continue

                if celdas and "Elaborado y aprobado" in celdas[0]:
                    print("Tabla 'Elaborado y aprobado' encontrada, terminando...")
                    break

                if len(celdas) >= 3 and len(set(c for c in celdas if c)) == 1:
                    componente_texto = limpiar_texto(celdas[0])
                    if componente_texto and componente_texto not in componentes_procesados:
                        componente_actual = {
                            "componente_a_evaluar": componente_texto,
                            "bloques": []
                        }
                        tablas_cuestionario.append(componente_actual)
                        componentes_procesados.add(componente_texto)
                        bloque = None
                        print(f"Componente detectado: {componente_texto}")
                        continue

                # Detectar encabezado
                encabezado_detectado = False
                for celda in celdas:
                    if celda and re.search(r":\s*$", celda):
                        encabezado_texto = limpiar_texto(celda)
                        if componente_actual:
                            bloque = {
                                "encabezado": encabezado_texto,
                                "preguntas": []
                            }
                            componente_actual["bloques"].append(bloque)
                            print(f"Encabezado detectado y añadido: {encabezado_texto}")
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
                            "id": contador_preguntas,  # Identificador único
                            "numero_pregunta": numero_pregunta,
                            "texto": texto_pregunta
                        })

        return tablas_cuestionario

    def extraer_contenido_archivo(self):
        """
        Extrae y procesa el contenido del archivo asociado (PDF/DOCX).
        Limpia y estructura componente, propósito y cuestionario.
        """
        import PyPDF2, mimetypes

        logger = logging.getLogger(__name__)

        if not self.archivo or not self.archivo.archivo:
            raise ValueError("No hay un archivo asociado a esta Guía de Autocontrol.")
        file_path = self.archivo.archivo.path
        mime, _ = mimetypes.guess_type(file_path)
        full_text = ""
        try:
            # --- Extracción de texto crudo ---
            if mime == 'application/pdf' or file_path.lower().endswith('.pdf'):
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            full_text += page_text + "\n"
                tablas_cuestionario = self._parsear_tabla_pdf(file_path)
            elif mime == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' or file_path.lower().endswith('.docx'):
                doc = Document(file_path)
                for para in doc.paragraphs:
                    full_text += para.text + "\n"
                for table in doc.tables:
                    for row in table.rows:
                        row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                        if row_text:
                            full_text += " | ".join(row_text) + "\n"
                tablas_cuestionario = self._parsear_tabla_docx(file_path)
            else:
                raise ValueError("Tipo de archivo no soportado para extracción automática.")

            # --- Procesamiento del texto extraído ---
            # 1. Extraer Componente y Propósito
            comp_match = re.search(r'COMPONENTE\s+«?([A-ZÁÉÍÓÚÜÑ\s]+)»?', full_text, re.IGNORECASE)
            self.componente = comp_match.group(1).strip() if comp_match else ""

            # Extraer propósito
            text_content = re.sub(r'\n\d+\s*$', '', full_text, flags=re.MULTILINE)
            prop_match = re.search(r'Propósito:\s*([\s\S]*?)(?=Principales fuentes de información para el autocontrol|$)', text_content, re.IGNORECASE)
            if prop_match:
                proposito = prop_match.group(1).strip()
                # Eliminar saltos de línea dentro de las oraciones
                proposito = re.sub(r'(?<![.!?])\n(?!\n)', ' ', proposito)
                proposito = re.sub(r'\s{2,}', ' ', proposito)
                proposito = re.sub(r'\n\s*\n', '\n', proposito)
                proposito = re.sub(r'(\s*\.\s*)+', '. ', proposito)
                proposito = proposito.replace('•', '')
                lineas = [l.strip() for l in proposito.split('\n') if l.strip() and not re.fullmatch(r'\d+', l.strip())]
                parrafos, encabezados, puntos = [], [], []
                buffer = ''
                for line in lineas:
                    line = re.sub(r'^[0-9]+[\s\.-·]*', '', line)
                    if re.match(r'^[A-ZÁÉÍÓÚÜÑ\s]+:$', line):
                        encabezados.append(line)
                    elif re.match(r'^(-|\*|•|·|[a-zA-Z]\))', line) or line.startswith(''):
                        puntos.append(line)
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

            # 3. Guardar resultados estructurados
            self.contenido_procesado = {
                "componente": self.componente,
                "proposito": self.proposito,
                "tablas_cuestionario": tablas_cuestionario if tablas_cuestionario else []
            }
            print(f"[DEBUG] Contenido procesado: {json.dumps(self.contenido_procesado, indent=2)}")
            self.save()
        except Exception as e:
            logger.error(f"Error al extraer contenido del archivo {self.archivo.nombre}: {e}")
            raise

    @staticmethod
    def imprimir_archivo_docx(ruta_archivo):
        doc = Document(ruta_archivo)
        for para in doc.paragraphs:
            print(para.text)


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
        Calcula el porcentaje de preguntas respondidas para esta evaluación.
        Asume que las respuestas están vinculadas a esta evaluación.
        """
        # Get all questions from the guide's processed content
        all_questions_flat = []
        if self.guia.contenido_procesado and 'tablas_cuestionario' in self.guia.contenido_procesado:
            for categoria in self.guia.contenido_procesado['tablas_cuestionario']:
                for bloque in categoria.get('bloques', []):
                    all_questions_flat.extend(bloque.get('preguntas', []))
        total_preguntas = len(all_questions_flat)
        if total_preguntas == 0:
            self.porcentaje_cumplimiento = Decimal('0.00')
            self.estado = 'no_iniciada'
            self.save()
            return Decimal('0.00')
        answered_count = self.respuestas.filter(
            respuesta__in=['si', 'no', 'na']
        ).count()
        porcentaje = (Decimal(answered_count) / Decimal(total_preguntas)) * Decimal('100.00')
        self.porcentaje_cumplimiento = round(porcentaje, 2)
        if self.porcentaje_cumplimiento == 100 and self.estado != 'completada':
            self.estado = 'completada'
            self.fecha_completado = timezone.now()
        elif self.porcentaje_cumplimiento < 100 and self.estado != 'en_progreso':
            self.estado = 'en_progreso'
            self.fecha_completado = None
        elif self.porcentaje_cumplimiento == 0 and self.estado != 'no_iniciada':
            self.estado = 'no_iniciada'
            self.fecha_completado = None
        self.save()
        return self.porcentaje_cumplimiento

    def obtener_estadisticas_por_categoria(self):
        """
        Obtiene estadísticas de respuestas por categoría.
        """
        if not self.guia.contenido_procesado.get('tablas_cuestionario'):
            return {}
        estadisticas = {}
        for categoria in self.guia.contenido_procesado['tablas_cuestionario']:
            nombre_categoria = categoria['categoria']
            preguntas_categoria = []
            for bloque in categoria.get('bloques', []):
                preguntas_categoria.extend(bloque.get('preguntas', []))
            numeros_preguntas = [p.get('numero_pregunta') for p in preguntas_categoria]
            respuestas_categoria = self.respuestas.filter(
                numero_pregunta__in=numeros_preguntas
            )
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
        verbose_name_plural = 'Respuestas de Guías'
        ordering = ['evaluacion__guia__titulo_guia', 'numero_pregunta']

    def __str__(self):
        return f"Resp. a P{self.numero_pregunta} ({self.evaluacion.guia.titulo_guia}) por {self.evaluacion.usuario.username}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Recalcula el porcentaje para la evaluación asociada después de guardar la respuesta
        self.evaluacion.calcular_porcentaje_cumplimiento()