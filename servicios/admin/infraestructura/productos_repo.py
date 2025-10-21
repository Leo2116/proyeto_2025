from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import sqlite3


BASE_DIR = Path(__file__).resolve().parents[3]
CATALOGO_DB = BASE_DIR / "data" / "catalogo.db"
CATALOGO_DB.parent.mkdir(parents=True, exist_ok=True)


class AdminProductosRepo:
    """
    Repositorio simple (SQLite) para productos administrables del panel.
    Extraído desde presentacion para cumplir SRP/DIP.
    """

    def _conn(self):
        conn = sqlite3.connect(str(CATALOGO_DB))
        conn.row_factory = sqlite3.Row
        return conn

    def ensure_schema(self) -> None:
        with self._conn() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS productos (
                  id TEXT PRIMARY KEY,
                  nombre TEXT NOT NULL,
                  precio REAL NOT NULL,
                  tipo TEXT NOT NULL CHECK (tipo IN ('Libro','UtilEscolar','Producto')),
                  atributo_extra_1 TEXT,
                  atributo_extra_2 TEXT,
                  sinopsis TEXT,
                  portada_url TEXT,
                  stock INTEGER NOT NULL DEFAULT 0,
                  eliminado INTEGER NOT NULL DEFAULT 0,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            # Secuencias para IDs autoincrementales
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS admin_sequences (
                  name TEXT PRIMARY KEY,
                  value INTEGER NOT NULL
                )
                """
            )
            # Inicializar secuencia si no existe, tomando el máximo ID numérico existente
            seq_row = c.execute("SELECT value FROM admin_sequences WHERE name = ?", ("productos_id",)).fetchone()
            if seq_row is None:
                max_row = c.execute("SELECT MAX(CAST(id AS INTEGER)) FROM productos WHERE id GLOB '[0-9]*'").fetchone()
                max_id = int(max_row[0]) if (max_row and max_row[0] is not None) else 0
                c.execute("INSERT INTO admin_sequences (name, value) VALUES (?, ?)", ("productos_id", max_id))
            # Catálogos enriquecidos (autores, editoriales, etc.)
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS catalog_autores (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nombre TEXT UNIQUE NOT NULL,
                  bio TEXT,
                  pais TEXT,
                  sitio_web TEXT,
                  notas TEXT
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS catalog_editoriales (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nombre TEXT UNIQUE NOT NULL,
                  pais TEXT,
                  sitio_web TEXT,
                  notas TEXT
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS catalog_isbns (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  codigo TEXT UNIQUE NOT NULL,
                  formato TEXT,
                  edicion TEXT,
                  anio INTEGER,
                  notas TEXT
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS catalog_paginas (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  cantidad INTEGER UNIQUE NOT NULL,
                  notas TEXT
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS catalog_materiales (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nombre TEXT UNIQUE NOT NULL,
                  descripcion TEXT
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS catalog_categorias (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nombre TEXT UNIQUE NOT NULL,
                  descripcion TEXT
                )
                """
            )

            # Migración ligera: agregar columnas si faltan
            cols = [r[1] for r in c.execute("PRAGMA table_info('productos')").fetchall()]
            if 'stock' not in cols:
                c.execute("ALTER TABLE productos ADD COLUMN stock INTEGER NOT NULL DEFAULT 0")
            if 'eliminado' not in cols:
                c.execute("ALTER TABLE productos ADD COLUMN eliminado INTEGER NOT NULL DEFAULT 0")
            for extra_col in ('autor_id','editorial_id','isbn_id','paginas_id','material_id','categoria_id','created_at','updated_at'):
                if extra_col not in cols:
                    if extra_col in ('created_at','updated_at'):
                        c.execute(f"ALTER TABLE productos ADD COLUMN {extra_col} DATETIME DEFAULT CURRENT_TIMESTAMP")
                    else:
                        c.execute(f"ALTER TABLE productos ADD COLUMN {extra_col} INTEGER")

    def _next_id(self) -> str:
        """Obtiene el siguiente ID autoincremental como string empezando en 1.
        Usa tabla admin_sequences para garantizar atomicidad.
        """
        with self._conn() as c:
            c.execute("BEGIN")
            row = c.execute("SELECT value FROM admin_sequences WHERE name = ?", ("productos_id",)).fetchone()
            if row is None:
                current = 0
                c.execute("INSERT INTO admin_sequences (name, value) VALUES (?, ?)", ("productos_id", current))
            else:
                current = int(row[0] or 0)
            new_value = current + 1
            c.execute("UPDATE admin_sequences SET value = ? WHERE name = ?", (new_value, "productos_id"))
            c.execute("COMMIT")
            return str(new_value)

    # CRUD ------------------------------------------------------
    def listar(self, *, incluir_eliminados: bool = False) -> List[Dict[str, Any]]:
        with self._conn() as c:
            if incluir_eliminados:
                rows = c.execute("SELECT * FROM productos ORDER BY (created_at IS NULL), created_at DESC, nombre ASC").fetchall()
            else:
                rows = c.execute("SELECT * FROM productos WHERE eliminado = 0 ORDER BY (created_at IS NULL), created_at DESC, nombre ASC").fetchall()
            return [
                {
                    "id": r["id"],
                    "nombre": r["nombre"],
                    "precio": r["precio"],
                    "tipo": r["tipo"],
                    "autor_marca": r["atributo_extra_1"],
                    "isbn_sku": r["atributo_extra_2"],
                    "sinopsis": r["sinopsis"],
                    "portada_url": r["portada_url"],
                    "stock": r["stock"],
                    "eliminado": r["eliminado"],
                }
                for r in rows
            ]

    def crear(self, pid: str, data: Dict[str, Any]) -> None:
        # Resolver y enlazar catálogos cuando aplique
        tipo = (data.get("tipo") or "").strip()
        autor_marca = (data.get("autor_marca") or None)
        isbn_sku = (data.get("isbn_sku") or None)
        editorial = (data.get("editorial") or None)
        paginas = data.get("paginas")
        material = (data.get("material") or None)
        categoria = (data.get("categoria") or None)

        autor_id = editorial_id = isbn_id = paginas_id = material_id = categoria_id = None
        if tipo == 'Libro':
            if autor_marca:
                autor_id = self.get_or_create_autor(autor_marca)
            if isbn_sku:
                isbn_id = self.get_or_create_isbn(isbn_sku)
            if editorial:
                editorial_id = self.get_or_create_editorial(editorial)
            try:
                if paginas is not None and str(paginas).strip() != '':
                    paginas_id = self.get_or_create_paginas(int(paginas))
            except Exception:
                paginas_id = None
        elif tipo == 'UtilEscolar':
            if material:
                material_id = self.get_or_create_material(material)
            if categoria:
                categoria_id = self.get_or_create_categoria(categoria)

        with self._conn() as c:
            c.execute(
                """
                INSERT INTO productos (
                  id, nombre, precio, tipo,
                  atributo_extra_1, atributo_extra_2,
                  sinopsis, portada_url, stock, eliminado,
                  autor_id, editorial_id, isbn_id, paginas_id, material_id, categoria_id
                ) VALUES (?,?,?,?,?,?,?,?,?,0,?,?,?,?,?,?)
                """,
                (
                    pid,
                    data.get("nombre"),
                    data.get("precio"),
                    tipo,
                    autor_marca,
                    isbn_sku,
                    data.get("sinopsis"),
                    data.get("portada_url"),
                    int(data.get("stock") or 0),
                    autor_id, editorial_id, isbn_id, paginas_id, material_id, categoria_id,
                ),
            )

    def crear_auto(self, data: Dict[str, Any]) -> str:
        """Crea un producto asignando ID automáticamente empezando desde 1.
        Retorna el ID generado como string.
        """
        pid = self._next_id()
        self.crear(pid, data)
        return pid

    def existe(self, pid: str) -> bool:
        with self._conn() as c:
            cur = c.execute("SELECT COUNT(1) FROM productos WHERE id = ?", (pid,)).fetchone()
            return bool(cur and (cur[0] or 0) > 0)

    def actualizar(self, pid: str, data: Dict[str, Any]) -> None:
        tipo = (data.get("tipo") or None)
        autor_marca = data.get("autor_marca")
        isbn_sku = data.get("isbn_sku")
        editorial = data.get("editorial")
        paginas = data.get("paginas")
        material = data.get("material")
        categoria = data.get("categoria")

        autor_id = editorial_id = isbn_id = paginas_id = material_id = categoria_id = None
        if tipo == 'Libro' or (autor_marca or isbn_sku or editorial or paginas is not None):
            if autor_marca:
                autor_id = self.get_or_create_autor(autor_marca)
            if isbn_sku:
                isbn_id = self.get_or_create_isbn(isbn_sku)
            if editorial:
                editorial_id = self.get_or_create_editorial(editorial)
            try:
                if paginas is not None and str(paginas).strip() != '':
                    paginas_id = self.get_or_create_paginas(int(paginas))
            except Exception:
                paginas_id = None
        if tipo == 'UtilEscolar' or (material or categoria):
            if material:
                material_id = self.get_or_create_material(material)
            if categoria:
                categoria_id = self.get_or_create_categoria(categoria)

        with self._conn() as c:
            c.execute(
                """
                UPDATE productos
                  SET nombre = COALESCE(?, nombre),
                      precio = COALESCE(?, precio),
                      tipo = COALESCE(?, tipo),
                      atributo_extra_1 = COALESCE(?, atributo_extra_1),
                      atributo_extra_2 = COALESCE(?, atributo_extra_2),
                      sinopsis = COALESCE(?, sinopsis),
                      portada_url = COALESCE(?, portada_url),
                      stock = COALESCE(?, stock),
                      autor_id = COALESCE(?, autor_id),
                      editorial_id = COALESCE(?, editorial_id),
                      isbn_id = COALESCE(?, isbn_id),
                      paginas_id = COALESCE(?, paginas_id),
                      material_id = COALESCE(?, material_id),
                      categoria_id = COALESCE(?, categoria_id),
                      updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    data.get("nombre") or None,
                    data.get("precio") if ("precio" in data) else None,
                    tipo or None,
                    autor_marca,
                    isbn_sku,
                    data.get("sinopsis"),
                    data.get("portada_url"),
                    int(data.get("stock")) if ("stock" in data) else None,
                    autor_id, editorial_id, isbn_id, paginas_id, material_id, categoria_id,
                    pid,
                ),
            )

    def eliminar(self, pid: str) -> None:
        # Soft delete: marcar eliminado = 1
        with self._conn() as c:
            c.execute("UPDATE productos SET eliminado = 1 WHERE id = ?", (pid,))

    def incrementar_stock(self, pid: str, cantidad: int) -> None:
        if not isinstance(cantidad, int):
            raise ValueError("cantidad debe ser entero")
        with self._conn() as c:
            c.execute("UPDATE productos SET stock = stock + ? WHERE id = ?", (cantidad, pid))

    # ---- Helpers de catálogos (get or create) ----
    def _get_or_create(self, table: str, key_col: str, value) -> int:
        with self._conn() as c:
            row = c.execute(f"SELECT id FROM {table} WHERE {key_col} = ?", (value,)).fetchone()
            if row:
                return int(row[0])
            c.execute(f"INSERT INTO {table} ({key_col}) VALUES (?)", (value,))
            new_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
            return int(new_id)

    def get_or_create_autor(self, nombre: str) -> int:
        return self._get_or_create('catalog_autores', 'nombre', nombre)

    def get_or_create_editorial(self, nombre: str) -> int:
        return self._get_or_create('catalog_editoriales', 'nombre', nombre)

    def get_or_create_isbn(self, codigo: str) -> int:
        return self._get_or_create('catalog_isbns', 'codigo', codigo)

    def get_or_create_paginas(self, cantidad: int) -> int:
        return self._get_or_create('catalog_paginas', 'cantidad', int(cantidad))

    def get_or_create_material(self, nombre: str) -> int:
        return self._get_or_create('catalog_materiales', 'nombre', nombre)

    def get_or_create_categoria(self, nombre: str) -> int:
        return self._get_or_create('catalog_categorias', 'nombre', nombre)
