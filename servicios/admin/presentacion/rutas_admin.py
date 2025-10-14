from __future__ import annotations

from flask import Blueprint, request, jsonify, session
from pathlib import Path
import sqlite3
from typing import Any, Dict

from configuracion import Config


admin_bp = Blueprint("admin_bp", __name__, url_prefix="/api/v1/admin")

# Ruta de la base de datos del catálogo (la misma que usa el servicio del catálogo)
BASE_DIR = Path(__file__).resolve().parents[3]
CATALOGO_DB = BASE_DIR / "data" / "catalogo.db"
CATALOGO_DB.parent.mkdir(parents=True, exist_ok=True)


def _is_admin() -> bool:
    email = (session.get("user_email") or "").lower().strip()
    return bool(email and (email in (Config.ADMIN_EMAILS or [])))


def _conn():
    conn = sqlite3.connect(str(CATALOGO_DB))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema():
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS productos (
              id TEXT PRIMARY KEY,
              nombre TEXT NOT NULL,
              precio REAL NOT NULL,
              tipo TEXT NOT NULL CHECK (tipo IN ('Libro','UtilEscolar','Producto')),
              atributo_extra_1 TEXT,  -- autor (Libro) / marca (UtilEscolar)
              atributo_extra_2 TEXT,  -- isbn  (Libro) / sku   (UtilEscolar)
              sinopsis TEXT,
              portada_url TEXT
            )
            """
        )


@admin_bp.before_app_request
def _warmup_schema():
    # Garantiza que la tabla exista cuando se use el admin
    try:
        _ensure_schema()
    except Exception:
        pass


@admin_bp.get("/check")
def admin_check():
    return jsonify({"admin": _is_admin()}), 200


@admin_bp.get("/productos")
def admin_listar_productos():
    if not _is_admin():
        return jsonify({"error": "No autorizado"}), 403
    with _conn() as c:
        rows = c.execute("SELECT * FROM productos ORDER BY nombre ASC").fetchall()
        data = []
        for r in rows:
            data.append({
                "id": r["id"],
                "nombre": r["nombre"],
                "precio": r["precio"],
                "tipo": r["tipo"],
                "autor_marca": r["atributo_extra_1"],
                "isbn_sku": r["atributo_extra_2"],
                "sinopsis": r["sinopsis"],
                "portada_url": r["portada_url"],
            })
        return jsonify(data), 200


def _validate_payload(payload: Dict[str, Any], is_update: bool = False):
    nombre = (payload.get("nombre") or "").strip()
    tipo = (payload.get("tipo") or "").strip() or "Producto"
    precio = float(payload.get("precio") or 0)
    autor_marca = (payload.get("autor_marca") or "").strip() or None
    isbn_sku = (payload.get("isbn_sku") or "").strip() or None
    sinopsis = (payload.get("sinopsis") or None)
    portada_url = (payload.get("portada_url") or None)

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
        "sinopsis": sinopsis,
        "portada_url": portada_url,
    }, None


@admin_bp.post("/productos")
def admin_crear_producto():
    if not _is_admin():
        return jsonify({"error": "No autorizado"}), 403
    payload = request.get_json(silent=True) or {}
    data, err = _validate_payload(payload)
    if err:
        return jsonify({"error": err}), 400

    # ID: usa el que venga o genera uno simple a partir de nombre
    pid = (payload.get("id") or data["nombre"].lower().replace(" ", "_")).strip()
    with _conn() as c:
        try:
            c.execute(
                """
                INSERT INTO productos (id, nombre, precio, tipo, atributo_extra_1, atributo_extra_2, sinopsis, portada_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pid,
                    data["nombre"],
                    data["precio"],
                    data["tipo"],
                    data["autor_marca"],
                    data["isbn_sku"],
                    data["sinopsis"],
                    data["portada_url"],
                ),
            )
            return jsonify({"ok": True, "id": pid}), 201
        except sqlite3.IntegrityError:
            return jsonify({"error": "ID ya existe"}), 409


@admin_bp.put("/productos/<string:pid>")
def admin_actualizar_producto(pid: str):
    if not _is_admin():
        return jsonify({"error": "No autorizado"}), 403
    payload = request.get_json(silent=True) or {}
    data, err = _validate_payload(payload, is_update=True)
    if err:
        return jsonify({"error": err}), 400
    with _conn() as c:
        cur = c.execute("SELECT COUNT(1) AS n FROM productos WHERE id = ?", (pid,)).fetchone()
        if not cur or (cur[0] or 0) == 0:
            return jsonify({"error": "No existe"}), 404
        c.execute(
            """
            UPDATE productos
              SET nombre = COALESCE(?, nombre),
                  precio = COALESCE(?, precio),
                  tipo = COALESCE(?, tipo),
                  atributo_extra_1 = COALESCE(?, atributo_extra_1),
                  atributo_extra_2 = COALESCE(?, atributo_extra_2),
                  sinopsis = COALESCE(?, sinopsis),
                  portada_url = COALESCE(?, portada_url)
            WHERE id = ?
            """,
            (
                data["nombre"] or None,
                data["precio"] if payload.get("precio") is not None else None,
                data["tipo"] or None,
                data["autor_marca"],
                data["isbn_sku"],
                data["sinopsis"],
                data["portada_url"],
                pid,
            ),
        )
        return jsonify({"ok": True, "id": pid}), 200


@admin_bp.delete("/productos/<string:pid>")
def admin_eliminar_producto(pid: str):
    if not _is_admin():
        return jsonify({"error": "No autorizado"}), 403
    with _conn() as c:
        c.execute("DELETE FROM productos WHERE id = ?", (pid,))
        return jsonify({"ok": True}), 200

