import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# PRIMERO CREAMOS LA APP PARA QUE NO DE ERROR
app = Flask(__name__)
CORS(app, resources={r"/": {"origins": ""}})

# Configuración de OpenAI con credenciales automáticas
client = OpenAI()

# Configuración de Base de Datos SQLite local
engine = create_engine('sqlite:///lysifix.db', echo=True)
Base = declarative_base()
# ==========================================
# RUTAS PARA EL DISEÑO Y LA PÁGINA WEB
# ==========================================
@app.route('/')
@app.route('/index.html')
def home():
    from flask import send_from_directory
    return send_from_directory('.', 'index.html')

@app.route('/estilos.css')
def css():
    from flask import send_from_directory
    return send_from_directory('.', 'estilos.css')

@app.route('/favicon-32x32.png')
def favicon32():
    from flask import send_from_directory
    return send_from_directory('.', 'favicon-32x32.png')

@app.route('/favicon-16x16.png')
def favicon16():
    from flask import send_from_directory
    return send_from_directory('.', 'favicon-16x16.png')

# ==========================================
# RUTAS PARA LA VERSIÓN EN INGLÉS
# ==========================================
@app.route('/en')
@app.route('/en/index.html')
def home_en():
    from flask import send_from_directory
    import os
    ruta_ingles = os.path.join('.', 'en')
    return send_from_directory(ruta_ingles, 'index.html')

@app.route('/en/<path:filename>')
def archivos_en(filename):
    from flask import send_from_directory
    import os
    ruta_ingles = os.path.join('.', 'en')
    return send_from_directory(ruta_ingles, filename)

# ==========================================
# RUTA PARA CONSUMIR CRÉDITOS Y LLAMAR A OPENAI
# ==========================================
@app.route('/api/consumir-credito', methods=['POST'])
def consumir_credito():
    datos = request.get_json() or {}
    email_usuario = datos.get('email')
    mensaje_usuario = datos.get('mensaje')
    
    if not email_usuario or not mensaje_usuario:
        return jsonify({"status": "error", "message": "Faltan datos"}), 400
        
    usuario = session.query(Usuario).filter_by(email=email_usuario).first()
    if not usuario:
        return jsonify({"status": "error", "message": "Usuario no encontrado"}), 404
        
    if usuario.creditos <= 0:
        return jsonify({"status": "bloqueado", "message": "Créditos agotados. Redirigiendo al Paywall."}), 403

    try:
        instrucciones = (
            "Eres Lysifix, el asistente virtual carismático y experto de Lysifix. "
            "Responde SIEMPRE en el mismo idioma en el que el usuario te esté escribiendo."
        )
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": instrucciones},
                {"role": "user", "content": mensaje_usuario}
            ]
        )
        respuesta_ia = completion.choices.message.content
        usuario.creditos -= 1
        session.commit()
        return jsonify({"status": "success", "creditos_restantes": usuario.creditos, "respuesta": respuesta_ia})
    except Exception as e:
        session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
