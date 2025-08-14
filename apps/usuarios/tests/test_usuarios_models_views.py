import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'infoweb.settings')
django.setup()
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone

class PerfilModelTest(TestCase):
    def test_creacion_perfil(self):
        user = User.objects.create_user(username='testuser1', password='12345')
        perfil = user.perfil  # Perfil creado automáticamente por la señal
        perfil.telefono = '123456789'
        perfil.save()
        self.assertEqual(perfil.telefono, '123456789')
        self.assertEqual(perfil.user.username, 'testuser1')

    def test_nombre_completo(self):
        user = User.objects.create_user(username='testuser2', password='12345', first_name='Juan', last_name='Pérez')
        perfil = user.perfil  # Perfil creado automáticamente
        self.assertEqual(perfil.nombre_completo, 'Juan Pérez')

    def test_es_online(self):
        user = User.objects.create_user(username='testuser3', password='12345')
        perfil = user.perfil
        perfil.last_activity = timezone.now()
        perfil.save()
        self.assertTrue(perfil.es_online())

class PerfilViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.perfil = self.user.perfil  # Usar el perfil creado automáticamente
        self.perfil.telefono = '123456789'
        self.perfil.save()

    def test_perfil_view_requires_login(self):
        response = self.client.get(reverse('perfil'))
        self.assertEqual(response.status_code, 302)  # Redirige a login

    def test_perfil_view_logged_in(self):
        self.client.login(username='testuser', password='12345')
        response = self.client.get(reverse('perfil'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')

    def test_cambiar_password_view(self):
        self.client.login(username='testuser', password='12345')
        response = self.client.post(reverse('cambiar_password'), {
            'old_password': '12345',
            'new_password1': 'nuevaClave123',
            'new_password2': 'nuevaClave123',
        })
        self.assertEqual(response.status_code, 302)  # Redirige a perfil
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('nuevaClave123'))

    def test_actualizar_perfil_view(self):
        self.client.login(username='testuser', password='12345')
        response = self.client.post(reverse('editar_perfil'), {
            'first_name': 'NuevoNombre',
            'last_name': 'NuevoApellido',
            'email': 'nuevo@email.com',
            'telefono': '555555',
            'cede': 1,
            'cargo': 'Nuevo Cargo',
            'recibir_notificaciones': True,
        })
        if response.status_code == 400:
            # Imprime errores de formulario para depuración
            print('user_form errors:', getattr(response.context.get('user_form'), 'errors', None))
            print('profile_form errors:', getattr(response.context.get('profile_form'), 'errors', None))
            print('content:', response.content.decode())
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'NuevoNombre')
        self.assertEqual(self.user.email, 'nuevo@email.com')
