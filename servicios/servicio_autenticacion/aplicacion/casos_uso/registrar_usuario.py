# servicios/servicio_autenticacion/aplicacion/casos_uso/registrar_usuario.py

import uuid
from typing import Callable

# Importamos las dependencias
from servicios.servicio_autenticacion.dominio.usuario import Usuario
from servicios.servicio_autenticacion.aplicacion.repositorios.repositorio_usuario_interface import IRepositorioUsuario

# ==============================================================================
# CASO DE USO: REGISTRAR USUARIO
# Este modulo contiene la logica de negocio pura para el registro.
# Es independiente de Flask o de la implementacion de la BD (SQLite).
# ==============================================================================
class RegistrarUsuario:
    """
    Caso de Uso responsable de registrar un nuevo usuario en el sistema.
    """
    def __init__(self, repositorio: IRepositorioUsuario, hasher: Callable):
        """
        Inyeccion de Dependencias:
        - repositorio: El contrato (interfaz) para acceder a la persistencia.
        - hasher: Una funcion o clase que maneja el hashing de contraseñas (e.g., passlib).
        """
        self.repositorio = repositorio
        self.hasher = hasher

    def ejecutar(self, nombre: str, email: str, password: str, es_admin: bool = False) -> Usuario:
        """
        Ejecuta la logica de registro.

        :raises ValueError: Si el email ya existe.
        :returns: La entidad Usuario recien creada.
        """
        # 1. Validacion de Reglas de Negocio
        if self.repositorio.email_existe(email):
            raise ValueError(f"El email '{email}' ya se encuentra registrado.")
        
        # 2. Hashing de la Contraseña (Seguridad)
        # El hasher es inyectado desde la capa de Presentacion/Infraestructura (rutas.py)
        password_hash = self.hasher.hash(password)

        # 3. Creacion de la Entidad de Dominio
        # Generamos un ID unico para el nuevo usuario
        id_usuario = str(uuid.uuid4())
        
        nuevo_usuario = Usuario(
            id_usuario=id_usuario,
            nombre=nombre,
            email=email,
            password_hash=password_hash,
            es_admin=bool(es_admin), # Seteado desde capa de presentación en registro
            activo=True
        )

        # 4. Persistencia (Usando la Interfaz, no la implementacion SQLite directa)
        self.repositorio.guardar_usuario(nuevo_usuario)

        return nuevo_usuario
