from flask import Blueprint, request, jsonify

from servicios.ia.gemini_client import chat_completion as gemini_chat


ia_bp = Blueprint("ia_bp", __name__, url_prefix="/api/v1/ia")


@ia_bp.post("/chat")
def ia_chat():
    data = request.get_json(silent=True) or {}
    mensaje = (data.get("mensaje") or data.get("message") or "").strip()
    if not mensaje:
        return jsonify({"error": "'mensaje' es requerido."}), 400

    try:
        model = data.get("model")
        system = data.get("system")
        temperature = float(data.get("temperature", 0.3))

        out = gemini_chat(mensaje, system_prompt=system, model=model, temperature=temperature)
        return jsonify({"respuesta": out.get("texto"), "usage": out.get("usage"), "provider": "gemini"}), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except RuntimeError as re:
        return jsonify({"error": str(re)}), 502
    except Exception:
        return jsonify({"error": "Error al consultar el modelo de IA."}), 502
