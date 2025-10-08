from servicios.servicio_autenticacion.infraestructura.persistencia.sqlite_repositorio_usuario import SQLiteRepositorioUsuario
from inicializar_db import UsuarioORM
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from configuracion import Config

email = 'testuser@example.com'
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, echo=False, future=True)
Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

s = Session()
user = s.query(UsuarioORM).filter_by(email=email).one_or_none()
print('USER', user.id_usuario, user.email, user.token_verificacion)
uid = user.id_usuario
s.close()

repo = SQLiteRepositorioUsuario()
repo.guardar_token_verificacion(uid, 'abc123')

s2 = Session()
user2 = s2.query(UsuarioORM).filter_by(email=email).one_or_none()
print('AFTER', user2.id_usuario, user2.email, user2.token_verificacion)
s2.close()

