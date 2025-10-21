# servicios/servicio_catalogo/infraestructura/persistencia/sqlite_repositorio_producto.py
import sqlite3
from typing import List, Optional

from servicios.servicio_catalogo.dominio.producto import Producto, Libro, UtilEscolar
from servicios.servicio_catalogo.aplicacion.repositorios.repositorio_producto_interface import IRepositorioProducto


class SQLiteRepositorioProducto(IRepositorioProducto):
    """
    Repositorio de productos con sqlite3.

    Esquema esperado de la tabla `productos`:
      id TEXT PRIMARY KEY,
      nombre TEXT NOT NULL,
      precio REAL NOT NULL,
      tipo TEXT NOT NULL CHECK (tipo IN ('Libro','UtilEscolar','Producto')),
      atributo_extra_1 TEXT,   -- autor (Libro) / marca (UtilEscolar)
      atributo_extra_2 TEXT,   -- isbn  (Libro) / sku   (UtilEscolar)
      sinopsis TEXT,
      portada_url TEXT
    """

    def __init__(self, db_path: str = "data/catalogo.db"):
        self.db_path = db_path

    # --------------------------- utilidades ---------------------------
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _reconstruir(self, row: sqlite3.Row) -> Producto:
        tipo = row["tipo"]
        if tipo == "Libro":
            return Libro(
                id=row["id"],
                nombre=row["nombre"],
                precio=row["precio"],
                isbn=row["atributo_extra_2"],
                autor=row["atributo_extra_1"],
                sinopsis=row["sinopsis"],
                portada_url=row["portada_url"],
            )
        if tipo == "UtilEscolar":
            return UtilEscolar(
                id=row["id"],
                nombre=row["nombre"],
                precio=row["precio"],
                sku=row["atributo_extra_2"],
                marca=row["atributo_extra_1"],
            )
        # Fallback genérico
        return Producto(id=row["id"], nombre=row["nombre"], precio=row["precio"])

    # ===================== MÉTODOS ABSTRACTOS (OBLIGATORIOS) =====================

    def buscar_productos(self, consulta: str) -> List[Producto]:
        like = f"%{consulta}%"
        with self._conn() as c:
            rows = c.execute(
                """
                SELECT * FROM productos
                WHERE nombre LIKE ?
                   OR atributo_extra_1 LIKE ?
                   OR atributo_extra_2 LIKE ?
                ORDER BY (created_at IS NULL), created_at DESC, rowid DESC
                """,
                (like, like, like),
            ).fetchall()
        return [self._reconstruir(r) for r in rows]

    def guardar_producto(self, p: Producto) -> None:
        with self._conn() as c:
            if isinstance(p, Libro):
                c.execute(
                    """
                    INSERT OR REPLACE INTO productos
                    (id, nombre, precio, tipo, atributo_extra_1, atributo_extra_2, sinopsis, portada_url)
                    VALUES (?, ?, ?, 'Libro', ?, ?, ?, ?)
                    """,
                    (p.id, p.nombre, p.precio, p.autor, p.isbn, getattr(p, "sinopsis", None), getattr(p, "portada_url", None)),
                )
            elif isinstance(p, UtilEscolar):
                c.execute(
                    """
                    INSERT OR REPLACE INTO productos
                    (id, nombre, precio, tipo, atributo_extra_1, atributo_extra_2, sinopsis, portada_url)
                    VALUES (?, ?, ?, 'UtilEscolar', ?, ?, NULL, NULL)
                    """,
                    (p.id, p.nombre, p.precio, p.marca, p.sku),
                )
            else:
                c.execute(
                    """
                    INSERT OR REPLACE INTO productos
                    (id, nombre, precio, tipo, atributo_extra_1, atributo_extra_2, sinopsis, portada_url)
                    VALUES (?, ?, ?, 'Producto', NULL, NULL, NULL, NULL)
                    """,
                    (p.id, p.nombre, p.precio),
                )

    def obtener_por_id(self, producto_id: str) -> Optional[Producto]:
        with self._conn() as c:
            row = c.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()
        return self._reconstruir(row) if row else None

    # ===================== CONVENIENCIA (COINCIDE CON TU CASO DE USO) ============

    def obtener_todos(self) -> List[Producto]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM productos ORDER BY (created_at IS NULL), created_at DESC, rowid DESC"
            ).fetchall()
        return [self._reconstruir(r) for r in rows]

    def buscar_por_consulta(self, consulta: str) -> List[Producto]:
        return self.buscar_productos(consulta)

    def buscar_por_id(self, producto_id: str) -> Optional[Producto]:
        return self.obtener_por_id(producto_id)
