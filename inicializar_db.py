# inicializar_db.py

from __future__ import annotations

import enum
import os
from pathlib import Path

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Enum as SAEnum,
    Boolean,
    DateTime,
    func,
)
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError

try:
    # Si tu Config define SQLALCHEMY_DATABASE_URI, lo utilizamos
    from configuracion import Config
    DEFAULT_DB_URI = getattr(Config, "SQLALCHEMY_DATABASE_URI", None)
except Exception:
    Config = None
    DEFAULT_DB_URI = None

# ----------------------------------------------------------------------
# Base ORM
# ----------------------------------------------------------------------
Base = declarative_base()

# ----------------------------------------------------------------------
# Modelos ORM
# ----------------------------------------------------------------------
class TipoProductoEnum(enum.Enum):
    LIBRO = "Libro"
    UTIL = "UtilEscolar"


class ProductoORM(Base):
    """Tabla de productos (libros y útiles escolares)."""
    __tablename__ = "productos"

    id_producto = Column(String, primary_key=True)     # p.ej. 'UTIL001', 'LIB001'
    nombre = Column(String, nullable=False)
    precio = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    imagen_url = Column(String)                        # ruta pública a /static/...

    # tipo: Libro o UtilEscolar
    tipo = Column(SAEnum(
        TipoProductoEnum,
        name="tipo_producto_enum",
        native_enum=False,           # Para SQLite crea CHECK en lugar de tipo nativo
        validate_strings=True
    ), nullable=False)

    # Atributos específicos de LIBRO
    autor = Column(String, nullable=True)
    editorial = Column(String, nullable=True)
    isbn = Column(String, unique=True, nullable=True)  # útil para Google Books
    paginas = Column(Integer, nullable=True)

    # Atributos específicos de UTIL ESCOLAR
    material = Column(String, nullable=True)
    categoria = Column(String, nullable=True)          # 'Cuaderno', 'Bolígrafo', etc.


class LogisticaORM(Base):
    """Tabla de tarifas y tiempos de logística para Guatemala."""
    __tablename__ = "logistica_zonas"

    id = Column(Integer, primary_key=True)
    zona_nombre = Column(String, unique=True, nullable=False)
    tarifa_gtq = Column(Float, nullable=False)
    tiempo_estimado_dias = Column(Integer, nullable=False)


# =========  NUEVO: USUARIOS  =========
class UsuarioORM(Base):
    """
    Tabla de usuarios para autenticación.
    - id_usuario: UUID en string (lo generas en la capa de aplicación)
    - email: único
    - password_hash: hash pbkdf2_sha256 (passlib) u otro
    - verificado: para control de cuenta confirmada por email
    - token_verificacion: token temporal para enlace de verificación
    """
    __tablename__ = "usuarios"

    id_usuario = Column(String, primary_key=True)
    nombre = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)

    # Estado/flags
    activo = Column(Boolean, default=True, nullable=False)
    verificado = Column(Boolean, default=False, nullable=False)

    # Token de verificación por correo (opcional)
    token_verificacion = Column(String, nullable=True)

    # Timestamps básicos
    creado_en = Column(DateTime, server_default=func.now(), nullable=False)
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


# =========  NUEVO: FACTURACIÓN LOCAL  =========
class FacturaORM(Base):
    __tablename__ = "facturas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    numero_factura = Column(String, unique=True, nullable=False, index=True)
    user_email = Column(String, nullable=True)
    total = Column(Float, nullable=False, default=0.0)
    fecha = Column(DateTime, server_default=func.now(), nullable=False)


class FacturaItemORM(Base):
    __tablename__ = "factura_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_factura = Column(Integer, nullable=False, index=True)
    producto_id = Column(String, nullable=True)
    nombre = Column(String, nullable=False)
    precio = Column(Float, nullable=False, default=0.0)
    cantidad = Column(Integer, nullable=False, default=1)
    subtotal = Column(Float, nullable=False, default=0.0)


# ----------------------------------------------------------------------
# Helpers DB
# ----------------------------------------------------------------------
def resolve_db_uri() -> str:
    """
    Devuelve la URI de la base de datos a usar.
    1) Si Config.SQLALCHEMY_DATABASE_URI existe, usa esa.
    2) Si no, usa sqlite:///data/catalogo.db y crea carpeta data/ si no existe.
    """
    if DEFAULT_DB_URI:
        db_uri = DEFAULT_DB_URI
    else:
        # Por defecto: <raíz>/data/catalogo.db
        base_dir = Path(__file__).resolve().parent
        data_dir = base_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        db_uri = f"sqlite:///{(data_dir / 'catalogo.db').as_posix()}"
    # Si es SQLite file-based, asegúrate que la carpeta exista
    if db_uri.startswith("sqlite:///"):
        sqlite_path = db_uri.replace("sqlite:///", "", 1)
        sqlite_file = Path(sqlite_path)
        sqlite_file.parent.mkdir(parents=True, exist_ok=True)
    return db_uri


def get_engine_and_session(db_uri: str):
    engine = create_engine(db_uri, echo=False, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return engine, SessionLocal


# ----------------------------------------------------------------------
# Inicialización
# ----------------------------------------------------------------------
def inicializar_base_datos():
    """
    Crea tablas si no existen e inserta datos base (logística y un producto de ejemplo).
    """
    db_uri = resolve_db_uri()
    engine, SessionLocal = get_engine_and_session(db_uri)

    # 1) Crear tablas
    Base.metadata.create_all(engine)
    print(f"Tablas creadas/verificadas en: {db_uri}")

    session = SessionLocal()
    try:
        # 2) Seed logística si está vacío
        if session.query(LogisticaORM).count() == 0:
            zonas = [
                LogisticaORM(zona_nombre="Esquipulas, Centro (Zonas 1-3)",      tarifa_gtq=5.00, tiempo_estimado_dias=1),
                LogisticaORM(zona_nombre="Esquipulas aldeño (Zonas 4-5)",       tarifa_gtq=10.00, tiempo_estimado_dias=1),
                LogisticaORM(zona_nombre="Resto del pais",        tarifa_gtq=35.00, tiempo_estimado_dias=2),
        
            ]
            session.add_all(zonas)
            session.commit()
            print("Datos de logística insertados.")

        # 3) Producto de ejemplo (no obligatorio; sólo si no existe)
        if session.query(ProductoORM).filter_by(id_producto="UTIL001").count() == 0:
            util = ProductoORM(
                id_producto="UTIL001",
                nombre="Cuaderno Espiral Universitario",
                precio=15.50,
                stock=500,
                # Ajusta la ruta si tu imagen está en /static/img/productos/cuaderno.png
                imagen_url="/static/img/productos/cuaderno.png",
                tipo=TipoProductoEnum.UTIL,
                material="Papel Bond 80g",
                categoria="Cuaderno",
            )
            session.add(util)
            session.commit()
            print("Producto de ejemplo insertado (UTIL001).")

    except SQLAlchemyError as e:
        print(f"Error durante la inicialización de la base de datos: {e}")
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    inicializar_base_datos()
