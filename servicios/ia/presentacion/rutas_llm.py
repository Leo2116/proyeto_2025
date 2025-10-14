from flask import Blueprint, request, jsonify

from servicios.ia.gemini_client import chat_completion as gemini_chat
try:
    from servicios.ia.openai_client import chat_completion as openai_chat
except Exception:
    openai_chat = None


ia_bp = Blueprint("ia_bp", __name__, url_prefix="/api/v1/ia")


@ia_bp.post("/chat")
def ia_chat():
    data = request.get_json(silent=True) or {}
    mensaje = (data.get("mensaje") or data.get("message") or "").strip()
    if not mensaje:
        return jsonify({"error": "'mensaje' es requerido."}), 400

    provider = (data.get("provider") or "gemini").lower()
    try:
        model = data.get("model")
        system = data.get("system")
        temperature = float(data.get("temperature", 0.3))

        if provider == "openai" and openai_chat is not None:
            out = openai_chat(mensaje, system_prompt=system, model=model, temperature=temperature)
        else:
            out = gemini_chat(mensaje, system_prompt=system, model=model, temperature=temperature)

        return jsonify({"respuesta": out.get("texto"), "usage": out.get("usage"), "provider": provider}), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except RuntimeError as re:
        return jsonify({"error": str(re)}), 502
    except Exception:
        return jsonify({"error": "Error al consultar el modelo de IA."}), 502
