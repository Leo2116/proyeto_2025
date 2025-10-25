from __future__ import annotations

from flask import Blueprint, request, jsonify, session, current_app
import os
import unicodedata

from servicios.ia.chat_service import generar_respuesta_catalogo
from servicios.servicio_catalogo.infraestructura.persistencia.pg_repositorio_producto import PGRepositorioProducto
from servicios.admin.infraestructura.tickets_repo import TicketsRepo
from servicios.servicio_catalogo.infraestructura.persistencia.sqlite_repositorio_producto import (
    SQLiteRepositorioProducto,
)
from servicios.servicio_autenticacion.infraestructura.clientes_externos.google_smtp_cliente import GoogleSMTPCliente


ia_bp = Blueprint("ia_bp", __name__, url_prefix="/api/v1/ia")
_tickets = TicketsRepo()
_tickets.ensure_schema()
_catalog_repo = PGRepositorioProducto()


@ia_bp.post("/chat")
def ia_chat():
    data = request.get_json(silent=True) or {}
    user_msg = (data.get("message") or data.get("mensaje") or "").strip()
    if not user_msg:
        return jsonify({"ok": False, "error": "message requerido"}), 400

    # (Opcional) obtén contexto del catálogo: top N productos o por palabra clave
    catalog_items = _catalog_context(user_msg, limit=8)
    contexto = catalog_items or None

    try:
        respuesta = generar_respuesta_catalogo(user_msg, contexto)
        current_app.logger.info("IA OK /chat")
        return jsonify({"ok": True, "message": respuesta}), 200
    except Exception:
        current_app.logger.exception("IA ERROR /chat")
        return jsonify({"ok": False, "error": "No se pudo generar respuesta"}), 500


def _norm(s: str) -> str:
    try:
        nf = unicodedata.normalize("NFD", str(s or ""))
        return "".join(ch for ch in nf if unicodedata.category(ch) != "Mn").lower()
    except Exception:
        return (str(s or "")).lower()


def _is_in_domain(text: str) -> bool:
    """Conservado por compatibilidad; no se usa actualmente."""
    enabled = (os.getenv("AI_DOMAIN_WHITELIST_ENABLED", "true").lower() in ("1", "true", "yes"))
    if not enabled:
        return True
    raw = os.getenv("AI_DOMAIN_WHITELIST", "") or ""
    if (not raw.strip()) or ("?" in raw):
        raw = ",".join([
            "libreria", "catalogo", "producto", "libro", "libros", "util", "utiles",
            "autor", "marca", "isbn", "sku", "precio", "presupuesto", "stock",
            "carrito", "comprar", "pagar", "checkout", "login", "registro", "verificacion",
            "factura", "pedido", "envio", "tarifa", "logistica", "usuario", "correo",
            "biblia", "cuaderno", "/api/v1",
        ])
    tokens = [t.strip() for t in (raw or "").split(",") if t.strip()]
    ntokens = [_norm(t) for t in tokens]
    nt = _norm(text)
    return any(t and t in nt for t in ntokens)


def _is_greeting(text: str) -> bool:
    nt = _norm(text or "")
    greetings = ("hola", "buenas", "buenos dias", "buenos días", "hello", "hi", "saludos")
    return any(nt.startswith(_norm(g)) for g in greetings) and len(nt.split()) <= 6



def _catalog_context(query: str, limit: int = 8) -> list[dict]:
    """Obtiene contexto del catálogo para el prompt.
    - Si el usuario pide algo genérico ("todos", "productos", "catálogo"), traer lista completa.
    - Si la búsqueda no devuelve resultados, hacer fallback a lista completa.
    """
    try:
        q = (query or "").strip()
        nt = _norm(q)
        generic_intents = {
            "todo", "todos", "todas", "productos", "producto", "catalogo", "catálogo",
            "lista", "listar", "muestrame", "muéstrame", "mostrar", "ver todo", "ver todos",
        }

        wants_all = (not q) or any(tok in nt for tok in generic_intents)

        items = _catalog_repo.obtener_todos() if wants_all else _catalog_repo.buscar_productos(q)
        # Fallback si búsqueda literal no encuentra nada
        if not items:
            items = _catalog_repo.obtener_todos()

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

@ia_bp.post("/ticket")
def ia_ticket_create():
    """Crea un ticket de soporte y envía correo a los administradores.
    Body JSON: { message, email?, provider? }
    """
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or data.get("mensaje") or "").strip()
    if not message:
        return jsonify({"ok": False, "error": "message requerido"}), 400
    user_email = (data.get("email") or session.get("user_email") or None)
    provider = (data.get("provider") or "chat/ia")

    # Crear ticket en SQLite (persistente para logs internos)
    try:
        tid = _tickets.crear(
            question=message,
            user_email=user_email,
            provider=provider,
        )
    except Exception:
        current_app.logger.exception("Fallo creando ticket")
        return jsonify({"ok": False, "error": "No se pudo crear el ticket"}), 500

    # Notificar por correo a administradores (y opcionalmente al usuario)
    try:
        admins = list(getattr(current_app.config, "ADMIN_EMAILS", []) or [])
        if not admins:
            import os as _os
            raw = (_os.getenv("ADMIN_EMAILS") or _os.getenv("ADMIN_EMAIL") or "").strip()
            if raw:
                admins = [e.strip() for e in raw.split(",") if e.strip()]
        if admins:
            smtp = GoogleSMTPCliente()
            asunto = f"Nuevo ticket #{tid}"
            html = (
                f"<h3>Nuevo ticket</h3><p><strong>ID:</strong> {tid}</p>"
                f"<p><strong>Usuario:</strong> {user_email or '-'} &nbsp;&nbsp;<strong>Origen:</strong> {provider}</p>"
                f"<p><strong>Pregunta:</strong><br>{message}</p>"
                f"<p>Panel admin: <a href=\"{getattr(current_app.config,'APP_BASE_URL','')}/admin\">Abrir</a></p>"
            )
            for a in admins:
                try:
                    smtp.enviar_correo(destinatario=a, asunto=asunto, cuerpo_html=html)
                except Exception:
                    current_app.logger.exception("No se pudo enviar correo de ticket a %s", a)
        if user_email:
            try:
                smtp = GoogleSMTPCliente()
                smtp.enviar_correo(
                    destinatario=user_email,
                    asunto=f"Recibimos tu solicitud (ticket #{tid})",
                    cuerpo_html=f"<p>Tu solicitud fue registrada con ID <strong>#{tid}</strong>.</p><p>Mensaje:</p><blockquote>{message}</blockquote>",
                )
            except Exception:
                pass
    except Exception:
        current_app.logger.exception("Fallo notificando ticket por correo")

    return jsonify({"ok": True, "id": tid}), 201
# --- Pruebas rápidas ---
# IA:
# curl -s -X POST "$APP_BASE_URL/api/v1/ia/chat" \
#   -H "Content-Type: application/json" \
#   -d '{"message":"busco un libro de matemáticas para secundaria"}'
