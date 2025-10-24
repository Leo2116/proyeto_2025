from __future__ import annotations

from flask import Blueprint, request, jsonify, session, current_app
import os
import unicodedata

from servicios.ia.chat_service import generar_respuesta_catalogo
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


# --- Pruebas rápidas ---
# IA:
# curl -s -X POST "$APP_BASE_URL/api/v1/ia/chat" \
#   -H "Content-Type: application/json" \
#   -d '{"message":"busco un libro de matemáticas para secundaria"}'

