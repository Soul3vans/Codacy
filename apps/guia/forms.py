"""FORMULARIOS"""
from django import forms
from .models import RespuestaGuia, EvaluacionGuia

# Constantes para opciones de respuesta
OPCIONES_RESPUESTA = [
    ('si', 'Sí'),
    ('no', 'No'),
    ('na', 'No Aplica'),
]

# Constantes para opciones de estado
ESTADO_CHOICES = [
    ('', 'Todos los estados'),
    ('en_progreso', 'En Progreso'),
    ('completada', 'Completada'),
    ('revisada', 'Revisada'),
    ('aprobada', 'Aprobada'),
]

class RespuestaGuiaForm(forms.ModelForm):
    """
    Formulario para responder preguntas de la guía.
    """
    class Meta:
        model = RespuestaGuia
        fields = ['respuesta', 'fundamentacion']
        widgets = {
            'respuesta': forms.RadioSelect(attrs={
                'class': 'form-check-input'
            }),
            'fundamentacion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Escriba aquí la fundamentación de su respuesta...'
            })
        }

    def clean(self):
        cleaned_data = super().clean()
        respuesta = cleaned_data.get('respuesta')
        fundamentacion = cleaned_data.get('fundamentacion')

        # Ejemplo de validación personalizada
        if respuesta == 'no' and not fundamentacion:
            raise forms.ValidationError("La fundamentación es obligatoria cuando la respuesta es 'No'.")

        return cleaned_data

class EvaluacionGuiaForm(forms.ModelForm):
    """
    Formulario para completar la evaluación.
    """
    class Meta:
        model = EvaluacionGuia
        fields = ['comentarios']
        widgets = {
            'comentarios': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Escriba aquí sus observaciones generales sobre la evaluación...'
            })
        }

class BusquedaGuiaForm(forms.Form):
    """
    Formulario para buscar guías.
    """
    busqueda = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por nombre o componente...'
        })
    )
    componente = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filtrar por componente...'
        })
    )

class FiltroEvaluacionForm(forms.Form):
    """
    Formulario para filtrar evaluaciones.
    """
    estado = forms.ChoiceField(
        choices=ESTADO_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    fecha_desde = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    fecha_hasta = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

class RespuestaRapidaForm(forms.Form):
    """
    Formulario para respuesta rápida por AJAX.
    """
    numero_pregunta = forms.IntegerField(widget=forms.HiddenInput())
    fundamentacion = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Fundamentación (opcional)'
        })
    )
    respuesta = forms.ChoiceField(
        choices=OPCIONES_RESPUESTA,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input respuesta-radio'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        respuesta = cleaned_data.get('respuesta')
        fundamentacion = cleaned_data.get('fundamentacion')

        # Ejemplo de validación personalizada
        if respuesta == 'no' and not fundamentacion:
            raise forms.ValidationError("La fundamentación es obligatoria cuando la respuesta es 'No'.")

        return cleaned_data
