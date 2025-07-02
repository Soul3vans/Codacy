// Limpiar formulario al cerrar modal
document.getElementById('modalEnlace').addEventListener('hidden.bs.modal', function () {
    limpiarFormulario();
});

function limpiarFormulario() {
    document.getElementById('formEnlace').reset();
    document.getElementById('enlace_id').value = '';
    document.getElementById('modalEnlaceLabel').innerHTML = '<i class="fas fa-link me-2"></i>Agregar Enlace de Interés';
    document.getElementById('imagen_preview').innerHTML = '';
}

function editarEnlace(enlaceId) {
    document.getElementById('modalEnlaceLabel').innerHTML = '<i class="fas fa-edit me-2"></i>Editar Enlace de Interés';
    document.getElementById('enlace_id').value = enlaceId;

    // Cargar datos del enlace via AJAX
    fetch(`/api/enlaces/${enlaceId}/`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('titulo').value = data.titulo;
            document.getElementById('url').value = data.url;
            document.getElementById('descripcion').value = data.descripcion || '';
            document.getElementById('categoria').value = data.categoria || '';
            document.getElementById('activo').checked = data.activo;
            document.getElementById('es_destacado').checked = data.es_destacado;

            // Mostrar imagen actual si existe
            if (data.imagen_url) {
                document.getElementById('imagen_preview').innerHTML = `
                    <div class="mt-2">
                        <img src="${data.imagen_url}" class="img-thumbnail" style="max-height: 150px;">
                        <p class="small text-muted mt-1">Imagen actual</p>
                    </div>
                `;
            }

            // *** AÑADIR ESTA LÍNEA PARA MOSTRAR EL MODAL DE EDICIÓN ***
            var modal = new bootstrap.Modal(document.getElementById('modalEnlace'));
            modal.show();
        })
        .catch(error => {
            console.error('Error al cargar datos del enlace:', error);
            alert('Error al cargar los datos del enlace');
        });
}

function eliminarEnlace(enlaceId, titulo) {
    document.getElementById('enlace-titulo').textContent = titulo;
    document.getElementById('eliminar_enlace_id').value = enlaceId;

    var modal = new bootstrap.Modal(document.getElementById('modalEliminar'));
    modal.show();
}

// Preview de imagen
document.getElementById('imagen').addEventListener('change', function (e) {
    const file = e.target.files[0];
    const preview = document.getElementById('imagen_preview');

    if (file) {
        const reader = new FileReader();
        reader.onload = function (e) {
            preview.innerHTML = `
                <div class="mt-2">
                    <img src="${e.target.result}" class="img-thumbnail" style="max-height: 150px;">
                    <p class="small text-muted mt-1">Vista previa de la imagen</p>
                </div>
            `;
        };
        reader.readAsDataURL(file);
    } else {
        preview.innerHTML = '';
    }
});

// Validación de URL
document.getElementById('url').addEventListener('blur', function () {
    const url = this.value;
    if (url && !url.startsWith('http://') && !url.startsWith('https://')) {
        this.value = 'https://' + url;
    }
});