const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('emailFile');
const botonProcesar = document.getElementById('btnProcesar');

if (dropZone && fileInput) {
    dropZone.addEventListener('click', (event) => {
        if (event.target !== fileInput) {
            fileInput.click();
        }
    });

    dropZone.addEventListener('dragover', (event) => {
        event.preventDefault();
        dropZone.style.borderColor = '#6366f1';
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.style.borderColor = '#334155';
    });

    dropZone.addEventListener('drop', (event) => {
        event.preventDefault();
        dropZone.style.borderColor = '#334155';
        if (event.dataTransfer.files.length > 0) {
            fileInput.files = event.dataTransfer.files;
        }
    });
}

if (botonProcesar) {
    botonProcesar.addEventListener('click', async (event) => {
        event.preventDefault();

        if (!fileInput || fileInput.files.length === 0) {
            alert('❌ Por favor, primero selecciona o arrastra un archivo Excel o CSV.');
            return;
        }

        const archivo = fileInput.files[0];
        const formData = new FormData();
        formData.append('file', archivo);
        const esLocal = window.location.hostname === 'localhost'
            || window.location.hostname === '127.0.0.1';
        const uploadUrl = esLocal
            ? 'http://127.0.0.1:5000/upload'
            : 'https://lysifix-website.onrender.com/upload';

        try {
            const response = await fetch(uploadUrl, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json().catch(() => null);
                throw new Error(error?.error || `HTTP ${response.status}`);
            }

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `Lysifix_Express_${archivo.name}`;
            document.body.appendChild(link);
            link.click();
            link.remove();
            URL.revokeObjectURL(url);
            alert('✅ ¡Optimización completada! Tu descarga ha iniciado.');
        } catch (error) {
            console.error('Error al procesar el archivo:', error);
            alert(`❌ No se pudo procesar el archivo: ${error.message}`);
        }
    });
}
