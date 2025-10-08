from __future__ import annotations

from flask import Blueprint, request, jsonify
from datetime import datetime

from inicializar_db import resolve_db_uri, get_engine_and_session, FacturaORM, FacturaItemORM


facturas_bp = Blueprint("facturas_bp", __name__, url_prefix="/api/v1")


def _generar_numero_factura(session) -> str:
    hoy = datetime.now()
    base = f"FCT-{hoy.strftime('%Y%m%d')}"
    prefix = f"{base}-"
    # Cuenta existentes con el mismo prefijo y suma 1
    existentes = session.query(FacturaORM).filter(FacturaORM.numero_factura.like(f"{prefix}%")).count()
    sec = existentes + 1
    return f"{prefix}{sec:04d}"


@facturas_bp.post("/facturas")
def crear_factura():
    data = request.get_json(silent=True) or {}
    items = data.get("items") or []
    email = data.get("email")

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
    session = SessionLocal()
    try:
        numero = _generar_numero_factura(session)
        fac = FacturaORM(numero_factura=numero, user_email=email, total=round(total, 2))
        session.add(fac)
        session.flush()  # para obtener fac.id

        for it in normalized:
            session.add(FacturaItemORM(id_factura=fac.id, **it))

        session.commit()
        return jsonify({
            "id": fac.id,
            "numero_factura": fac.numero_factura,
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

