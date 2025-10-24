from __future__ import annotations

from typing import List, Dict, Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from configuracion import Config
from inicializar_db import Base, ProductoORM, TipoProductoEnum
from servicios.admin.infraestructura.productos_repo import AdminProductosRepo


def migrate_sqlite_admin_to_postgres() -> Dict[str, Any]:
    """
    Copia productos del admin (SQLite) hacia Postgres (tabla 'productos').
    - Mapea campos equivalentes.
    - Upsert simple por id (reemplaza si existe).
    """
    src = AdminProductosRepo()
    src.ensure_schema()
    items: List[Dict[str, Any]] = src.listar(incluir_eliminados=True)

    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, future=True)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(engine)
    created = 0
    updated = 0
    with Session() as s:
        for it in items:
            pid = str(it.get('id') or '').strip()
            if not pid:
                continue
            nombre = it.get('nombre')
            precio = float(it.get('precio') or 0)
            tipo = (it.get('tipo') or 'UtilEscolar').strip()
            # Map a enum
            tipo_enum = TipoProductoEnum.LIBRO if tipo == 'Libro' else TipoProductoEnum.UTIL
            portada = it.get('portada_url')
            stock = int(it.get('stock') or 0)
            autor = None
            isbn = None
            material = None
            categoria = None
            if tipo == 'Libro':
                autor = it.get('autor_marca')
                isbn = it.get('isbn_sku')
            elif tipo == 'UtilEscolar':
                material = it.get('material') or None
                categoria = it.get('categoria') or None

            existing = s.get(ProductoORM, pid)
            if existing:
                existing.nombre = nombre
                existing.precio = precio
                existing.stock = stock
                existing.imagen_url = portada
                existing.tipo = tipo_enum
                existing.autor = autor
                existing.isbn = isbn
                existing.material = material
                existing.categoria = categoria
                updated += 1
            else:
                s.add(ProductoORM(
                    id_producto=pid,
                    nombre=nombre,
                    precio=precio,
                    stock=stock,
                    imagen_url=portada,
                    tipo=tipo_enum,
                    autor=autor,
                    isbn=isbn,
                    material=material,
                    categoria=categoria,
                ))
                created += 1
        s.commit()
    return {"created": created, "updated": updated, "total": len(items)}

