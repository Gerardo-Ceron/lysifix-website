// Iniciar la animación de la terminal cuando cargue la página
if (typeof typeTerminal === 'function') {
    document.addEventListener("DOMContentLoaded", typeTerminal);
}

// ==========================================
// CÓDIGO DE LA ZONA DE ARRASTRE (DROP ZONE)
// ==========================================
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('emailFile');
let archivoSeleccionado = null;

if (dropZone && fileInput) {
    dropZone.addEventListener('click', (e) => {
        if (e.target !== fileInput) fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            archivoSeleccionado = e.target.files[0];
            alert("✅ Archivo cargado correctamente: " + archivoSeleccionado.name);
        }
    });

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#6366f1';
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.style.borderColor = '#334155';
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#334155';
        if (e.dataTransfer.files.length > 0) {
            archivoSeleccionado = e.dataTransfer.files[0];
            fileInput.files = e.dataTransfer.files; 
            alert("✅ Archivo arrastrado correctamente: " + archivoSeleccionado.name);
        }
    });
}

// ==========================================
// CÓDIGO DEL BOTÓN AZUL - PROCESAR Y DESCARGAR
// ==========================================
const botonProcesar = document.getElementById('btnProcesar');

if (botonProcesar) {
    botonProcesar.addEventListener('click', async (e) => {
        e.preventDefault();

        const inputArchivo = document.getElementById('emailFile');

        if (!inputArchivo || !inputArchivo.files || inputArchivo.files.length === 0) {
            alert("❌ Por favor, primero selecciona o arrastra un archivo Excel o CSV.");
            return;
        }

        const archivoParaEnviar = inputArchivo.files[0];
        const formData = new FormData();
        formData.append("file", archivoParaEnviar);

        alert("Conectando con Lysifix Cloud para procesar: " + archivoParaEnviar.name);

        try {
            const response = await fetch("http://127.0.0.1:5000/upload", {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Error en el servidor');
            }

            const blob = await response.blob();

            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = "Lysifix_Express_" + archivoParaEnviar.name;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);

            alert("✅ ¡Optimización Completada! Tu descarga ha iniciado.");
        } catch (error) {
            console.error("Error al procesar el archivo:", error);
            alert("❌ Ocurrió un error al intentar conectar con el servidor de Python.");
        }
    });
}