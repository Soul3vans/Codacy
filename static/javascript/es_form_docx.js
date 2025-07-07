document.addEventListener('DOMContentLoaded', function() {
    const archivoInput = document.getElementById('id_archivo') || document.getElementById('id_nuevo_archivo');
    const nombreInput = document.getElementById('id_nombre');
    const selectTipo = document.getElementById('id_tipo');
    const formularioCheckbox = document.getElementById('formularioCheckbox');
    const esFormularioCheckbox = document.getElementById('id_es_formulario');

    if (archivoInput) {
        archivoInput.addEventListener('change', function(event) {
            const file = this.files[0];
            // Mostrar/ocultar checkbox de formulario según extensión
            if (formularioCheckbox) {
                if (file && file.name.endsWith('.docx')) {
                    formularioCheckbox.style.display = 'block';
                } else {
                    formularioCheckbox.style.display = 'none';
                    if (esFormularioCheckbox) esFormularioCheckbox.checked = false;
                }
            }
            // Autocompletar el campo nombre solo si está vacío
            if (nombreInput && file) {
                if (!nombreInput.value) {
                    const fileName = file.name.replace(/\.[^/.]+$/, '');
                    nombreInput.value = fileName;
                }
            }
            // Selección automática del tipo de archivo
            if (selectTipo && file) {
                const ext = file.name.split('.').pop().toLowerCase();
                let tipo = 'otro';
                if (["jpg","jpeg","png","gif","bmp","svg","webp"].includes(ext)) tipo = 'imagen';
                else if (["pdf"].includes(ext)) tipo = 'pdf';
                else if (["doc","docx","odt","txt","xls","xlsx","ppt","pptx"].includes(ext)) tipo = 'documento';
                else if (["mp4","avi","mov","wmv","mkv","webm"].includes(ext)) tipo = 'video';
                selectTipo.value = tipo;
            }
        });
    }
});