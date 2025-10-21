from flask import Blueprint, request, jsonify, session
import os
import unicodedata

from servicios.ia.gemini_client import chat_completion as gemini_chat
from servicios.admin.infraestructura.tickets_repo import TicketsRepo


ia_bp = Blueprint("ia_bp", __name__, url_prefix="/api/v1/ia")
_tickets = TicketsRepo()
_tickets.ensure_schema()


@ia_bp.post("/chat")
def ia_chat():
    data = request.get_json(silent=True) or {}
    mensaje = (data.get("mensaje") or data.get("message") or "").strip()
    if not mensaje:
        return jsonify({"error": "'mensaje' es requerido."}), 400

    try:
        # Guardado de dominio: responder solo sobre la libreria/base de datos
        if not _is_in_domain(mensaje):
            rechazo = (
                "Lo siento, solo puedo ayudarte con temas relacionados a la Libreria Jehova Jireh "
                "(catalogo, productos, ISBN, stock, pedidos, envios y endpoints de la app)."
            )
            user_email = (session.get("user_email") or None)
            try:
                tid = _tickets.crear(mensaje, user_email=user_email, provider="guard", error="outside_domain")
            except Exception:
                tid = None
            return jsonify({"respuesta": rechazo, "provider": "guard", "ticket_id": tid}), 200

        model = data.get("model")
        system = data.get("system")
        temperature = float(data.get("temperature", 0.3))

        out = gemini_chat(mensaje, system_prompt=system, model=model, temperature=temperature)
        texto = (out.get("texto") or "").strip()
        if not texto:
            # crear ticket si modelo no pudo responder
            user_email = (session.get("user_email") or None)
            try:
                tid = _tickets.crear(mensaje, user_email=user_email, provider="gemini", error="empty_response")
            except Exception:
                tid = None
            rechazo = "No tengo una respuesta precisa en este momento. He generado un ticket para atención humana."
            return jsonify({"respuesta": rechazo, "provider": "gemini", "ticket_id": tid}), 200
        return jsonify({"respuesta": texto, "usage": out.get("usage"), "provider": "gemini"}), 200
    except ValueError as ve:
        # Error de entrada / prompt; crear ticket para seguimiento
        try:
            _tickets.crear(mensaje or "", user_email=(session.get("user_email") or None), provider="gemini", error=str(ve))
        except Exception:
            pass
        return jsonify({"error": str(ve), "ticket": True}), 400
    except RuntimeError as re:
        try:
            _tickets.crear(mensaje or "", user_email=(session.get("user_email") or None), provider="gemini", error=str(re))
        except Exception:
            pass
        return jsonify({"error": str(re), "ticket": True}), 502
    except Exception:
        try:
            _tickets.crear(mensaje or "", user_email=(session.get("user_email") or None), provider="gemini", error="unexpected_error")
        except Exception:
            pass
        return jsonify({"error": "Error al consultar el modelo de IA.", "ticket": True}), 502
def _norm(s: str) -> str:
    try:
        nf = unicodedata.normalize("NFD", str(s or ""))
        return "".join(ch for ch in nf if unicodedata.category(ch) != "Mn").lower()
    except Exception:
        return (str(s or "")).lower()

def _is_in_domain(text: str) -> bool:
    enabled = (os.getenv("AI_DOMAIN_WHITELIST_ENABLED", "true").lower() in ("1", "true", "yes"))
    if not enabled:
        return True
    raw = os.getenv(
        "AI_DOMAIN_WHITELIST",
        "libreria,catalogo,producto,autor,isbn,precio,stock,carrito,login,registro,verificacion,factura,pedido,envio,tarifa,logistica,usuario,correo,endpoint,/api/v1",
    )
    tokens = [t.strip() for t in (raw or "").split(",") if t.strip()]
    ntokens = [_norm(t) for t in tokens]
    nt = _norm(text)
    return any(t and t in nt for t in ntokens)
