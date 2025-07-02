document.getElementById('id_archivo').addEventListener('change', function (event) {
    var fileInput = event.target;
    var file = fileInput.files[0];
    var formularioCheckbox = document.getElementById('formularioCheckbox');

    if (file && file.name.endsWith('.docx')) {
        formularioCheckbox.style.display = 'block';
    } else {
        formularioCheckbox.style.display = 'none';
        document.getElementById('id_es_formulario').checked = false;
    }
});