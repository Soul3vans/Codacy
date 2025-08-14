import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'infoweb.settings')
django.setup()
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.guia.models import GuiaAutocontrol
from apps.dashboard.models import Archivo
from django.test import Client

User = get_user_model()

class GuiaAutocontrolModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.archivo = Archivo.objects.create(
            nombre='Test Guia',
            archivo=SimpleUploadedFile('test.docx', b'data'),
            tipo='documento',
            subido_por=self.user,
            es_formulario=True
        )

    def test_str(self):
        guia = GuiaAutocontrol.objects.create(archivo=self.archivo)
        self.assertIn('Guía', str(guia))

    def test_save_calcula_hash(self):
        guia = GuiaAutocontrol.objects.create(archivo=self.archivo)
        self.assertTrue(guia.hash_archivo)

    def test_get_absolute_url(self):
        guia = GuiaAutocontrol.objects.create(archivo=self.archivo)
        url = guia.get_absolute_url()
        self.assertTrue(url.startswith('/'))

class GuiaViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.archivo = Archivo.objects.create(
            nombre='Test Guia',
            archivo=SimpleUploadedFile('test.docx', b'data'),
            tipo='documento',
            subido_por=self.user,
            es_formulario=True
        )
        self.guia = GuiaAutocontrol.objects.create(archivo=self.archivo)
        self.client = Client()
        self.client.login(username='testuser', password='testpass')

    def test_guia_list_view(self):
        url = reverse('guia:lista')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'guia/lista_guias.html')
        self.assertIn('guias', response.context)

class GuiaSignalsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='signaluser', password='signalpass')
        self.archivo = Archivo.objects.create(
            nombre='Archivo Formulario',
            archivo=SimpleUploadedFile('form.docx', b'data'),
            tipo='documento',
            subido_por=self.user,
            es_formulario=True
        )

    def test_signal_crear_guia_autocontrol(self):
        # Simula la creación de un archivo con es_formulario=True
        # El signal de dashboard debería crear GuiaAutocontrol automáticamente
        self.assertTrue(GuiaAutocontrol.objects.filter(archivo=self.archivo).exists())

# Puedes agregar más tests para métodos de procesamiento y API de GuiaAutocontrol si lo necesitas.
