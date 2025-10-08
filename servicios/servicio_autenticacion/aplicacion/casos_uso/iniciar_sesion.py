# servicios/servicio_autenticacion/aplicacion/casos_uso/iniciar_sesion.py

from typing import Callable
from servicios.servicio_autenticacion.dominio.usuario import Usuario
from servicios.servicio_autenticacion.aplicacion.repositorios.repositorio_usuario_interface import IRepositorioUsuario

# ==============================================================================
# CASO DE USO: INICIAR SESION
# Logica de negocio para verificar credenciales.
# ==============================================================================
class IniciarSesion:
    """
    Caso de Uso responsable de autenticar a un usuario con su email y password.
    """
    def __init__(self, repositorio: IRepositorioUsuario, hasher: Callable):
        """
        Inyeccion de Dependencias:
        - repositorio: El contrato (interfaz) para acceder a la persistencia.
        - hasher: Una funcion o clase que maneja la verificacion de hashes (e.g., passlib).
        """
        self.repositorio = repositorio
        self.hasher = hasher

    def ejecutar(self, email: str, password: str) -> Usuario:
        """
        Busca el usuario y verifica la contraseña.

        :raises ValueError: Si el email no existe o la contraseña es incorrecta.
        :returns: La entidad Usuario autenticada.
        """
        # 1. Buscar el usuario por email
        usuario = self.repositorio.obtener_por_email(email)

        if not usuario:
            # Es una buena practica retornar un error generico por seguridad
            raise ValueError("Credenciales inválidas. Verifique su email y contraseña.")

        # 2. Verificar la contraseña usando el hasher inyectado
        # Comparamos la contrasena plana con el hash almacenado en la BD
        if not self.hasher.verify(password, usuario.password_hash):
            raise ValueError("Credenciales inválidas. Verifique su email y contraseña.")

        # 3. Retornar el objeto Usuario
        # El controlador de Flask puede usar este objeto para generar un token de sesion
        return usuario