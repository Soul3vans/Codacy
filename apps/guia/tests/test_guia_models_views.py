import os
import django
import json
from unittest.mock import patch, MagicMock
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'infoweb.settings')
django.setup()
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.guia.models import GuiaAutocontrol, EvaluacionGuia, RespuestaGuia
from apps.dashboard.models import Archivo

User = get_user_model()


class GuiaAutocontrolModelTest(TestCase):
    """
    Pruebas para el modelo GuiaAutocontrol.
    """
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        # Usar SimpleUploadedFile para simular el archivo correctamente
        archivo_en_memoria = SimpleUploadedFile('test_guia.docx', b'data')

        # Se crea el objeto Archivo con el archivo en memoria.
        self.archivo = Archivo.objects.create(
            nombre='Test Guia',
            archivo=archivo_en_memoria,
            tipo='documento',
            subido_por=self.user,
            es_formulario=True
        )
        
        # La señal debería haber creado el objeto GuiaAutocontrol, lo obtenemos.
        self.guia = GuiaAutocontrol.objects.get(archivo=self.archivo)
        
        # Configuramos el contenido procesado para el test
        self.guia.contenido_procesado = {
            'tablas_cuestionario': [
                {
                    'componente_a_evaluar': 'Componente A',
                    'bloques': [{'preguntas': [{'numero_pregunta': 1, 'texto': 'P1?'}, {'numero_pregunta': 2, 'texto': 'P2?'}]}]
                },
                {
                    'componente_a_evaluar': 'Componente B',
                    'bloques': [{'preguntas': [{'numero_pregunta': 3, 'texto': 'P3?'}]}]
                }
            ]
        }
        self.guia.save()

    def test_str(self):
        """Verifica la representación en string del modelo."""
        self.assertIn('Guía', str(self.guia))

    @patch('apps.guia.models.GuiaAutocontrol.calcular_hash_archivo')
    def test_save_calcula_hash(self, mock_calcular_hash):
        """Verifica que el hash del archivo se calcula al guardar."""
        mock_calcular_hash.return_value = 'fake_hash'
        guia_con_hash = GuiaAutocontrol.objects.get(pk=self.guia.pk)
        guia_con_hash.save()
        self.assertEqual(guia_con_hash.hash_archivo, 'fake_hash')
        mock_calcular_hash.assert_called_once()
        
    def test_save_calcula_campos_denormalizados(self):
        """Verifica que total_preguntas y categorias_count se calculan correctamente."""
        self.assertEqual(self.guia.total_preguntas, 3)
        self.assertEqual(self.guia.categorias_count, 2)

    def test_get_absolute_url(self):
        """Verifica la URL absoluta del modelo."""
        url = self.guia.get_absolute_url()
        self.assertEqual(url, reverse('guia:detalle', kwargs={'pk': self.guia.pk}))

    def test_generar_resumen_evaluacion(self):
        """Verifica que el resumen de evaluación se genera correctamente."""
        RespuestaGuia.objects.create(guia=self.guia, usuario=self.user, numero_pregunta=1, respuesta='si')
        RespuestaGuia.objects.create(guia=self.guia, usuario=self.user, numero_pregunta=3, respuesta='no')
        
        resumen = self.guia.generar_resumen_evaluacion(self.user.pk)
        
        self.assertEqual(resumen['total_preguntas'], 3)
        self.assertEqual(resumen['respondidas'], 2)
        self.assertAlmostEqual(resumen['porcentaje'], 66.67)
        self.assertEqual(resumen['por_componente']['Componente A']['respondidas'], 1)
        self.assertAlmostEqual(resumen['por_componente']['Componente A']['porcentaje'], 50.0)
        self.assertEqual(resumen['por_componente']['Componente B']['respondidas'], 1)
        self.assertAlmostEqual(resumen['por_componente']['Componente B']['porcentaje'], 100.0)


class EvaluacionGuiaModelTest(TestCase):
    """
    Pruebas para el modelo EvaluacionGuia.
    """
    def setUp(self):
        self.user = User.objects.create_user(username='evaluser', password='evalpass')
        
        # Reemplazar MagicMock con SimpleUploadedFile
        archivo_en_memoria = SimpleUploadedFile('test_guia_eval.docx', b'datos de prueba')
        
        self.archivo = Archivo.objects.create(
            nombre='Test Guia Eval',
            archivo=archivo_en_memoria,
            tipo='documento',
            subido_por=self.user,
            es_formulario=True
        )
        self.guia = GuiaAutocontrol.objects.get(archivo=self.archivo)
        self.guia.contenido_procesado = {
            'tablas_cuestionario': [
                {'bloques': [{'preguntas': [{'numero_pregunta': 1}, {'numero_pregunta': 2}]}]}
            ]
        }
        self.guia.save()
        self.evaluacion = EvaluacionGuia.objects.create(guia=self.guia, usuario=self.user)

    def test_actualizar_estadisticas_en_progreso(self):
        """Verifica que las estadísticas se actualizan correctamente para un estado 'en_progreso'."""
        RespuestaGuia.objects.create(guia=self.guia, usuario=self.user, numero_pregunta=1, respuesta='si')
        self.evaluacion.actualizar_estadisticas()
        
        self.assertEqual(self.evaluacion.total_respuestas, 1)
        self.assertEqual(self.evaluacion.respuestas_si, 1)
        self.assertEqual(self.evaluacion.respuestas_no, 0)
        self.assertAlmostEqual(self.evaluacion.porcentaje_cumplimiento, 50.00)
        self.assertEqual(self.evaluacion.estado, 'en_progreso')

    def test_actualizar_estadisticas_completada(self):
        """Verifica que la evaluación se marca como 'completada' al responder todas las preguntas."""
        RespuestaGuia.objects.create(guia=self.guia, usuario=self.user, numero_pregunta=1, respuesta='si')
        RespuestaGuia.objects.create(guia=self.guia, usuario=self.user, numero_pregunta=2, respuesta='no')
        self.evaluacion.actualizar_estadisticas()
        
        self.assertEqual(self.evaluacion.total_respuestas, 2)
        self.assertEqual(self.evaluacion.respuestas_si, 1)
        self.assertEqual(self.evaluacion.respuestas_no, 1)
        self.assertAlmostEqual(self.evaluacion.porcentaje_cumplimiento, 100.00)
        self.assertEqual(self.evaluacion.estado, 'completada')
        self.assertIsNotNone(self.evaluacion.fecha_completado)

    def test_actualizar_respuestas_json(self):
        """Verifica que el campo respuestas_json se actualiza correctamente."""
        RespuestaGuia.objects.create(guia=self.guia, usuario=self.user, numero_pregunta=1, respuesta='si', fundamentacion='test')
        self.evaluacion.actualizar_respuestas_json()

        resp_json = self.evaluacion.respuestas_json
        self.assertIn('tabla_respuestas', resp_json)
        self.assertEqual(resp_json['tabla_respuestas'][0]['respuestas_guias'][0]['numero_pregunta'], 1)
        self.assertEqual(resp_json['tabla_respuestas'][0]['respuestas_guias'][0]['respuesta'], 'si')
        self.assertEqual(resp_json['tabla_respuestas'][0]['respuestas_guias'][0]['fundamentacion'], 'test')


@patch('apps.guia.models.GuiaAutocontrol.calcular_hash_archivo', return_value='fake_hash')
class GuiaViewsTest(TestCase):
    """
    Pruebas para las vistas de la aplicación guia.
    """
    def setUp(self, mock_calcular_hash):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        
        # Simula los archivos necesarios
        archivo_en_memoria_1 = SimpleUploadedFile('file1.docx', b'data1')
        self.archivo1 = Archivo.objects.create(
            nombre='Guia 1', 
            es_formulario=True, 
            archivo=archivo_en_memoria_1,
            subido_por=self.user
        )

        archivo_en_memoria_2 = SimpleUploadedFile('file2.docx', b'data2')
        self.archivo2 = Archivo.objects.create(
            nombre='Guia 2', 
            es_formulario=True, 
            archivo=archivo_en_memoria_2,
            subido_por=self.user
        )

        archivo_en_memoria_3 = SimpleUploadedFile('file3.docx', b'data3')
        self.archivo3 = Archivo.objects.create(
            nombre='Guia 3', 
            es_formulario=True, 
            archivo=archivo_en_memoria_3,
            subido_por=self.user
        )

        # OBTIENE las guías que ya fueron creadas por el signal
        self.guia1 = GuiaAutocontrol.objects.get(archivo=self.archivo1)
        self.guia2 = GuiaAutocontrol.objects.get(archivo=self.archivo2)
        self.guia3 = GuiaAutocontrol.objects.get(archivo=self.archivo3)

        # Actualiza los campos de las guías para la prueba
        self.guia1.titulo_guia = 'Guia Completada'
        self.guia1.activa = True
        self.guia1.total_preguntas = 1
        self.guia1.contenido_procesado = {'tablas_cuestionario': [{'bloques': [{'preguntas': [{'numero_pregunta': 1, 'texto': 'P1?'}]}]}]}
        self.guia1.save()

        self.guia2.titulo_guia = 'Guia En Progreso'
        self.guia2.activa = True
        self.guia2.total_preguntas = 2
        self.guia2.contenido_procesado = {'tablas_cuestionario': [{'bloques': [{'preguntas': [{'numero_pregunta': 1, 'texto': 'P1?'}, {'numero_pregunta': 2, 'texto': 'P2?'}]}]}]}
        self.guia2.save()

        self.guia3.titulo_guia = 'Guia Pendiente'
        self.guia3.activa = True
        self.guia3.total_preguntas = 10
        self.guia3.contenido_procesado = {'tablas_cuestionario': [{'bloques': [{'preguntas': [{} for _ in range(10)]}]}]}
        self.guia3.save()
        
        # Crea las evaluaciones con los estados deseados
        self.eval_completada = EvaluacionGuia.objects.create(
            guia=self.guia1,
            usuario=self.user,
            estado='completada',
            porcentaje_cumplimiento=100
        )
        RespuestaGuia.objects.create(guia=self.guia1, usuario=self.user, numero_pregunta=1, respuesta='si')

        self.eval_en_progreso = EvaluacionGuia.objects.create(
            guia=self.guia2,
            usuario=self.user,
            estado='en_progreso',
            porcentaje_cumplimiento=50
        )
        RespuestaGuia.objects.create(guia=self.guia2, usuario=self.user, numero_pregunta=1, respuesta='si')

        # URLs de las vistas
        self.url_lista = reverse('guia:lista')

    def test_guia_list_view_context(self, mock_calcular_hash):
        """
        Verifica que la vista de lista de guías clasifique correctamente las guías
        sin depender de la creación de archivos.
        """
        response = self.client.get(self.url_lista)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'guia/lista_guias.html')

        context = response.context
        self.assertEqual(context['total_guias'], 3)
        self.assertEqual(context['total_completadas'], 1)
        self.assertEqual(context['total_en_progreso'], 1)
        self.assertEqual(context['total_pendientes'], 1)
        
        completadas = context['guias_completadas']
        en_progreso = context['guias_en_progreso']
        pendientes = context['guias_pendientes']

        self.assertIn(self.guia1, completadas)
        self.assertIn(self.guia2, en_progreso)
        self.assertIn(self.guia3, pendientes)
        
        guias_ordenadas = list(context['guias'])
        self.assertIn(self.guia1, guias_ordenadas[-1:])
        self.assertIn(self.guia2, guias_ordenadas[:-1])
        self.assertIn(self.guia3, guias_ordenadas[:-1])

    def test_detalle_guia_get(self, mock_calcular_hash):
        """Verifica que la vista de detalle GET muestre la información correcta."""
        url = reverse('guia:detalle', kwargs={'pk': self.guia1.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'guia/detalle_guia.html')
        
        context = response.context
        self.assertEqual(context['guia'].pk, self.guia1.pk)
        self.assertEqual(context['porcentaje_completado'], 100)
        self.assertEqual(context['preguntas_respondidas'], 1)
        self.assertEqual(context['total_preguntas'], 1)

    def test_detalle_guia_post_save_response(self, mock_calcular_hash):
        """Verifica que la vista de detalle POST guarde una respuesta y devuelva el JSON correcto."""
        url = reverse('guia:detalle', kwargs={'pk': self.guia2.pk})
        data = {
            'numero_pregunta': 2,
            'respuesta': 'si',
            'fundamentacion': 'Fundamentacion de prueba'
        }
        response = self.client.post(url, json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        json_response = response.json()
        self.assertEqual(json_response['status'], 'success')
        self.assertAlmostEqual(json_response['porcentaje_completado'], 100)
        self.assertEqual(json_response['preguntas_respondidas'], 2)
        self.assertEqual(json_response['total_preguntas'], 2)
        
        self.eval_en_progreso.refresh_from_db()
        self.assertEqual(self.eval_en_progreso.estado, 'completada')
        self.assertEqual(self.eval_en_progreso.porcentaje_cumplimiento, 100)

    def test_completar_evaluacion_success(self, mock_calcular_hash):
        """Verifica que se pueda completar una evaluación cuando todas las preguntas están respondidas."""
        url = reverse('guia:completar_evaluacion', kwargs={'guia_pk': self.guia1.pk})
        response = self.client.post(url)
        self.assertRedirects(response, reverse('guia:resumen_evaluacion', kwargs={'pk': self.eval_completada.pk}))
        
        self.eval_completada.refresh_from_db()
        self.assertEqual(self.eval_completada.estado, 'completada')

    def test_completar_evaluacion_incomplete(self, mock_calcular_hash):
        """Verifica que no se pueda completar una evaluación si faltan preguntas."""
        url = reverse('guia:completar_evaluacion', kwargs={'guia_pk': self.guia2.pk})
        response = self.client.post(url)
        self.assertRedirects(response, reverse('guia:detalle', kwargs={'pk': self.guia2.pk}))
        
        self.eval_en_progreso.refresh_from_db()
        self.assertEqual(self.eval_en_progreso.estado, 'en_progreso')
        self.assertIn('Faltan', [str(m) for m in response.context['messages']])

    def test_resumen_evaluacion_view(self, mock_calcular_hash):
        """Verifica que la vista de resumen de evaluación muestre las estadísticas correctas."""
        url = reverse('guia:resumen_evaluacion', kwargs={'pk': self.eval_completada.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'guia/resumen_evaluacion.html')
        
        context = response.context
        self.assertEqual(context['evaluacion'].pk, self.eval_completada.pk)
        self.assertEqual(context['total_si'], 1)
        self.assertEqual(context['total_no'], 0)
        self.assertEqual(context['total_na'], 0)

    @patch('apps.guia.views.generar_pdf_guia_async')
    def test_generar_pdf_guia_async_view(self, mock_task, mock_calcular_hash):
        """
        Verifica que la vista asíncrona para generar PDF devuelva el JSON correcto.
        """
        mock_task_instance = MagicMock()
        mock_task_instance.id = 'fake-task-id'
        mock_task.delay.return_value = mock_task_instance

        url = reverse('guia:generar_pdf_guia_async', kwargs={'pk': self.guia1.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        json_response = response.json()

        self.assertEqual(json_response['status'], 'processing')
        self.assertEqual(json_response['task_id'], 'fake-task-id')
        self.assertIn(f'/media/pdfs_temp/guia_{self.guia1.pk}_user_{self.user.pk}.pdf', json_response['download_url'])
        mock_task.delay.assert_called_once()


class GuiaSignalsTest(TestCase):
    """
    Pruebas para los signals de la aplicación guia.
    """
    def setUp(self):
        self.user = User.objects.create_user(username='signaluser', password='signalpass')
        self.client = Client()
        self.client.login(username='signaluser', password='signalpass')

    def test_signal_crear_guia_autocontrol(self):
        """Verifica que un archivo con es_formulario=True cree una GuiaAutocontrol."""
        # Se utiliza SimpleUploadedFile para simular un archivo en memoria
        archivo_en_memoria = SimpleUploadedFile('form_signal.docx', b'data')
        Archivo.objects.create(
            nombre='Archivo Formulario Signal',
            archivo=archivo_en_memoria,
            tipo='documento',
            subido_por=self.user,
            es_formulario=True
        )
        self.assertTrue(GuiaAutocontrol.objects.filter(archivo__nombre='Archivo Formulario Signal').exists())

    def test_signal_no_crea_guia_si_no_es_formulario(self):
        """Verifica que no se cree una GuiaAutocontrol si el archivo no es un formulario."""
        Archivo.objects.create(
            nombre='Archivo No Formulario',
            archivo=SimpleUploadedFile('no_form.pdf', b'data'),
            tipo='documento',
            subido_por=self.user,
            es_formulario=False
        )
        self.assertFalse(GuiaAutocontrol.objects.filter(archivo__nombre='Archivo No Formulario').exists())