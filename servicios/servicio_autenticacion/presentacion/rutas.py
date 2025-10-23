# servicios/servicio_autenticacion/presentacion/rutas.py

from flask import Blueprint, request, jsonify, session
import os
import requests

# Importamos las clases de Caso de Uso
from servicios.servicio_autenticacion.aplicacion.casos_uso.registrar_usuario import RegistrarUsuario
from servicios.servicio_autenticacion.aplicacion.casos_uso.iniciar_sesion import IniciarSesion
from servicios.servicio_autenticacion.aplicacion.casos_uso.enviar_verificacion_correo import EnviarVerificacionCorreo

# Importamos la implementacion del Repositorio
from servicios.servicio_autenticacion.infraestructura.persistencia.sqlite_repositorio_usuario import SQLiteRepositorioUsuario
from servicios.servicio_autenticacion.infraestructura.clientes_externos.google_smtp_cliente import GoogleSMTPCliente
from configuracion import Config
from utils.jwt import create_jwt
from passlib.hash import pbkdf2_sha256 as pwd_context

# Enterprise helper (opcional)
from servicios.servicio_autenticacion.presentacion.recaptcha_enterprise import verify_enterprise

# ----------------------------------------------------------------------
# INICIALIZACION Y BLUEPRINT
# ----------------------------------------------------------------------

# Creamos el Blueprint para agrupar las rutas de autenticacion
auth_bp = Blueprint('auth_bp', __name__, url_prefix='/api/v1/auth')

# ----------------------------------------------------------------------
# CONFIGURACION DE CASOS DE USO E INFRAESTRUCTURA
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
# RUTAS DE AUTENTICACION
# ----------------------------------------------------------------------

def _enterprise_enabled():
    try:
        flag = os.getenv('RECAPTCHA_ENTERPRISE') or getattr(Config, 'RECAPTCHA_ENTERPRISE', None)
        return bool(flag) and str(flag).lower() in ('1', 'true', 'yes')
    except Exception:
        return False


def _registrar_impl():
    """Ruta para registrar un nuevo usuario."""
    data = request.get_json() or {}

    nombre = data.get('nombre')
    email = data.get('email')
    password = data.get('password')
    # reCAPTCHA (v2 o Enterprise)
    recaptcha_token = data.get('recaptcha') or data.get('g_recaptcha_response') or data.get('g-recaptcha-response')

    if not all([nombre, email, password]):
        return jsonify({"error": "Faltan campos requeridos (nombre, email, password)."}), 400

    # Enterprise primero si está activado
    if _enterprise_enabled():
        ok, msg = verify_enterprise(
            recaptcha_token,
            action=(getattr(Config, 'RECAPTCHA_ACTION_REGISTER', None) or 'register'),
            request_obj=request
        )
        if not ok:
            return jsonify({"error": msg}), (502 if 'No se pudo verificar' in (msg or '') else 400)
    else:
        # Validación reCAPTCHA v2 si hay SECRET configurado
        secret = os.getenv('RECAPTCHA_SECRET_KEY') or getattr(Config, 'RECAPTCHA_SECRET_KEY', None)
        if secret:
            if not recaptcha_token:
                return jsonify({"error": "Falta verificación reCAPTCHA."}), 400
            try:
                r = requests.post(
                    'https://www.google.com/recaptcha/api/siteverify',
                    data={'secret': secret, 'response': recaptcha_token, 'remoteip': request.headers.get('X-Forwarded-For', request.remote_addr)},
                    timeout=10
                )
                jr = (r.json() or {})
                ok = jr.get('success', False)
                # Log and handle common error codes for diagnostics
                try:
                    print('reCAPTCHA verify', {'ok': ok, 'errors': jr.get('error-codes'), 'hostname': jr.get('hostname')})
                except Exception:
                    pass
                errors = jr.get('error-codes') or []
                if (not ok) and isinstance(errors, list) and ('timeout-or-duplicate' in errors):
                    return jsonify({"error": "reCAPTCHA expirado. Marca nuevamente el checkbox."}), 400
                if not ok:
                    return jsonify({"error": "reCAPTCHA inválido."}), 400
            except Exception:
                return jsonify({"error": "No se pudo verificar reCAPTCHA."}), 502

    try:
        # 1) Crear usuario (marcar admin si su email está en ADMIN_EMAILS)
        admin_list = set((getattr(Config, 'ADMIN_EMAILS', []) or []))
        es_admin_flag = str(email or '').strip().lower() in admin_list
        usuario = registrar_usuario_uc.ejecutar(nombre=nombre, email=email, password=password, es_admin=es_admin_flag)

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
            "email": usuario.email,
            "is_admin": bool(getattr(usuario, 'es_admin', False))
        }), 201

    except ValueError as e:
        # Manejo de errores de validación (ej: email ya existe)
        return jsonify({"error": str(e)}), 409  # Conflicto

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
    data = request.get_json() or {}

    email = data.get('email')
    password = data.get('password')
    # reCAPTCHA (v2 o Enterprise)
    recaptcha_token = data.get('recaptcha') or data.get('g_recaptcha_response') or data.get('g-recaptcha-response')

    if not all([email, password]):
        return jsonify({"error": "Faltan campos requeridos (email, password)."}), 400

    # Enterprise primero si está activado
    if _enterprise_enabled():
        ok, msg = verify_enterprise(
            recaptcha_token,
            action=(getattr(Config, 'RECAPTCHA_ACTION_LOGIN', None) or 'login'),
            request_obj=request
        )
        if not ok:
            return jsonify({"error": msg}), (502 if 'No se pudo verificar' in (msg or '') else 400)
    else:
        # Validación reCAPTCHA v2 si hay SECRET configurado
        secret = os.getenv('RECAPTCHA_SECRET_KEY') or getattr(Config, 'RECAPTCHA_SECRET_KEY', None)
        if secret:
            if not recaptcha_token:
                return jsonify({"error": "Falta verificación reCAPTCHA."}), 400
            try:
                r = requests.post(
                    'https://www.google.com/recaptcha/api/siteverify',
                    data={'secret': secret, 'response': recaptcha_token, 'remoteip': request.headers.get('X-Forwarded-For', request.remote_addr)},
                    timeout=10
                )
                jr = (r.json() or {})
                ok = jr.get('success', False)
                try:
                    print('reCAPTCHA verify', {'ok': ok, 'errors': jr.get('error-codes'), 'hostname': jr.get('hostname')})
                except Exception:
                    pass
                errors = jr.get('error-codes') or []
                if (not ok) and isinstance(errors, list) and ('timeout-or-duplicate' in errors):
                    return jsonify({"error": "reCAPTCHA expirado. Marca nuevamente el checkbox."}), 400
                if not ok:
                    return jsonify({"error": "reCAPTCHA inválido."}), 400
            except Exception:
                return jsonify({"error": "No se pudo verificar reCAPTCHA."}), 502

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

        # 4) Crear token tipo JWT (HS256) incluyendo is_admin
        admin_list = set((getattr(Config, 'ADMIN_EMAILS', []) or []))
        is_admin = bool(getattr(usuario, 'es_admin', False)) or (str(usuario.email).lower() in admin_list)
        token = create_jwt(
            {
                "sub": usuario.id_usuario,
                "email": usuario.email,
                "nombre": usuario.nombre,
                "is_admin": bool(is_admin),
            },
            secret=getattr(Config, 'SECRET_KEY', ''),
            expires_in=3600,
        )

        return jsonify({
            "mensaje": "Inicio de sesion exitoso.",
            "user": {
                "id": usuario.id_usuario,
                "email": usuario.email,
                "nombre": usuario.nombre,
                "is_admin": bool(is_admin),
            },
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 3600
        }), 200

    except ValueError as e:
        # Manejo de errores de credenciales (ej: email o password incorrectos)
        return jsonify({"error": str(e)}), 401  # No autorizado

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


@auth_bp.route('/resend-verification', methods=['POST'])
def resend_verification():
    """Reenvía el correo de verificación al usuario especificado por email o al usuario en sesión."""
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or session.get('user_email') or '').strip()
    if not email:
        return jsonify({"error": "Email requerido para reenviar verificación."}), 400

    try:
        # Buscar usuario por email
        usuario = repositorio_usuario.obtener_por_email(email)
        if not usuario:
            return jsonify({"error": "Usuario no encontrado para ese email."}), 404
        # Si ya está verificado, informar y salir
        if repositorio_usuario.email_verificado(email):
            return jsonify({"ok": True, "mensaje": "La cuenta ya está verificada."}), 200

        # Enviar correo de verificación
        servicio_correo = GoogleSMTPCliente()
        try:
            from servicios.servicio_autenticacion.aplicacion.casos_uso.enviar_verificacion_correo import EnviarVerificacionCorreo
            enviar_verif_uc = EnviarVerificacionCorreo(repositorio_usuario, servicio_correo)
            enviar_verif_uc.ejecutar(usuario.id_usuario, email=email)
        except Exception as e:
            # Error controlado al enviar
            return jsonify({"error": f"No se pudo enviar verificación: {str(e)}"}), 502

        return jsonify({"ok": True, "mensaje": "Correo de verificación reenviado (revisa SPAM)."}), 200
    except Exception:
        return jsonify({"error": "Error interno al reintentar verificación."}), 500
