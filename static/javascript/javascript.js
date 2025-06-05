// Event listeners para los botones
document.addEventListener('click', function(e) {
    const usuarioId = e.target.closest('button')?.dataset.usuarioId;
    
    if (e.target.closest('.btn-editar')) {
        editarUsuario(usuarioId);
    } else if (e.target.closest('.btn-suspender')) {
        suspenderUsuario(usuarioId);
    } else if (e.target.closest('.btn-activar')) {
        activarUsuario(usuarioId);
    }
});
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('btn-eliminar')) {
        const archivoId = e.target.dataset.archivoId;
        eliminarArchivo(archivoId);
    }
});