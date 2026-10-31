import os
from flask import Flask, request, jsonify, send_from_directory, make_response
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
from sqlalchemy import Column, Integer, String

class Usuario(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    creditos = Column(Integer, default=100)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
session = SessionLocal()
Base.metadata.create_all(bind=engine)
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
@app.route('/api/consumir_credito', methods=['POST', 'OPTIONS'])
def consumir_credito():
    # Manejo automático de peticiones de seguridad del navegador (Preflight)
    import flask
    if flask.request.method == 'OPTIONS':
        voto = flask.make_response()
        voto.headers.add("Access-Control-Allow-Origin", "*")
        voto.headers.add('Access-Control-Allow-Headers', "*")
        voto.headers.add('Access-Control-Allow-Methods', "*")
        return voto

    datos = request.get_json() or {}
    email_usuario = datos.get('email', 'anonimo')
    mensaje_usuario = datos.get('mensaje', '')

    if not mensaje_usuario:
        respuesta = jsonify({"status": "error", "message": "El mensaje está vacío"})
        respuesta.headers.add("Access-Control-Allow-Origin", "*")
        return respuesta, 400
        
    usuario = session.query(Usuario).filter_by(email=email_usuario).first()
    if not usuario:
        usuario = Usuario(email=email_usuario, creditos=100)
        session.add(usuario)
        session.commit()
        
    if usuario.creditos <= 0:
        return jsonify({"status": "bloqueado", "message": "Créditos agotados. Redirigiendo al Paywall."}), 403

    try:
        instrucciones = """Eres el asistente virtual oficial de Lysifix. 
Cuando un usuario te pregunte si puedes ayudarlo con un programa, software o servicio de automatización para su empresa, debes responder siempre con entusiasmo y en tercera persona usando frases como '¡Claro! Lysifix te puede ayudar con eso' o 'En Lysifix somos expertos en desarrollar soluciones de automatización a la medida para empresas'. 
Sé muy profesional, habla en nombre de la marca, dale una breve idea de lo que se puede lograr y siempre invítalo a ponerse en contacto a través de la sección de contacto de la página web para cotizar su proyecto.
Responde SIEMPRE en el mismo idioma en el que el usuario te esté escribiendo."""

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

# from flask import Flask, request, jsonify, make_response, send_from_directory

@app.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        response = make_response('', 200)
        response.headers["Access-Control-Allow-Origin"] = "https://lysifix.dev"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response
        
    try:
        datos = request.get_json()
        mensaje_usuario = datos.get('mensaje')
        
        # 1. LLAMADA REAL A LA IA (Asegúrate de usar tu variable 'client' u 'openai')
        completion = client.chat.completions.create(
            model="gpt-4o-mini", # O el modelo que estés usando (gpt-3.5-turbo, etc.)
            messages=[
                {"role": "system", "content": "Eres Lysifix, un asistente virtual experto en automatización web."},
                {"role": "user", "content": mensaje_usuario}
            ]
        )
        
        # 2. EXTRAER EL TEXTO GENERADO POR LA IA
        respuesta_ia = completion.choices[0].message.content
        
        # 3. ENVIAR LA RESPUESTA REAL AL FRONTEND
        response = make_response(jsonify({"respuesta": respuesta_ia}), 200)
        response.headers["Access-Control-Allow-Origin"] = "https://lysifix.dev"
        return response
        
    except Exception as e:
        response = make_response(jsonify({"error": str(e)}), 400)
        response.headers["Access-Control-Allow-Origin"] = "https://lysifix.dev"
        return response

if __name__ == '__main__':
     port = int(os.environ.get("PORT", 5000))
     app.run(host='0.0.0.0', port=port)
    
