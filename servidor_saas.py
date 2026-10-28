from flask import Flask, request, jsonify
from flask_cors import CORS
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from flask_bcrypt import Bcrypt

app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)

# 1. CONFIGURACIÓN DE BASE DE DATOS
engine = create_engine('sqlite:///lysifix.db', echo=False)
Base = declarative_base()

# 2. MODELO DE USUARIO (Corregido con la herencia exacta)
class Usuario(Base):
    __tablename__ = 'usuarios'
    
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    creditos = Column(Integer, default=5)  # Todos empiezan con 5 créditos gratis
    is_premium = Column(Boolean, default=False)

# Crear la tabla en el archivo local si no existe
Base.metadata.create_all(engine)

# Configurar la sesión después de mapear las tablas
Session = sessionmaker(bind=engine)
session = Session()

# 3. RUTA PARA CONSUMIR CRÉDITOS
@app.route('/api/consumir-credito', methods=['POST'])
def consumir_credito():
    datos = request.get_json() or {}
    email_usuario = datos.get('email')
    
    if not email_usuario:
        return jsonify({"status": "error", "message": "Email requerido"}), 400
        
    # Buscar al usuario en la base de datos real
    usuario = session.query(Usuario).filter_by(email=email_usuario).first()
    
    if not usuario:
        return jsonify({"status": "error", "message": "Usuario no encontrado"}), 404
        
    # Verificar créditos disponibles
    if usuario.creditos > 0:
        usuario.creditos -= 1
        session.commit()
        return jsonify({
            "status": "success", 
            "creditos_restantes": usuario.creditos,
            "message": "Crédito consumido con éxito en el backend real de Lysifix."
        })
    else:
        return jsonify({
            "status": "bloqueado", 
            "message": "Créditos agotados. Redirigiendo al Paywall."
        }), 403
# 4. RUTA PARA REGISTRAR UN USUARIO DE PRUEBA
@app.route('/api/registrar', methods=['POST'])
def registrar_usuario():
    datos = request.get_json() or {}
    email = datos.get('email')
    password = datos.get('password')
    
    if not email or not password:
        return jsonify({"status": "error", "message": "Email y contraseña requeridos"}), 400
        
    # Verificar si el usuario ya existe
    usuario_existente = session.query(Usuario).filter_by(email=email).first()
    if usuario_existente:
        return jsonify({"status": "error", "message": "El usuario ya existe"}), 400
        
    # Encriptar la contraseña por seguridad e insertar en la base de datos
    password_encriptada = bcrypt.generate_password_hash(password).decode('utf-8')
    nuevo_usuario = Usuario(email=email, password=password_encriptada, creditos=5)
    
    session.add(nuevo_usuario)
    session.commit()
    
    return jsonify({
        "status": "success", 
        "message": f"Usuario {email} creado con éxito con 5 créditos gratis."
    }), 21
    # 4. RUTA PARA REGISTRAR UN USUARIO DE PRUEBA
@app.route('/api/registrar', methods=['POST'])
def registrar_usuario():
    datos = request.get_json() or {}
    email = datos.get('email')
    password = datos.get('password')
    
    if not email or not password:
        return jsonify({"status": "error", "message": "Email y contraseña requeridos"}), 400
        
    # Verificar si el usuario ya existe
    usuario_existente = session.query(Usuario).filter_by(email=email).first()
    if usuario_existente:
        return jsonify({"status": "error", "message": "El usuario ya existe"}), 400
        
    # Encriptar la contraseña por seguridad e insertar en la base de datos
    password_encriptada = bcrypt.generate_password_hash(password).decode('utf-8')
    nuevo_usuario = Usuario(email=email, password=password_encriptada, creditos=5)
    
    session.add(nuevo_usuario)
    session.commit()
    
    return jsonify({
        "status": "success", 
        "message": f"Usuario {email} creado con éxito con 5 créditos gratis."
    }), 201
if __name__ == '__main__':
    # Corre el servidor local
    app.run(debug=True, port=5000)
