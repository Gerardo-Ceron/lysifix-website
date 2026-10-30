import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from flask_bcrypt import Bcrypt
from openai import OpenAI  # <-- 1. Importamos la librería de OpenAI
from dotenv import load_dotenv

# 🔥 TRUCO DEFINITIVO: Busca el archivo .env en la misma carpeta que este script
ruta_dir = os.path.dirname(os.path.abspath(__file__))
ruta_env = os.path.join(ruta_dir, '.env')
load_dotenv(ruta_env)

app = Flask(__name__, template_folder='.', static_folder='.', root_path=ruta_dir)
CORS(app, resources={r"/api/": {"origins": ""}})
bcrypt = Bcrypt(app)

# 🚀 CLIENTE LIMPIO Y SEGURO: Busca la clave en el entorno de forma automática
client = OpenAI()

# 1. CONFIGURACIÓN DE BASE DE DATOS
engine = create_engine('sqlite:///lysifix.db', echo=False)
Base = declarative_base()

# 2. MODELO DE USUARIO
class Usuario(Base):
    __tablename__ = 'usuarios'
    
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    creditos = Column(Integer, default=5)
    is_premium = Column(Boolean, default=False)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# ==========================================
# RUTAS PARA EL DISEÑO Y LA PÁGINA WEB
# ==========================================
@app.route('/')
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

# RUTA PARA LA PÁGINA EN INGLÉS (Busca el index adentro de la carpeta 'en')
@app.route('/en')
def home_en():
    from flask import send_from_directory
    import os
    ruta_ingles = os.path.join('.', 'en')
    return send_from_directory(ruta_ingles, 'index.html')

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
        # 1. Detectamos el idioma que viene en el mensaje (o si el usuario escribe en inglés)
        # Para hacerlo ultra inteligente, le pedimos a OpenAI que mantenga el idioma del usuario.
        instrucciones = (
            "Eres Lysifix, el asistente virtual carismático y experto de Lysifix. "
            "Responde SIEMPRE en el mismo idioma en el que el usuario te esté escribiendo. "
            "If the user speaks to you in English, reply in English with a fresh and professional tone. "
            "Si te hablan en español, responde en español con un tono fresco y profesional."
        )

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": instrucciones}, # <-- Le pasamos la instrucción bilingüe
                {"role": "user", "content": mensaje_usuario}
            ]
        )
        
        respuesta_ia = completion.choices[0].message.content
        usuario.creditos -= 1
        session.commit()
        return jsonify({"status": "success", "creditos_restantes": usuario.creditos, "respuesta": respuesta_ia})
    except Exception as e:
        session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

# Crear usuario de prueba automáticamente al arrancar si no existe
with app.app_context():
    existe = session.query(Usuario).filter_by(email="prueba@lysifix.com").first()
    if not existe:
        pass_enc = bcrypt.generate_password_hash("secreto123").decode('utf-8')
        user_prueba = Usuario(email="prueba@lysifix.com", password=pass_enc, creditos=5)
        session.add(user_prueba)
        session.commit()
        print("🚀 [Lysifix] ¡Usuario prueba@lysifix.com listo en la base de datos!")
# ==========================================
# RUTA PARA MOSTRAR TU PÁGINA WEB PRINCIPAL
# ==========================================
@app.route('/')
def home():
    from flask import send_from_directory
    return send_from_directory('.', 'index.html')
# ==========================================
# 3. RUTA PARA CONSUMIR CRÉDITOS Y LLAMAR A OPENAI
@app.route('/api/consumir-credito', methods=['POST'])
def consumir_credito():
    datos = request.get_json() or {}
    email_usuario = datos.get('email')
    mensaje_usuario = datos.get('mensaje')  # <-- Recibimos el mensaje del chat
    
    if not email_usuario:
        return jsonify({"status": "error", "message": "Email requerido"}), 400
    if not mensaje_usuario:
        return jsonify({"status": "error", "message": "Mensaje requerido"}), 400
        
    # Buscar al usuario
    usuario = session.query(Usuario).filter_by(email=email_usuario).first()
    
    if not usuario:
        return jsonify({"status": "error", "message": "Usuario no encontrado"}), 404
        
    # Verificar créditos disponibles
    if usuario.creditos <= 0:
        return jsonify({
            "status": "bloqueado", 
            "message": "Créditos agotados. Redirigiendo al Paywall."
        }), 403

    try:
        # 2. Llamada real a la API de OpenAI
        completion = client.chat.completions.create(
            model="gpt-4o-mini",  # Modelo rápido y muy económico
            messages=[
                {"role": "system", "content": "Eres Lysifix, un asistente virtual experto y amable."},
                {"role": "user", "content": mensaje_usuario}
            ]
        )
        
        respuesta_ia = completion.choices[0].message.content

        # 3. Si OpenAI responde con éxito, restamos el crédito
        usuario.creditos -= 1
        session.commit()

        return jsonify({
            "status": "success", 
            "creditos_restantes": usuario.creditos,
            "respuesta": respuesta_ia,  # <-- Enviamos la respuesta de la IA al frontend
            "message": "Crédito consumido y respuesta de OpenAI generada correctamente."
        })

    except Exception as e:
        session.rollback()
        print(f"❌ Error al conectar con OpenAI: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": f"Fallo en la comunicación con la IA: {str(e)}"
        }), 500

# 4. RUTA PARA REGISTRAR UN USUARIO
@app.route('/api/registrar', methods=['POST'])
def registrar_usuario():
    datos = request.get_json() or {}
    email = datos.get('email')
    password = datos.get('password')
    
    if not email or not password:
        return jsonify({"status": "error", "message": "Email y contraseña requeridos"}), 400
        
    usuario_existente = session.query(Usuario).filter_by(email=email).first()
    if usuario_existente:
        return jsonify({"status": "error", "message": "El usuario ya existe"}), 400
        
    password_encriptada = bcrypt.generate_password_hash(password).decode('utf-8')
    nuevo_usuario = Usuario(email=email, password=password_encriptada, creditos=5)
    
    session.add(nuevo_usuario)
    session.commit()
    
    return jsonify({
        "status": "success", 
        "message": f"Usuario {email} creado con éxito con 5 créditos gratis."
    }), 201

if __name__ == '__main__':
    app.run(debug=True, port=5000)