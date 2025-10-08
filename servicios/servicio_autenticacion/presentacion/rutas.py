# servicios/servicio_autenticacion/presentacion/rutas.py

from flask import Blueprint, request, jsonify, session

# Importamos las clases de Caso de Uso
# Asumimos que generarás estos archivos pronto para que esto funcione
from servicios.servicio_autenticacion.aplicacion.casos_uso.registrar_usuario import RegistrarUsuario
from servicios.servicio_autenticacion.aplicacion.casos_uso.iniciar_sesion import IniciarSesion
from servicios.servicio_autenticacion.aplicacion.casos_uso.enviar_verificacion_correo import EnviarVerificacionCorreo

# Importamos la implementacion del Repositorio
from servicios.servicio_autenticacion.infraestructura.persistencia.sqlite_repositorio_usuario import SQLiteRepositorioUsuario
from servicios.servicio_autenticacion.infraestructura.clientes_externos.google_smtp_cliente import GoogleSMTPCliente
from configuracion import Config
from passlib.hash import pbkdf2_sha256 as pwd_context

# ----------------------------------------------------------------------
# INICIALIZACIÓN Y BLUEPRINT
# ----------------------------------------------------------------------

# Creamos el Blueprint para agrupar las rutas de autenticacion
auth_bp = Blueprint('auth_bp', __name__, url_prefix='/api/v1/auth')

# ----------------------------------------------------------------------
# CONFIGURACIÓN DE CASOS DE USO E INFRAESTRUCTURA
# ----------------------------------------------------------------------
# Se inicializa el Repositorio de Infraestructura
repositorio_usuario = SQLiteRepositorioUsuario()

# Se inyectan las dependencias en los Casos de Uso
registrar_usuario_uc = RegistrarUsuario(
    repositorio=repositorio_usuario,
    hasher=pwd_context
)
iniciar_sesion_uc = IniciarSesion(
    repositorio=repositorio_usuario,
    hasher=pwd_context
)


# ----------------------------------------------------------------------
# RUTAS DE AUTENTICACIÓN
# ----------------------------------------------------------------------

def _registrar_impl():
    """Ruta para registrar un nuevo usuario."""
    data = request.get_json()
    
    nombre = data.get('nombre')
    email = data.get('email')
    password = data.get('password')

    if not all([nombre, email, password]):
        return jsonify({"error": "Faltan campos requeridos (nombre, email, password)."}), 400

    try:
        # 1) Crear usuario
        usuario = registrar_usuario_uc.ejecutar(nombre=nombre, email=email, password=password)

        # 2) Enviar verificación por correo (no bloquea el registro si falla)
        try:
            servicio_correo = GoogleSMTPCliente()
            enviar_verif_uc = EnviarVerificacionCorreo(repositorio_usuario, servicio_correo)
            enviar_verif_uc.ejecutar(usuario.id_usuario, usuario.email, usuario.nombre)
        except Exception:
            # Log ya se imprime dentro; continuamos
            pass

        return jsonify({
            "mensaje": "Usuario registrado exitosamente.",
            "id_usuario": usuario.id_usuario,
            "email": usuario.email
        }), 201

    except ValueError as e:
        # Manejo de errores de validacion (ej: email ya existe)
        return jsonify({"error": str(e)}), 409 # Conflicto

    except Exception:
        # Manejo de errores internos (ej: error de base de datos)
        return jsonify({"error": "Error interno del servidor al registrar."}), 500


@auth_bp.route('/registro', methods=['POST'])
def registro():
    return _registrar_impl()

@auth_bp.route('/register', methods=['POST'])
def register():
    return _registrar_impl()


@auth_bp.route('/login', methods=['POST'])
def login():
    """Ruta para iniciar sesion y obtener un token (mock de JWT)."""
    data = request.get_json()
    
    email = data.get('email')
    password = data.get('password')

    if not all([email, password]):
        return jsonify({"error": "Faltan campos requeridos (email, password)."}), 400

    try:
        # 1) Verificar credenciales
        usuario = iniciar_sesion_uc.ejecutar(email=email, password=password)

        # 2) Comprobar verificación de correo
        if not repositorio_usuario.email_verificado(usuario.email):
            return jsonify({"error": "Debes verificar tu correo antes de iniciar sesión."}), 403

        # 3) Guardar sesión simple (no JWT)
        session['user_id'] = usuario.id_usuario
        session['user_email'] = usuario.email
        session['user_nombre'] = usuario.nombre

        return jsonify({
            "mensaje": "Inicio de sesion exitoso.",
            "user": {
                "id": usuario.id_usuario,
                "email": usuario.email,
                "nombre": usuario.nombre
            }
        }), 200

    except ValueError as e:
        # Manejo de errores de credenciales (ej: email o password incorrectos)
        return jsonify({"error": str(e)}), 401 # No autorizado

    except Exception:
        # Manejo de errores internos
        return jsonify({"error": "Error interno del servidor al iniciar sesion."}), 500


@auth_bp.route('/verify', methods=['GET'])
def verify_email():
    """Marca la cuenta como verificada usando token + user + email por querystring."""
    token = request.args.get('token')
    user_id = request.args.get('user')
    email = request.args.get('email')

    if not token or not user_id or not email:
        return jsonify({"error": "Parámetros incompletos."}), 400

    ok = repositorio_usuario.verificar_cuenta_por_token(user_id, email, token)
    if not ok:
        return jsonify({"ok": False, "mensaje": "Token inválido o expirado."}), 400
    return jsonify({"ok": True, "mensaje": "Cuenta verificada correctamente."}), 200


@auth_bp.route('/me', methods=['GET'])
def me():
    """Retorna el estado de autenticación y datos básicos del usuario."""
    uid = session.get('user_id')
    if not uid:
        return jsonify({"authenticated": False}), 200
    email = session.get('user_email')
    nombre = session.get('user_nombre')
    verificado = repositorio_usuario.email_verificado(email) if email else False
    return jsonify({
        "authenticated": True,
        "user": {
            "id": uid,
            "email": email,
            "nombre": nombre,
            "verificado": verificado
        }
    }), 200


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    session.pop('user_email', None)
    session.pop('user_nombre', None)
    return jsonify({"ok": True}), 200
