from __future__ import annotations

from flask import Blueprint, jsonify, request

from servicios.ia.gemini import call_gemini, BadRequest, GeminiError


ai_dev_bp = Blueprint("ai_dev_bp", __name__, url_prefix="/api/v1/ai")


@ai_dev_bp.post("/gemini-ping")
def gemini_ping():
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    image = data.get("image")
    if not prompt:
        return jsonify({"error": "'prompt' es requerido."}), 400
    try:
        result = call_gemini(prompt_text=prompt, image_source=image)
        return (
            jsonify(
                {
                    "model": result.get("model"),
                    "mime": result.get("mime"),
                    "size_mb": result.get("size_mb"),
                    "text": result.get("text"),
                }
            ),
            200,
        )
    except BadRequest as br:
        return jsonify({"error": str(br), "kind": "bad_request"}), 400
    except GeminiError as ge:
        return jsonify({"error": str(ge), "kind": ge.category}), ge.status
    except Exception:
        return jsonify({"error": "Error inesperado"}), 502

