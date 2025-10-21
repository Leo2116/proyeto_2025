from functools import wraps
from flask import request, jsonify
from configuracion import Config
from utils.jwt import decode_jwt, JWTError


def _get_bearer_token() -> str | None:
    auth = request.headers.get("Authorization") or ""
    if not auth.lower().startswith("bearer "):
        return None
    return auth.split(" ", 1)[1].strip()


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _get_bearer_token()
        if not token:
            return jsonify({"error": "Token requerido"}), 401
        try:
            payload = decode_jwt(token, getattr(Config, "SECRET_KEY", ""))
        except JWTError as e:
            return jsonify({"error": str(e)}), 401
        if not bool(payload.get("is_admin")):
            return jsonify({"error": "No autorizado"}), 403
        # opcional: exponer payload en request context si se necesita
        return fn(*args, **kwargs)
    return wrapper

