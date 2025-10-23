from __future__ import annotations

from flask import Blueprint, request, jsonify, session
import os
import re
import requests
from typing import Any, Dict

from configuracion import Config
from utils.jwt import decode_jwt, JWTError
from servicios.admin.infraestructura.productos_repo import AdminProductosRepo
from servicios.admin.infraestructura.tickets_repo import TicketsRepo


admin_bp = Blueprint("admin_bp", __name__, url_prefix="/api/v1/admin")

_repo = AdminProductosRepo()
_tickets_repo = TicketsRepo()


def _is_admin() -> bool:
    email = (session.get("user_email") or "").lower().strip()
    return bool(email and (email in (Config.ADMIN_EMAILS or [])))


def _ensure_schema():
    _repo.ensure_schema()
    _tickets_repo.ensure_schema()


def _is_admin_request() -> bool:
    """Permite validar admin via JWT Bearer o via sesión como fallback."""
    auth = (request.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        try:
            payload = decode_jwt(token, getattr(Config, 'SECRET_KEY', ''))
            return bool(payload.get("is_admin"))
        except JWTError:
            return False
    return _is_admin()


@admin_bp.before_app_request
def _warmup_schema():
    try:
        _ensure_schema()
    except Exception:
        pass


@admin_bp.get("/check")
def admin_check():
    # Preferir JWT si viene en Authorization: Bearer
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        try:
            payload = decode_jwt(token, getattr(Config, 'SECRET_KEY', ''))
            return jsonify({"admin": bool(payload.get("is_admin"))}), 200
        except JWTError:
            return jsonify({"admin": False}), 200
    # Fallback compatibilidad: sesión + ADMIN_EMAILS
    return jsonify({"admin": _is_admin()}), 200


# ---------------- Tickets -----------------

@admin_bp.get("/tickets")
def admin_listar_tickets():
    if not _is_admin_request():
        return jsonify({"error": "No autorizado"}), 403
    status = request.args.get("status")
    page = int(request.args.get("page", "1") or 1)
    limit = int(request.args.get("limit", "50") or 50)
    data = _tickets_repo.listar(status=status, page=page, limit=limit)
    return jsonify(data), 200


@admin_bp.get("/tickets/<int:ticket_id>")
def admin_obtener_ticket(ticket_id: int):
    if not _is_admin_request():
        return jsonify({"error": "No autorizado"}), 403
    tk = _tickets_repo.obtener(ticket_id)
    if not tk:
        return jsonify({"error": "No existe"}), 404
    return jsonify(tk), 200


@admin_bp.post("/tickets/<int:ticket_id>/assign")
def admin_asignar_ticket(ticket_id: int):
    if not _is_admin_request():
        return jsonify({"error": "No autorizado"}), 403
    body = request.get_json(silent=True) or {}
    assigned_to = (body.get("assigned_to") or "").strip()
    if not assigned_to:
        return jsonify({"error": "'assigned_to' es requerido"}), 400
    assigned_by = (session.get("user_email") or "").strip() or None
    notes = (body.get("notes") or None)
    priority = (body.get("priority") or None)
    ok = _tickets_repo.asignar(ticket_id, assigned_to, assigned_by=assigned_by, notes=notes, priority=priority)
    if not ok:
        return jsonify({"error": "No se pudo asignar (ticket no existe?)"}), 404
    # Notificar por correo si assigned_to parece un email y SMTP está configurado
    try:
        if re.search(r"@", assigned_to):
            from servicios.servicio_autenticacion.infraestructura.clientes_externos.google_smtp_cliente import GoogleSMTPCliente
            smtp = GoogleSMTPCliente()
            asunto = f"Nuevo ticket asignado #{ticket_id}"
            detalle = _tickets_repo.obtener(ticket_id) or {}
            html = f"""
                <h3>Ticket asignado</h3>
                <p><strong>ID:</strong> {ticket_id}</p>
                <p><strong>Pregunta:</strong> { (detalle.get('question') or '')[:400] }</p>
                <p><strong>Estado:</strong> {detalle.get('status') or 'assigned'}</p>
                <p><strong>Prioridad:</strong> {priority or (detalle.get('priority') or 'normal')}</p>
                <p><strong>Notas:</strong> {notes or ''}</p>
                <hr>
                <p>Ir al panel: <a href="{getattr(Config, 'APP_BASE_URL', 'http://127.0.0.1:5000')}/admin">Administración</a></p>
            """
            smtp.enviar_correo(destinatario=assigned_to, asunto=asunto, cuerpo_html=html)
    except Exception:
        pass
    # Slack opcional
    try:
        webhook = os.getenv('SLACK_WEBHOOK_URL')
        if webhook:
            detalle = _tickets_repo.obtener(ticket_id) or {}
            text = f"Ticket #{ticket_id} asignado a {assigned_to}. Prioridad: {priority or detalle.get('priority') or 'normal'}."
            requests.post(webhook, json={"text": text}, timeout=5)
    except Exception:
        pass
    return jsonify({"ok": True}), 200


@admin_bp.post("/tickets/<int:ticket_id>/status")
def admin_actualizar_estado_ticket(ticket_id: int):
    if not _is_admin_request():
        return jsonify({"error": "No autorizado"}), 403
    body = request.get_json(silent=True) or {}
    status = (body.get("status") or "").strip()
    if status not in ("open", "assigned", "resolved", "closed"):
        return jsonify({"error": "status inválido"}), 400
    answer = body.get("answer")
    notes = body.get("notes")
    ok = _tickets_repo.actualizar_estado(ticket_id, status, answer=answer, notes=notes)
    if not ok:
        return jsonify({"error": "No se pudo actualizar"}), 404
    return jsonify({"ok": True}), 200


@admin_bp.get("/productos")
def admin_listar_productos():
    if not _is_admin():
        return jsonify({"error": "No autorizado"}), 403
    incluir_eliminados = (request.args.get("include_deleted") or "").lower() in ("1","true","yes")
    data = _repo.listar(incluir_eliminados=incluir_eliminados)
    return jsonify(data), 200


def _validate_payload(payload: Dict[str, Any], is_update: bool = False):
    nombre = (payload.get("nombre") or "").strip()
    tipo = (payload.get("tipo") or "").strip() or "Producto"
    precio = float(payload.get("precio") or 0)
    autor_marca = (payload.get("autor_marca") or "").strip() or None
    isbn_sku = (payload.get("isbn_sku") or "").strip() or None
    editorial = (payload.get("editorial") or "").strip() or None
    # páginas puede venir como número o string
    paginas = None
    try:
        if payload.get("paginas") not in (None, ""):
            paginas = int(payload.get("paginas"))
    except Exception:
        paginas = None
    material = (payload.get("material") or "").strip() or None
    categoria = (payload.get("categoria") or "").strip() or None
    sinopsis = (payload.get("sinopsis") or None)
    portada_url = (payload.get("portada_url") or None)
    stock = None
    try:
        if payload.get("stock") is not None:
            stock = int(payload.get("stock") or 0)
    except Exception:
        stock = None

    if not is_update:
        if not nombre:
            return None, "Falta 'nombre'"
        if precio < 0:
            return None, "Precio inválido"
        if tipo not in ("Libro", "UtilEscolar", "Producto"):
            return None, "Tipo inválido"

    return {
        "nombre": nombre,
        "tipo": tipo,
        "precio": precio,
        "autor_marca": autor_marca,
        "isbn_sku": isbn_sku,
        "editorial": editorial,
        "paginas": paginas,
        "material": material,
        "categoria": categoria,
        "sinopsis": sinopsis,
        "portada_url": portada_url,
        "stock": stock,
    }, None


@admin_bp.post("/productos")
def admin_crear_producto():
    if not _is_admin():
        return jsonify({"error": "No autorizado"}), 403
    payload = request.get_json(silent=True) or {}
    data, err = _validate_payload(payload)
    if err:
        return jsonify({"error": err}), 400

    try:
        # Generar ID automáticamente, comenzando desde 1
        pid = _repo.crear_auto(data)
        return jsonify({"ok": True, "id": pid}), 201
    except Exception:
        return jsonify({"error": "No se pudo crear"}), 500


@admin_bp.put("/productos/<string:pid>")
def admin_actualizar_producto(pid: str):
    if not _is_admin():
        return jsonify({"error": "No autorizado"}), 403
    payload = request.get_json(silent=True) or {}
    data, err = _validate_payload(payload, is_update=True)
    if err:
        return jsonify({"error": err}), 400
    if not _repo.existe(pid):
        return jsonify({"error": "No existe"}), 404
    _repo.actualizar(pid, data)
    return jsonify({"ok": True, "id": pid}), 200


@admin_bp.delete("/productos/<string:pid>")
def admin_eliminar_producto(pid: str):
    if not _is_admin():
        return jsonify({"error": "No autorizado"}), 403
    _repo.eliminar(pid)
    return jsonify({"ok": True}), 200


@admin_bp.post("/productos/<string:pid>/stock")
def admin_incrementar_stock(pid: str):
    if not _is_admin():
        return jsonify({"error": "No autorizado"}), 403
    body = request.get_json(silent=True) or {}
    try:
        cantidad = int(body.get("cantidad") or 0)
    except Exception:
        return jsonify({"error": "'cantidad' debe ser entero."}), 400
    if cantidad == 0:
        return jsonify({"error": "'cantidad' no puede ser 0."}), 400
    try:
        _repo.incrementar_stock(pid, cantidad)
        return jsonify({"ok": True, "id": pid, "delta": cantidad}), 200
    except Exception:
        return jsonify({"error": "No se pudo actualizar el stock."}), 500


@admin_bp.get("/diag")
def admin_diag():
    """Diagnóstico básico (solo admin): DB reachable, alembic head, claves presentes.
    No expone secretos ni datos sensibles.
    """
    if not _is_admin_request():
        return jsonify({"error": "No autorizado"}), 403
    # Datos base
    info = {
        "app_base_url": getattr(Config, "APP_BASE_URL", None),
        "recaptcha_site_key_len": len(getattr(Config, "RECAPTCHA_SITE_KEY", "") or ""),
        "hostname": request.host,
    }
    # DB checks
    try:
        from sqlalchemy import create_engine, text
        db_url = getattr(Config, "SQLALCHEMY_DATABASE_URI", None)
        engine = create_engine(db_url, future=True)
        with engine.connect() as conn:
            head = None
            try:
                res = conn.execute(text("select version_num from alembic_version limit 1"))
                row = res.first()
                head = row[0] if row else None
            except Exception:
                head = None
            who = conn.execute(text("select current_user, current_database(), current_schema()"))
            cu, cd, cs = who.first()
            info.update({
                "db_ok": True,
                "alembic_head": head,
                "db_user": cu,
                "db_name": cd,
                "db_schema": cs,
                "db_driver": engine.dialect.name,
            })
    except Exception as e:
        info.update({"db_ok": False, "db_error": str(e)})
    return jsonify(info), 200


@admin_bp.get("/diag_public")
def public_diag():
    """Diagnóstico básico público con token: /api/v1/admin/diag_public?token=XYZ
    Usa el env DIAG_TOKEN para autorizar; no expone secretos.
    """
    token = (request.args.get("token") or "").strip()
    expected = (os.getenv("DIAG_TOKEN") or "").strip()
    if not expected or token != expected:
        return jsonify({"error": "No autorizado"}), 403

    info = {
        "app_base_url": getattr(Config, "APP_BASE_URL", None),
        "recaptcha_site_key_len": len(getattr(Config, "RECAPTCHA_SITE_KEY", "") or ""),
        "hostname": request.host,
    }
    try:
        from sqlalchemy import create_engine, text
        db_url = getattr(Config, "SQLALCHEMY_DATABASE_URI", None)
        engine = create_engine(db_url, future=True)
        with engine.connect() as conn:
            head = None
            try:
                res = conn.execute(text("select version_num from alembic_version limit 1"))
                row = res.first()
                head = row[0] if row else None
            except Exception:
                head = None
            who = conn.execute(text("select current_user, current_database(), current_schema()"))
            cu, cd, cs = who.first()
            info.update({
                "db_ok": True,
                "alembic_head": head,
                "db_user": cu,
                "db_name": cd,
                "db_schema": cs,
                "db_driver": engine.dialect.name,
            })
    except Exception as e:
        info.update({"db_ok": False, "db_error": str(e)})
    return jsonify(info), 200

