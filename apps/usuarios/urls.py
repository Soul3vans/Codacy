from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # URLs de autenticación de Django
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # URLs de registro y perfil
    path('registro/', views.registro, name='registro'),
    path('perfil/', views.perfil, name='perfil'),

    # URLs de administración
    path('admin_panel/', views.panel_admin, name='panel_admin'),
    path('cambiar_rol/<int:user_id>/', views.cambiar_rol, name='cambiar_rol'),
]