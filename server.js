const express = require('express');
const multer = require('multer');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 3000;

// Permitir que tu HTML de Live Server se conecte sin bloqueos de seguridad
app.use(cors());
app.use(express.json());

// Configuración para recibir los archivos en una carpeta temporal
const uploadDirectory = path.join(__dirname, 'uploads');
fs.mkdirSync(uploadDirectory, { recursive: true });
const upload = multer({ dest: uploadDirectory });

// ESTA ES LA RUTA QUE ANTES DABA ERROR 405
function processFile(req, res) {
    try {
        if (!req.file) {
            return res.status(400).send('No se subió ningún archivo.');
        }

        console.log(`📥 Archivo recibido con éxito: ${req.file.originalname}`);

        // -------------------------------------------------------------
        // NOTA PARA EL FUTURO: Aquí irá tu lógica para corregir el Excel
        // y la verificación del pago de Stripe/MercadoPago.
        // -------------------------------------------------------------

        // Por ahora, devolvemos el mismo archivo recibido para comprobar que la conexión funciona
        const caminoArchivo = req.file.path;
        res.download(caminoArchivo, 'archivo_procesado.xlsx', (err) => {
            if (err) {
                console.error("Error al descargar:", err);
            }
            // Borrar el archivo temporal de la computadora después de enviarlo
            if (fs.existsSync(caminoArchivo)) {
                fs.unlinkSync(caminoArchivo); 
            }
        });

    } catch (error) {
        console.error(error);
        res.status(500).send('Error interno en el servidor.');
    }
}

app.post(['/procesar-archivo', '/upload'], upload.single('file'), processFile);

app.listen(PORT, () => {
    console.log(`🚀 Servidor backend corriendo en http://localhost:${PORT}`);
});