from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Field, Div
from .models import Post, Comentario, Archivo

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = [
            'titulo', 'resumen', 'contenido', 
            'imagen_destacada', 'estado', 'destacado', 'permitir_comentarios'
        ]
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título del post'}),
            'resumen': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Breve descripción...'}),
            'contenido': forms.Textarea(attrs={'class': 'form-control', 'rows': 10, 'placeholder': 'Contenido del post...'}),
            'imagen_destacada': forms.FileInput(attrs={'class': 'form-control-file'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'destacado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'permitir_comentarios': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'titulo': 'Título',
            'categoria': 'Categoría',
            'resumen': 'Resumen',
            'contenido': 'Contenido',
            'imagen_destacada': 'Imagen destacada',
            'estado': 'Estado',
            'destacado': 'Post destacado',
            'permitir_comentarios': 'Permitir comentarios',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.add_input(Submit('submit', 'Guardar Post', css_class='btn btn-primary'))
        
        # Mejorar el layout
        self.helper.layout = Layout(
            Div(
                Field('titulo'),
                Field('categoria'),
                css_class='row'
            ),
            Field('resumen'),
            Field('contenido'),
            Div(
                Field('imagen_destacada'),
                Field('estado'),
                css_class='row'
            ),
            Div(
                Field('destacado'),
                Field('permitir_comentarios'),
                css_class='row'
            ),
        )

class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ['contenido']
        widgets = {
            'contenido': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Escribe tu comentario aquí...',
                'maxlength': 500
            }),
        }
        labels = {
            'contenido': 'Comentario',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Publicar Comentario', css_class='btn btn-primary btn-sm'))

class ArchivoForm(forms.ModelForm):
    class Meta:
        model = Archivo
        fields = ['nombre', 'archivo', 'tipo', 'descripcion', 'publico']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del archivo'}),
            'archivo': forms.FileInput(attrs={'class': 'form-control-file'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción opcional...'}),
            'publico': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'nombre': 'Nombre',
            'archivo': 'Archivo',
            'tipo': 'Tipo de archivo',
            'descripcion': 'Descripción',
            'publico': 'Archivo público',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.add_input(Submit('submit', 'Subir Archivo', css_class='btn btn-success'))

class BusquedaForm(forms.Form):
    q = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar posts...',
        }),
        label='',
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_class = 'form-inline'
        self.helper.field_template = 'bootstrap4/layout/inline_field.html'
        self.helper.layout = Layout(
            Field('q', css_class='mr-2'),
            Field('categoria', css_class='mr-2'),
            Submit('submit', 'Buscar', css_class='btn btn-outline-primary')
        )