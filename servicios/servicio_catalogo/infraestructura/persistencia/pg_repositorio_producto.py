# servicios/servicio_catalogo/infraestructura/persistencia/pg_repositorio_producto.py
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, or_, cast, String

from configuracion import Config
from inicializar_db import ProductoORM, TipoProductoEnum
from servicios.servicio_catalogo.dominio.producto import Producto, Libro, UtilEscolar
from servicios.servicio_catalogo.aplicacion.repositorios.repositorio_producto_interface import IRepositorioProducto


class PGRepositorioProducto(IRepositorioProducto):
    """Repositorio de productos usando SQLAlchemy y Postgres (Neon)."""

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or Config.SQLALCHEMY_DATABASE_URI
        self.engine = create_engine(self.db_url, future=True)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)

    # Utilidad: reconstruir dominio a partir de ORM
    def _to_domain(self, row: ProductoORM) -> Producto:
        if row.tipo == TipoProductoEnum.LIBRO:
            p = Libro(
                id=row.id_producto,
                nombre=row.nombre,
                precio=row.precio or 0.0,
                stock=row.stock or 0,
                isbn=row.isbn or '',
                autor=row.autor or 'Desconocido',
            )
            # Atributos extendidos usados en otras capas
            try:
                p.sinopsis = getattr(row, 'sinopsis', None)
                p.portada_url = row.imagen_url
            except Exception:
                pass
            return p
        else:
            p = UtilEscolar(
                id=row.id_producto,
                nombre=row.nombre,
                precio=row.precio or 0.0,
                stock=row.stock or 0,
                sku=row.id_producto,  # si no hay SKU dedicado, usamos el id
                categoria=row.categoria or '',
                marca='Generico',
            )
            try:
                p.portada_url = row.imagen_url
            except Exception:
                pass
            return p

    def buscar_productos(self, consulta: str) -> List[Producto]:
        consulta = (consulta or '').strip()
        with self.Session() as s:
            if not consulta:
                rows = s.query(ProductoORM).order_by(ProductoORM.id_producto.desc()).limit(50).all()
            else:
                like = f"%{consulta}%"
                rows = (
                    s.query(ProductoORM)
                    .filter(
                        or_(
                            ProductoORM.nombre.ilike(like),
                            cast(ProductoORM.isbn, String).ilike(like),
                            cast(ProductoORM.autor, String).ilike(like),
                            cast(ProductoORM.categoria, String).ilike(like),
                            cast(ProductoORM.material, String).ilike(like),
                        )
                    )
                    .order_by(ProductoORM.id_producto.desc())
                    .limit(50)
                    .all()
                )
        return [self._to_domain(r) for r in rows]

    def guardar_producto(self, p: Producto) -> None:
        with self.Session() as s:
            row = s.get(ProductoORM, p.id)
            if row is None:
                row = ProductoORM(id_producto=p.id, nombre=p.nombre, precio=p.precio, stock=getattr(p, 'stock', 0), tipo=(TipoProductoEnum.LIBRO if isinstance(p, Libro) else TipoProductoEnum.UTIL))
                s.add(row)
            else:
                row.nombre = p.nombre
                row.precio = p.precio
                row.stock = getattr(p, 'stock', row.stock)
            if isinstance(p, Libro):
                row.autor = getattr(p, 'autor', None)
                row.isbn = getattr(p, 'isbn', None)
            else:
                row.categoria = getattr(p, 'categoria', None)
                row.material = getattr(p, 'material', None)
            s.commit()

    def obtener_por_id(self, producto_id: str) -> Optional[Producto]:
        with self.Session() as s:
            row = s.get(ProductoORM, producto_id)
            return self._to_domain(row) if row else None

    def obtener_todos(self) -> List[Producto]:
        with self.Session() as s:
            rows = s.query(ProductoORM).order_by(ProductoORM.id_producto.desc()).limit(100).all()
        return [self._to_domain(r) for r in rows]

