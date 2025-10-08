from flask import Blueprint, jsonify

from servicios.api_externa.zip_postal import buscar_codigo_postal_gt


postal_bp = Blueprint("postal_bp", __name__, url_prefix="/api/v1")


@postal_bp.get("/postal/<codigo>")
def api_postal_gt(codigo: str):
    try:
        data = buscar_codigo_postal_gt(codigo)
        if not data:
            return jsonify({"error": "Código postal no encontrado."}), 404
        return jsonify(data), 200
    except Exception:
        return jsonify({"error": "Error al consultar Zippopotam.us"}), 502

