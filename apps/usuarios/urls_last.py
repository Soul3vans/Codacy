from django.urls import path
from . import views

urlpatterns = [
    path('registro/', views.registro, name='registro'),
    path('perfil/', views.perfil, name='perfil'),

    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    
    path('panel-admin/', views.panel_admin, name='panel_admin'),
    path('cambiar-rol/<int:user_id>/', views.cambiar_rol, name='cambiar_rol'),
]