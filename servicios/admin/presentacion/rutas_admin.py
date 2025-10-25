from __future__ import annotations

from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine, text
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

    # Intentar crear en Postgres (Neon); fallback a SQLite admin
    try:
        db_url = getattr(Config, "SQLALCHEMY_DATABASE_URI", None)
        if db_url:
            engine = create_engine(db_url, future=True)
            with engine.begin() as conn:
                row = conn.execute(text("SELECT COALESCE(MAX(CAST(id_producto AS INTEGER)),0)+1 FROM productos")).first()
                pid = str(int(row[0]))
                tipo = 'LIBRO' if data.get('tipo')=='Libro' else 'UTIL'
                conn.execute(text(
                    """
                    INSERT INTO productos (id_producto,nombre,precio,stock,tipo,autor,isbn,material,categoria,imagen_url)
                    VALUES (:id,:nombre,:precio,:stock,:tipo,:autor,:isbn,:material,:categoria,:img)
                    """
                ), {
                    'id': pid,
                    'nombre': data.get('nombre'),
                    'precio': float(data.get('precio') or 0),
                    'stock': int(data.get('stock') or 0),
                    'tipo': tipo,
                    'autor': data.get('autor_marca') if data.get('tipo')=='Libro' else None,
                    'isbn': data.get('isbn_sku') if data.get('tipo')=='Libro' else None,
                    'material': data.get('material') if data.get('tipo')=='UtilEscolar' else None,
                    'categoria': data.get('categoria') if data.get('tipo')=='UtilEscolar' else None,
                    'img': data.get('portada_url')
                })
                return jsonify({"ok": True, "id": pid}), 201
    except Exception:
        pass
    try:
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
    # Intentar actualizar en Postgres (Neon); fallback a SQLite
    try:
        db_url = getattr(Config, "SQLALCHEMY_DATABASE_URI", None)
        if db_url:
            engine = create_engine(db_url, future=True)
            with engine.begin() as conn:
                fields = {
                    'nombre': data.get('nombre'),
                    'precio': float(data.get('precio')) if ('precio' in data) else None,
                    'stock': int(data.get('stock')) if ('stock' in data) else None,
                    'imagen_url': data.get('portada_url'),
                }
                if data.get('tipo')=='Libro':
                    fields.update({'tipo': 'LIBRO', 'autor': data.get('autor_marca'), 'isbn': data.get('isbn_sku'), 'material': None, 'categoria': None})
                elif data.get('tipo')=='UtilEscolar':
                    fields.update({'tipo': 'UTIL', 'autor': None, 'isbn': None, 'material': data.get('material'), 'categoria': data.get('categoria')})
                sets = ",".join([f"{k} = :{k}" for k,v in fields.items() if v is not None])
                if sets:
                    params = {k:v for k,v in fields.items() if v is not None}
                    params['id'] = pid
                    conn.execute(text(f"UPDATE productos SET {sets} WHERE id_producto = :id"), params)
                return jsonify({"ok": True, "id": pid}), 200
    except Exception:
        pass
    if not _repo.existe(pid):
        return jsonify({"error": "No existe"}), 404
    _repo.actualizar(pid, data)
    return jsonify({"ok": True, "id": pid}), 200


@admin_bp.delete("/productos/<string:pid>")
def admin_eliminar_producto(pid: str):
    if not _is_admin():
        return jsonify({"error": "No autorizado"}), 403
    try:
        db_url = getattr(Config, "SQLALCHEMY_DATABASE_URI", None)
        if db_url:
            engine = create_engine(db_url, future=True)
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM productos WHERE id_producto = :id"), {"id": pid})
                return jsonify({"ok": True}), 200
    except Exception:
        pass
    _repo.eliminar(pid)
    return jsonify({"ok": True}), 200


# ---------------- Catálogos (categorías/materiales) -----------------

@admin_bp.get("/catalog/categories")
def admin_list_categories():
    if not _is_admin_request():
        return jsonify({"error": "No autorizado"}), 403
    try:
        # Preferir Postgres si está disponible
        db_url = getattr(Config, "SQLALCHEMY_DATABASE_URI", None)
        if db_url:
            engine = create_engine(db_url, future=True)
            with engine.connect() as conn:
                rows = conn.execute(text("SELECT id, nombre FROM catalog_categorias ORDER BY nombre ASC")).fetchall()
                return jsonify([{"id": int(r[0]), "nombre": r[1]} for r in rows]), 200
        # Fallback a SQLite admin
        return jsonify(_repo.listar_categorias()), 200
    except Exception:
        return jsonify([]), 200


@admin_bp.post("/catalog/categories")
def admin_create_category():
    if not _is_admin_request():
        return jsonify({"error": "No autorizado"}), 403
    body = request.get_json(silent=True) or {}
    name = (body.get("nombre") or body.get("name") or "").strip()
    if not name:
        return jsonify({"error": "'nombre' es requerido"}), 400
    try:
        db_url = getattr(Config, "SQLALCHEMY_DATABASE_URI", None)
        if db_url:
            engine = create_engine(db_url, future=True)
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO catalog_categorias(nombre) VALUES (:n) ON CONFLICT (nombre) DO NOTHING"), {"n": name})
                row = conn.execute(text("SELECT id FROM catalog_categorias WHERE nombre=:n"), {"n": name}).first()
                return jsonify({"ok": True, "id": int(row[0]) if row else None, "nombre": name}), 201
        cid = _repo.get_or_create_categoria(name)
        return jsonify({"ok": True, "id": cid, "nombre": name}), 201
    except Exception:
        return jsonify({"error": "No se pudo crear"}), 500


@admin_bp.get("/catalog/materials")
def admin_list_materials():
    if not _is_admin_request():
        return jsonify({"error": "No autorizado"}), 403
    try:
        db_url = getattr(Config, "SQLALCHEMY_DATABASE_URI", None)
        if db_url:
            engine = create_engine(db_url, future=True)
            with engine.connect() as conn:
                rows = conn.execute(text("SELECT id, nombre FROM catalog_materiales ORDER BY nombre ASC")).fetchall()
                return jsonify([{"id": int(r[0]), "nombre": r[1]} for r in rows]), 200
        return jsonify(_repo.listar_materiales()), 200
    except Exception:
        return jsonify([]), 200


@admin_bp.post("/catalog/materials")
def admin_create_material():
    if not _is_admin_request():
        return jsonify({"error": "No autorizado"}), 403
    body = request.get_json(silent=True) or {}
    name = (body.get("nombre") or body.get("name") or "").strip()
    if not name:
        return jsonify({"error": "'nombre' es requerido"}), 400
    try:
        db_url = getattr(Config, "SQLALCHEMY_DATABASE_URI", None)
        if db_url:
            engine = create_engine(db_url, future=True)
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO catalog_materiales(nombre) VALUES (:n) ON CONFLICT (nombre) DO NOTHING"), {"n": name})
                row = conn.execute(text("SELECT id FROM catalog_materiales WHERE nombre=:n"), {"n": name}).first()
                return jsonify({"ok": True, "id": int(row[0]) if row else None, "nombre": name}), 201
        mid = _repo.get_or_create_material(name)
        return jsonify({"ok": True, "id": mid, "nombre": name}), 201
    except Exception:
        return jsonify({"error": "No se pudo crear"}), 500


# ---------------- Upload de imágenes -----------------

@admin_bp.post("/upload")
def admin_upload_image():
    if not _is_admin_request():
        return jsonify({"error": "No autorizado"}), 403
    if 'file' not in request.files:
        return jsonify({"error": "archivo 'file' es requerido (multipart/form-data)"}), 400
    f = request.files['file']
    if not f or f.filename == '':
        return jsonify({"error": "Archivo vacío"}), 400
    # Aceptar imágenes comunes
    allowed = {'.png', '.jpg', '.jpeg', '.webp'}
    ext = ('.' + f.filename.rsplit('.', 1)[-1].lower()) if '.' in f.filename else ''
    if ext not in allowed:
        return jsonify({"error": "Formato no permitido"}), 400
    try:
        from pathlib import Path
        from configuracion import Config
        base_dir = Path(__file__).resolve().parents[3]
        img_dir = base_dir / 'static' / 'img' / 'productos'
        img_dir.mkdir(parents=True, exist_ok=True)
        fname = secure_filename(f.filename)
        # Evitar sobrescribir: si existe, añade sufijo incremental
        dest = img_dir / fname
        if dest.exists():
            stem = dest.stem
            i = 1
            while True:
                alt = img_dir / f"{stem}_{i}{dest.suffix}"
                if not alt.exists():
                    dest = alt
                    break
                i += 1
        f.save(str(dest))
        url = f"/static/img/productos/{dest.name}"
        return jsonify({"ok": True, "url": url}), 201
    except Exception:
        current_app.logger.exception("Upload fallo")
        return jsonify({"error": "No se pudo subir"}), 500


# ---------------- Importar elementos de vitrina a DB -----------------

@admin_bp.post("/import/static-products")
def admin_import_from_static():
    if not _is_admin_request():
        return jsonify({"error": "No autorizado"}), 403
    try:
        from pathlib import Path
        from servicios.servicio_catalogo.presentacion.rutas import PRECIOS_ESPECIFICOS
        base_dir = Path(__file__).resolve().parents[3]
        img_dir = base_dir / 'static' / 'img' / 'productos'
        count = _repo.importar_desde_static(img_dir, PRECIOS_ESPECIFICOS)
        return jsonify({"ok": True, "importados": count}), 200
    except Exception:
        current_app.logger.exception("Import static-products fallo")
        return jsonify({"error": "No se pudo importar"}), 500


# ---------------- Migración SQLite → Postgres -----------------

@admin_bp.post("/migrate/sqlite-to-pg")
def admin_migrate_sqlite_to_pg():
    if not _is_admin_request():
        return jsonify({"error": "No autorizado"}), 403
    try:
        from servicios.admin.infraestructura.pg_migrator import migrate_sqlite_admin_to_postgres
        result = migrate_sqlite_admin_to_postgres()
        return jsonify({"ok": True, **result}), 200
    except Exception as e:
        current_app.logger.exception("Migración SQLite→PG fallo")
        return jsonify({"error": "No se pudo migrar", "detail": str(e)}), 500


# ---------------- Estado Neon (conteos) -----------------

@admin_bp.get("/neon-status")
def admin_neon_status():
    if not _is_admin_request():
        return jsonify({"error": "No autorizado"}), 403
    try:
        db_url = getattr(Config, "SQLALCHEMY_DATABASE_URI", None)
        if not db_url:
            return jsonify({"ok": False, "message": "Sin SQLALCHEMY_DATABASE_URI"}), 200
        engine = create_engine(db_url, future=True)
        with engine.connect() as conn:
            cnt = conn.execute(text("SELECT COUNT(1) FROM productos")).scalar() or 0
            cats = 0
            mats = 0
            try:
                cats = conn.execute(text("SELECT COUNT(1) FROM catalog_categorias")).scalar() or 0
                mats = conn.execute(text("SELECT COUNT(1) FROM catalog_materiales")).scalar() or 0
            except Exception:
                pass
            head = None
            try:
                row = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).first()
                head = row[0] if row else None
            except Exception:
                pass
        return jsonify({"ok": True, "productos": int(cnt), "categorias": int(cats), "materiales": int(mats), "alembic_head": head}), 200
    except Exception:
        current_app.logger.exception("neon-status fallo")
        return jsonify({"ok": False, "message": "error"}), 500


# ---------------- Importar vitrina → Postgres directo -----------------

@admin_bp.post("/import/static-products-to-pg")
def admin_import_static_to_pg():
    if not _is_admin_request():
        return jsonify({"error": "No autorizado"}), 403
    try:
        from pathlib import Path
        from servicios.servicio_catalogo.presentacion.rutas import PRECIOS_ESPECIFICOS
        db_url = getattr(Config, "SQLALCHEMY_DATABASE_URI", None)
        if not db_url:
            return jsonify({"error": "Sin SQLALCHEMY_DATABASE_URI"}), 400
        engine = create_engine(db_url, future=True)
        img_dir = Path(__file__).resolve().parents[3] / 'static' / 'img' / 'productos'
        exts = {'.png', '.jpg', '.jpeg', '.webp'}
        created = 0
        with engine.begin() as conn:
            for file in sorted(img_dir.iterdir()):
                if not file.is_file() or file.suffix.lower() not in exts:
                    continue
                stem = file.stem
                nombre = stem.replace('_', ' ').replace('-', ' ').strip().title()
                precio = float(PRECIOS_ESPECIFICOS.get(stem.lower(), 10.0))
                # Insertar si no existe
                conn.execute(text(
                    """
                    INSERT INTO productos (id_producto,nombre,precio,stock,tipo,autor,isbn,material,categoria,imagen_url)
                    VALUES (:id,:nombre,:precio,:stock,'UTIL',NULL,NULL,NULL,NULL,:img)
                    ON CONFLICT (id_producto) DO NOTHING
                    """
                ), {"id": stem, "nombre": nombre, "precio": precio, "stock": 0, "img": f"/static/img/productos/{file.name}"})
                created += 1
        return jsonify({"ok": True, "importados": created}), 200
    except Exception:
        current_app.logger.exception("import static to pg fallo")
        return jsonify({"error": "No se pudo importar a PG"}), 500


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


