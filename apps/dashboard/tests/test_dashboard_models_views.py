import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'infoweb.settings')
django.setup()
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from ..models import Archivo, EnlaceInteres
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.signals import post_save
from django.dispatch import Signal
from apps.dashboard import signals as dashboard_signals

class DashboardViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.user.is_active = True
        self.user.save()
        self.client.login(username='testuser', password='testpass')

    def test_inicio_view(self):
        url = reverse('inicio')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/index.html')

    def test_gestionar_archivos_requires_permission(self):
        url = reverse('gestionar_archivos')
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 200)  # No tiene permisos por defecto

    def test_archivo_model_str(self):
        archivo = Archivo.objects.create(
            nombre='Test Archivo',
            archivo=SimpleUploadedFile('test.txt', b'contenido'),
            tipo='documento',
            subido_por=self.user
        )
        self.assertEqual(str(archivo), 'Test Archivo')

    def test_enlaceinteres_model_str(self):
        enlace = EnlaceInteres.objects.create(
            titulo='Test Enlace',
            url='https://example.com',
            creado_por=self.user
        )
        self.assertEqual(str(enlace), 'Test Enlace')

class DashboardSignalsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='signaluser', password='signalpass')

    def test_crear_guia_desde_archivo_signal(self):
        # Simula la creación de un archivo con es_formulario=True
        archivo = Archivo.objects.create(
            nombre='Archivo Formulario',
            archivo=SimpleUploadedFile('test.docx', b'data'),
            tipo='documento',
            subido_por=self.user,
            es_formulario=True
        )
        # El signal debería ejecutarse automáticamente. Si tienes efectos secundarios, verifica aquí.
        # Por ejemplo, si GuiaAutocontrol se crea, deberías importarlo y comprobarlo.
        # from apps.guia.models import GuiaAutocontrol
        # self.assertTrue(GuiaAutocontrol.objects.filter(archivo=archivo).exists())
        self.assertTrue(archivo.es_formulario)

    def test_signal_not_triggered_without_es_formulario(self):
        archivo = Archivo.objects.create(
            nombre='Archivo Normal',
            archivo=SimpleUploadedFile('normal.txt', b'data'),
            tipo='documento',
            subido_por=self.user,
            es_formulario=False
        )
        self.assertFalse(archivo.es_formulario)

# Puedes agregar más tests para editar/eliminar archivos y enlaces, y para AJAX si lo necesitas.
