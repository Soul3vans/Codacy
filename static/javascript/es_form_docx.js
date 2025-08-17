document.addEventListener('DOMContentLoaded', function() {
    const archivoInput = document.getElementById('id_archivo') || document.getElementById('id_nuevo_archivo');
    const nombreInput = document.getElementById('id_nombre');
    const selectTipo = document.getElementById('id_tipo');
    const formularioCheckbox = document.getElementById('formularioCheckbox');
    const esFormularioCheckbox = document.getElementById('id_es_formulario');

    // Función para mostrar/ocultar el checkbox del formulario
    function handleFormCheckbox(file) {
        if (!formularioCheckbox) return;

        if (file && file.name.endsWith('.docx')) {
            formularioCheckbox.style.display = 'block';
        } else {
            formularioCheckbox.style.display = 'none';
            if (esFormularioCheckbox) esFormularioCheckbox.checked = false;
        }
    }

    // Función para autocompletar el nombre del archivo
    function autoFillName(file) {
        if (nombreInput && file && !nombreInput.value) {
            const fileName = file.name.replace(/\.[^/.]+$/, '');
            nombreInput.value = fileName;
        }
    }

    // Función para seleccionar automáticamente el tipo de archivo
    function autoSelectFileType(file) {
        if (!selectTipo || !file) return;

        const ext = file.name.split('.').pop().toLowerCase();
        let tipo = 'otro';

        const fileTypes = {
            imagen: ["jpg", "jpeg", "png", "gif", "bmp", "svg", "webp"],
            pdf: ["pdf"],
            documento: ["doc", "docx", "odt", "txt", "xls", "xlsx", "ppt", "pptx"],
            video: ["mp4", "avi", "mov", "wmv", "mkv", "webm"]
        };

        for (const [key, extensions] of Object.entries(fileTypes)) {
            if (extensions.includes(ext)) {
                tipo = key;
                break;
            }
        }
        selectTipo.value = tipo;
    }

    if (archivoInput) {
        archivoInput.addEventListener('change', function(event) {
            const file = this.files[0];
            if (file) {
                handleFormCheckbox(file);
                autoFillName(file);
                autoSelectFileType(file);
            }
        });
    }
});