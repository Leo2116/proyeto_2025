# servicios/servicio_autenticacion/infraestructura/persistencia/sqlite_repositorio_usuario.py 

# ==============================================================================
# IMPORTACIONES CLAVE
# ==============================================================================
from typing import Optional
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text

# Contrato de la capa de aplicación
from servicios.servicio_autenticacion.aplicacion.repositorios.repositorio_usuario_interface import IRepositorioUsuario

# Entidad de Dominio y ORM
from servicios.servicio_autenticacion.dominio.usuario import Usuario
from inicializar_db import UsuarioORM
from configuracion import Config

# ==============================================================================
# CONFIGURACIÓN DEL MOTOR DE BASE DE DATOS
# ==============================================================================
Engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, echo=False, future=True)
Session = sessionmaker(bind=Engine, autoflush=False, autocommit=False, future=True)

# Pequeña migración defensiva: asegurar columna is_admin en 'usuarios'
def _ensure_is_admin_column():
    try:
        with Engine.begin() as conn:
            # SQLite PRAGMA table_info devuelve: cid, name, type, notnull, dflt_value, pk
            res = conn.exec_driver_sql("PRAGMA table_info(usuarios)")
            cols = [row[1] for row in res]
            if 'is_admin' not in cols:
                conn.exec_driver_sql("ALTER TABLE usuarios ADD COLUMN is_admin BOOLEAN DEFAULT 0")
    except Exception as e:
        # No interrumpir la app si falla; solo loguear
        print(f"[WARN] No se pudo verificar/agregar columna is_admin: {e}")

_ensure_is_admin_column()

# ==============================================================================
# IMPLEMENTACIÓN DEL REPOSITORIO DE USUARIO (INFRAESTRUCTURA)
# ==============================================================================
class SQLiteRepositorioUsuario(IRepositorioUsuario):
    """
    Adaptador de persistencia que implementa IRepositorioUsuario 
    utilizando SQLite y SQLAlchemy.
    """

    # --------------------------------------------------------------------------
    # Mapeo de la Entidad de Dominio <-> Modelo ORM
    # --------------------------------------------------------------------------
    def _map_to_domain(self, orm_usuario: UsuarioORM) -> Usuario:
        """Convierte un objeto ORM a la entidad de Dominio Usuario."""
        return Usuario(
            id_usuario=orm_usuario.id_usuario,
            nombre=orm_usuario.nombre,
            email=orm_usuario.email,
            password_hash=orm_usuario.password_hash,
            es_admin=bool(getattr(orm_usuario, 'is_admin', False)),
            activo=orm_usuario.activo
        )

    def _map_to_orm(self, domain_usuario: Usuario) -> UsuarioORM:
        """Convierte la entidad de Dominio Usuario a un objeto ORM."""
        return UsuarioORM(
            id_usuario=domain_usuario.id_usuario,
            nombre=domain_usuario.nombre,
            email=domain_usuario.email,
            password_hash=domain_usuario.password_hash,
            activo=domain_usuario.activo,
            is_admin=bool(getattr(domain_usuario, 'es_admin', False))
            # verificado y token_verificacion quedan con sus defaults
        )

    # --------------------------------------------------------------------------
    # Implementación del Contrato IRepositorioUsuario
    # --------------------------------------------------------------------------
    def obtener_por_id(self, id_usuario: str) -> Optional[Usuario]:
        """Recupera un usuario por su identificador único (ID)."""
        session = Session()
        try:
            orm_usuario = (
                session.query(UsuarioORM)
                .filter_by(id_usuario=id_usuario)
                .one_or_none()
            )
            return self._map_to_domain(orm_usuario) if orm_usuario else None
        finally:
            session.close()

    def obtener_por_email(self, email: str) -> Optional[Usuario]:
        """Busca un usuario por su correo electrónico."""
        session = Session()
        try:
            orm_usuario = (
                session.query(UsuarioORM)
                .filter_by(email=email)
                .one_or_none()
            )
            return self._map_to_domain(orm_usuario) if orm_usuario else None
        finally:
            session.close()

    def guardar_usuario(self, usuario: Usuario) -> None:
        """Guarda un nuevo usuario o actualiza uno existente (UPSERT)."""
        session = Session()
        try:
            orm_existente = (
                session.query(UsuarioORM)
                .filter_by(id_usuario=usuario.id_usuario)
                .one_or_none()
            )
            if orm_existente:
                orm_existente.nombre = usuario.nombre
                orm_existente.email = usuario.email
                orm_existente.password_hash = usuario.password_hash
                orm_existente.activo = usuario.activo
                try:
                    # Puede no existir si tabla antigua, pero _ensure_is_admin_column ya intenta agregarla
                    setattr(orm_existente, 'is_admin', bool(getattr(usuario, 'es_admin', False)))
                except Exception:
                    pass
                # No tocamos verificado/token aquí.
            else:
                nuevo_orm = self._map_to_orm(usuario)
                session.add(nuevo_orm)

            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error al guardar o actualizar usuario: {e}")
            raise
        finally:
            session.close()

    def email_existe(self, email: str) -> bool:
        """Verifica si un correo electrónico ya está registrado."""
        session = Session()
        try:
            count = session.query(UsuarioORM).filter_by(email=email).count()
            return count > 0
        finally:
            session.close()

    # --------------------------------------------------------------------------
    # Extensiones para verificación por correo (usadas por EnviarVerificacionCorreo y /verify)
    # --------------------------------------------------------------------------
    def guardar_token_verificacion(self, id_usuario: str, token: str) -> None:
        """Guarda (o reemplaza) el token de verificación en el usuario."""
        session = Session()
        try:
            orm_usuario = (
                session.query(UsuarioORM)
                .filter_by(id_usuario=id_usuario)
                .one_or_none()
            )
            if not orm_usuario:
                raise ValueError("Usuario no encontrado para guardar token de verificación.")

            orm_usuario.token_verificacion = token
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error al guardar token de verificación: {e}")
            raise
        finally:
            session.close()

    def verificar_cuenta_por_token(self, id_usuario: str, email: str, token: str) -> bool:
        """
        Valida el token de verificación y marca la cuenta como verificada.
        Retorna True si se verificó, False si el token/usuario/email no coinciden.
        """
        session = Session()
        try:
            orm_usuario = (
                session.query(UsuarioORM)
                .filter_by(id_usuario=id_usuario, email=email)
                .one_or_none()
            )
            if not orm_usuario:
                return False

            if not token or orm_usuario.token_verificacion != token:
                return False

            orm_usuario.verificado = True
            orm_usuario.token_verificacion = None
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Error al verificar cuenta: {e}")
            return False
        finally:
            session.close()

    def email_verificado(self, email: str) -> bool:
        """Devuelve True si el usuario con 'email' tiene 'verificado' en True."""
        session = Session()
        try:
            orm_usuario = (
                session.query(UsuarioORM)
                .filter_by(email=email)
                .one_or_none()
            )
            return bool(orm_usuario and orm_usuario.verificado)
        except Exception:
            return False
        finally:
            session.close()
