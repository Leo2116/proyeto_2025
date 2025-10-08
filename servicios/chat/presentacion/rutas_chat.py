from flask import Blueprint, request, jsonify

from inicializar_db import resolve_db_uri, get_engine_and_session, ProductoORM
from servicios.chat.recomendador import recomendar


chat_bp = Blueprint("chat_bp", __name__, url_prefix="/api/v1/chat")


@chat_bp.post("/recomendar")
def api_chat_recomendar():
    data = request.get_json(silent=True) or {}
    mensaje = (data.get("mensaje") or data.get("text") or "").strip()

    # Crear sesión a la DB SQLite directamente (no usamos extensión Flask-SQLAlchemy aquí)
    db_uri = resolve_db_uri()
    engine, SessionLocal = get_engine_and_session(db_uri)
    session = SessionLocal()
    try:
        productos = session.query(ProductoORM).limit(200).all()
        sugerencias = recomendar(mensaje, productos)
        return jsonify(sugerencias), 200
    except Exception:
        return jsonify({"error": "Error al recomendar productos."}), 500
    finally:
        session.close()

