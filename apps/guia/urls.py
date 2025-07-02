from django.urls import path
from . import views

app_name = 'guia'

urlpatterns = [
    # Lista de guías disponibles
    path('', views.GuiaListView.as_view(), name='lista'),
    # Detalle de una guía específica con formulario
    path('guia/<int:pk>/', views.detalle_guia, name='detalle'),
    path('guardar_respuesta/<int:guia_pk>/', views.guardar_respuesta, name='guardar_respuesta'),
    # Completar evaluación
    path('guia/<int:guia_pk>/completar/', views.completar_evaluacion, name='completar_evaluacion'),
    # Resumen de evaluación
    path('evaluacion/<int:pk>/resumen/', views.resumen_evaluacion, name='resumen_evaluacion'),
    # Mis evaluaciones
    path('mis-evaluaciones/', views.mis_evaluaciones, name='mis_evaluaciones'),
    # Procesar archivo para crear guía
    path('archivo/procesar-archivo/<int:archivo_id>/', views.procesar_archivo_guia, name='procesar_archivo'),
    # Nueva URL para la vista archivo_guia_view
    path('archivos/', views.archivo_guia_view, name='archivo_guia'),
    # Generar PDF
    path('guia/<int:pk>/generar_pdf/', views.generar_pdf_guia, name='generar_pdf_guia'), # <-- Nueva URL
]