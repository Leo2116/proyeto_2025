from flask import Blueprint, request, jsonify, session
import os
import unicodedata

from servicios.ia.gemini_client import chat_completion as gemini_chat
from servicios.admin.infraestructura.tickets_repo import TicketsRepo
from servicios.servicio_catalogo.infraestructura.persistencia.sqlite_repositorio_producto import (
    SQLiteRepositorioProducto,
)


ia_bp = Blueprint("ia_bp", __name__, url_prefix="/api/v1/ia")
_tickets = TicketsRepo()
_tickets.ensure_schema()
_catalog_repo = SQLiteRepositorioProducto()


@ia_bp.post("/chat")
def ia_chat():
    data = request.get_json(silent=True) or {}
    mensaje = (data.get("mensaje") or data.get("message") or "").strip()
    if not mensaje:
        return jsonify({"error": "'mensaje' es requerido."}), 400

    try:
        # Saludo amable pero acotado al dominio
        if _is_greeting(mensaje):
            saludo = (
                "¡Hola! Soy el asistente de la Librería Jehová Jiréh. "
                "Puedo ayudarte a buscar productos o recomendar opciones de nuestro catálogo. "
                "¿Qué estás buscando (tipo, autor/marca o presupuesto)?"
            )
            return jsonify({"respuesta": saludo, "provider": "assistant"}), 200

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

        # Construir contexto desde la base de datos para forzar respuestas basadas en catálogo
        catalog_items = _catalog_context(mensaje, limit=8)
        if not catalog_items:
            aclarar = (
                "Puedo ayudarte a elegir, pero necesito un poco más de información. "
                "¿Buscas un libro o un útil escolar? ¿Autor/marca o presupuesto aproximado?"
            )
            return jsonify({"respuesta": aclarar, "provider": "assistant"}), 200

        reglas = (
            "Eres el asistente de la 'Librería Jehová Jiréh'.\n"
            "Responde únicamente usando el catálogo provisto; no inventes datos.\n"
            "Sé amable y breve. Si falta información, pide 1-2 aclaraciones (tipo, autor/marca, presupuesto).\n"
            "Si intentan conversar de otros temas, indica amablemente que solo ayudas con la librería.\n"
            "En recomendaciones, sugiere 3-5 opciones del catálogo con precio y un motivo simple."
        )
        lines = []
        for it in catalog_items:
            precio = float(it.get("precio") or 0)
            extra_am = it.get("autor") or it.get("marca") or it.get("autor_marca")
            extra_is = it.get("isbn") or it.get("sku") or it.get("isbn_sku")
            line = f"- {it.get('id')} | {it.get('nombre')} | {it.get('tipo') or '-'} | Q{precio:.2f}"
            if extra_am:
                line += f" | Autor/Marca: {extra_am}"
            if extra_is:
                line += f" | ISBN/SKU: {extra_is}"
            lines.append(line)
        contexto = "Catálogo (máx 8):\n" + "\n".join(lines)
        sys_prompt = ((system or "").strip() + "\n\n" + reglas + "\n\n" + contexto).strip()

        out = gemini_chat(mensaje, system_prompt=sys_prompt, model=model, temperature=temperature)
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


def _is_greeting(text: str) -> bool:
    nt = _norm(text or "")
    greetings = ("hola", "buenas", "buenos dias", "buenos días", "hello", "hi", "saludos")
    return any(nt.startswith(_norm(g)) for g in greetings) and len(nt.split()) <= 6


def _catalog_context(query: str, limit: int = 8) -> list[dict]:
    try:
        q = (query or "").strip()
        items = _catalog_repo.buscar_productos(q) if q else _catalog_repo.obtener_todos()
        data: list[dict] = []
        for p in items[: max(1, limit)]:
            try:
                data.append(p.to_dict())
            except Exception:
                data.append({
                    "id": getattr(p, "id", None),
                    "nombre": getattr(p, "nombre", None),
                    "precio": getattr(p, "precio", 0),
                    "tipo": p.__class__.__name__,
                })
        return data
    except Exception:
        return []
