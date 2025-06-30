//Muestra el textarea cuando se marque la opcion no
document.addEventListener('DOMContentLoaded', function () {
    var radios = document.querySelectorAll('input[name^="respuesta_"]');
    radios.forEach(function (radio) {
        radio.addEventListener('change', function () {
            var preguntaId = this.getAttribute('data-pregunta-id');
            var box = document.getElementById('fundamentacion-box-' + preguntaId);
            if (this.value === 'no' && this.checked) {
                box.style.display = '';
            } else if (this.checked) {
                box.style.display = 'none';
            }
        });
    });
});

