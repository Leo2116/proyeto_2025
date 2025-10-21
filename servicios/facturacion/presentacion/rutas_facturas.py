from __future__ import annotations

from flask import Blueprint, request, jsonify, render_template, session as flask_session
from datetime import datetime
from sqlalchemy import text

from inicializar_db import resolve_db_uri, get_engine_and_session, FacturaORM, FacturaItemORM
from servicios.servicio_autenticacion.infraestructura.clientes_externos.google_smtp_cliente import GoogleSMTPCliente


facturas_bp = Blueprint("facturas_bp", __name__, url_prefix="/api/v1")


def _generar_numero_factura(session) -> str:
    hoy = datetime.now()
    base = f"FCT-{hoy.strftime('%Y%m%d')}"
    prefix = f"{base}-"
    # Cuenta existentes con el mismo prefijo y suma 1
    existentes = session.query(FacturaORM).filter(FacturaORM.numero_factura.like(f"{prefix}%")).count()
    sec = existentes + 1
    return f"{prefix}{sec:04d}"


def _normalize_nit(raw: str | None) -> str | None:
    """Normaliza/valida NIT.
    - Vacío => 'C/F'
    - 'CF'/'C/F' => 'C/F'
    - Numérico con guiones (3-20), sin espacios => tal cual
    - Cualquier espacio interno => inválido
    - Otro caso => None (inválido)
    """
    s = (raw or "").strip()
    if not s:
        return "C/F"
    s_up = s.upper()
    if s_up in ("C/F", "CF"):
        return "C/F"
    # Rechazar espacios en cualquier posición
    if any(ch.isspace() for ch in s):
        return None
    import re
    if re.fullmatch(r"^[0-9-]{3,20}$", s_up):
        return s
    return None


def _ensure_factura_columns(engine) -> None:
    """Agrega columnas extra si no existen (SQLite). Idempotente."""
    try:
        with engine.connect() as conn:
            res = conn.exec_driver_sql("PRAGMA table_info('facturas')")
            cols = [row[1] for row in res]
            def add(col, ddl):
                if col not in cols:
                    conn.exec_driver_sql(f"ALTER TABLE facturas ADD COLUMN {ddl}")
            add("nit", "nit TEXT")
            add("pago_metodo", "pago_metodo TEXT")
            add("entrega_metodo", "entrega_metodo TEXT")
            add("envio_nombre", "envio_nombre TEXT")
            add("envio_telefono", "envio_telefono TEXT")
            add("envio_direccion", "envio_direccion TEXT")
            add("origen", "origen TEXT")
    except Exception:
        pass


@facturas_bp.post("/facturas")
def crear_factura():
    data = request.get_json(silent=True) or {}
    items = data.get("items") or []
    email = data.get("email")
    nit = _normalize_nit(data.get("nit"))
    if nit is None:
        return jsonify({"error": "NIT inválido. Usa solo números (y guiones) o 'C/F'."}), 400
    # Extras de checkout
    pago = (data.get("pago") or {})
    pago_metodo = (pago.get("metodo") or data.get("pago_metodo") or "").strip() or None
    entrega = (data.get("entrega") or {})
    entrega_metodo = (entrega.get("metodo") or data.get("entrega_metodo") or "").strip() or None
    envio_nombre = (entrega.get("nombre") or data.get("envio_nombre") or None)
    envio_telefono = (entrega.get("telefono") or data.get("envio_telefono") or None)
    envio_direccion = (entrega.get("direccion") or data.get("envio_direccion") or None)
    origen = (data.get("origen") or "web").strip() or "web"

    if not isinstance(items, list) or not items:
        return jsonify({"error": "'items' es requerido y no puede estar vacío."}), 400

    # Calcular totales
    total = 0.0
    normalized = []
    for it in items:
        try:
            nombre = str(it.get("nombre") or "Producto")
            precio = float(it.get("precio") or 0)
            cantidad = int(it.get("cantidad") or 1)
            pid = it.get("id") or it.get("producto_id")
            if cantidad <= 0 or precio < 0:
                raise ValueError()
            subtotal = round(precio * cantidad, 2)
            total += subtotal
            normalized.append({
                "producto_id": pid,
                "nombre": nombre,
                "precio": precio,
                "cantidad": cantidad,
                "subtotal": subtotal,
            })
        except Exception:
            return jsonify({"error": "Item inválido en 'items'."}), 400

    db_uri = resolve_db_uri()
    engine, SessionLocal = get_engine_and_session(db_uri)
    _ensure_factura_columns(engine)
    session = SessionLocal()
    try:
        numero = _generar_numero_factura(session)
        fac = FacturaORM(
            numero_factura=numero,
            user_email=email,
            nit=nit,
            pago_metodo=pago_metodo,
            entrega_metodo=entrega_metodo,
            envio_nombre=envio_nombre,
            envio_telefono=envio_telefono,
            envio_direccion=envio_direccion,
            total=round(total, 2),
            origen=origen,
        )
        session.add(fac)
        session.flush()  # para obtener fac.id

        for it in normalized:
            session.add(FacturaItemORM(id_factura=fac.id, **it))

        session.commit()
        # Email de factura (opcional)
        if email:
            try:
                _enviar_factura_email(email=email, numero=fac.numero_factura, total=fac.total, nit=nit,
                                      items=normalized, pago_metodo=pago_metodo, entrega_metodo=entrega_metodo,
                                      envio_nombre=envio_nombre, envio_telefono=envio_telefono, envio_direccion=envio_direccion)
            except Exception:
                pass
        return jsonify({
            "id": fac.id,
            "numero_factura": fac.numero_factura,
            "nit": nit,
            "pago_metodo": pago_metodo,
            "entrega_metodo": entrega_metodo,
            "envio_nombre": envio_nombre,
            "envio_telefono": envio_telefono,
            "envio_direccion": envio_direccion,
            "origen": origen,
            "total": fac.total,
            "fecha": fac.fecha.isoformat() if fac.fecha else None,
        }), 201
    except Exception:
        session.rollback()
        return jsonify({"error": "Error al crear factura."}), 500
    finally:
        session.close()


@facturas_bp.get("/facturas/<int:fid>")
def obtener_factura(fid: int):
    db_uri = resolve_db_uri()
    engine, SessionLocal = get_engine_and_session(db_uri)
    _ensure_factura_columns(engine)
    session = SessionLocal()
    try:
        fac = session.query(FacturaORM).filter_by(id=fid).first()
        if not fac:
            return jsonify({"error": "Factura no encontrada."}), 404
        items = session.query(FacturaItemORM).filter_by(id_factura=fid).all()
        return jsonify({
            "id": fac.id,
            "numero_factura": fac.numero_factura,
            "user_email": fac.user_email,
            "nit": getattr(fac, "nit", None),
            "pago_metodo": getattr(fac, "pago_metodo", None),
            "entrega_metodo": getattr(fac, "entrega_metodo", None),
            "envio_nombre": getattr(fac, "envio_nombre", None),
            "envio_telefono": getattr(fac, "envio_telefono", None),
            "envio_direccion": getattr(fac, "envio_direccion", None),
            "origen": getattr(fac, "origen", None),
            "total": fac.total,
            "fecha": fac.fecha.isoformat() if fac.fecha else None,
            "items": [
                {
                    "id": it.id,
                    "producto_id": it.producto_id,
                    "nombre": it.nombre,
                    "precio": it.precio,
                    "cantidad": it.cantidad,
                    "subtotal": it.subtotal,
                }
                for it in items
            ],
        }), 200
    except Exception:
        return jsonify({"error": "Error al consultar factura."}), 500
    finally:
        session.close()


def _enviar_factura_email(*, email: str, numero: str, total: float, nit: str | None,
                          items: list[dict], pago_metodo: str | None,
                          entrega_metodo: str | None, envio_nombre: str | None,
                          envio_telefono: str | None, envio_direccion: str | None) -> None:
    cliente = GoogleSMTPCliente()
    filas = ''.join(
        f"<tr><td>{(it.get('nombre') or 'Producto')}</td><td style='text-align:right'>Q{float(it.get('precio') or 0):.2f}</td><td style='text-align:center'>{int(it.get('cantidad') or 1)}</td><td style='text-align:right'>Q{float(it.get('subtotal') or 0):.2f}</td></tr>"
        for it in items
    )
    ent = (f"<p><strong>Entrega:</strong> {entrega_metodo or '-'}" +
           (f"<br><strong>Nombre:</strong> {envio_nombre or ''}<br><strong>Teléfono:</strong> {envio_telefono or ''}<br><strong>Dirección:</strong> {envio_direccion or ''}" if (entrega_metodo == 'domicilio') else "") +
           "</p>")
    html = f"""
    <h2>Factura {numero}</h2>
    <p><strong>NIT:</strong> {nit or 'C/F'} &nbsp; | &nbsp; <strong>Método de pago:</strong> {pago_metodo or '-'} </p>
    {ent}
    <table border='1' cellspacing='0' cellpadding='6' style='border-collapse:collapse;width:100%'>
      <thead><tr><th>Producto</th><th>Precio</th><th>Cant.</th><th>Subtotal</th></tr></thead>
      <tbody>{filas}</tbody>
    </table>
    <p style='text-align:right;font-size:1.1rem'><strong>Total: Q{float(total):.2f}</strong></p>
    """
    cliente.enviar_email(para=email, asunto=f"Factura {numero}", html=html, texto_plano=f"Factura {numero} Total Q{float(total):.2f}")


@facturas_bp.get("/facturas/print/<int:fid>")
def imprimir_factura(fid: int):
    """Vista HTML imprimible para guardar como PDF desde el navegador."""
    db_uri = resolve_db_uri()
    engine, SessionLocal = get_engine_and_session(db_uri)
    _ensure_factura_columns(engine)
    session = SessionLocal()
    try:
        fac = session.query(FacturaORM).filter_by(id=fid).first()
        if not fac:
            return "Factura no encontrada", 404
        items = session.query(FacturaItemORM).filter_by(id_factura=fid).all()
        return render_template("factura_print.html", fac=fac, items=items)
    except Exception:
        return "Error al generar vista de factura", 500
    finally:
        session.close()


@facturas_bp.get("/facturas")
def listar_facturas():
    """Lista facturas por email (querystring) o por sesión de usuario, con filtro por fecha.

    Query params:
      - email (opcional)
      - from (YYYY-MM-DD opcional)
      - to   (YYYY-MM-DD opcional, inclusivo)
      - page (1..n)  por defecto 1
      - limit (1..50) por defecto 10
    """
    email = (request.args.get("email") or (flask_session.get("user_email") if flask_session else None))
    page = max(1, int(request.args.get("page", 1) or 1))
    limit = max(1, min(int(request.args.get("limit", 10) or 10), 50))
    from_q = (request.args.get("from") or request.args.get("desde") or "").strip()
    to_q = (request.args.get("to") or request.args.get("hasta") or "").strip()

    db_uri = resolve_db_uri()
    engine, SessionLocal = get_engine_and_session(db_uri)
    _ensure_factura_columns(engine)
    session = SessionLocal()
    try:
        q = session.query(FacturaORM)
        if email:
            q = q.filter(FacturaORM.user_email == email)
        # Filtro por rango de fechas (opcional)
        from_dt = None
        to_dt = None
        try:
            if from_q:
                from_dt = datetime.fromisoformat(from_q)
            if to_q:
                # Inclusivo: sumar un día y usar <
                to_dt = datetime.fromisoformat(to_q)
                to_dt = to_dt.replace(hour=23, minute=59, second=59)
        except Exception:
            from_dt = None; to_dt = None
        if from_dt:
            q = q.filter(FacturaORM.fecha >= from_dt)
        if to_dt:
            q = q.filter(FacturaORM.fecha <= to_dt)
        total = q.count()
        rows = q.order_by(FacturaORM.id.desc()).offset((page - 1) * limit).limit(limit).all()
        out = []
        for fac in rows:
            out.append({
                "id": fac.id,
                "numero_factura": fac.numero_factura,
                "user_email": fac.user_email,
                "nit": fac.nit,
                "pago_metodo": fac.pago_metodo,
                "entrega_metodo": fac.entrega_metodo,
                "total": fac.total,
                "fecha": fac.fecha.isoformat() if fac.fecha else None,
                "origen": fac.origen,
                "print_url": f"/api/v1/facturas/print/{fac.id}",
            })
        return jsonify({"items": out, "total": total, "page": page, "limit": limit}), 200
    except Exception:
        return jsonify({"error": "Error al listar facturas."}), 500
    finally:
        session.close()


    
