# servicios/servicio_autenticacion/aplicacion/repositorios/repositorio_usuario_interface.py

from abc import ABC, abstractmethod
from typing import Optional

# Importamos la entidad del Dominio
from servicios.servicio_autenticacion.dominio.usuario import Usuario

# ==============================================================================
# INTERFAZ (Contrato)
# Define el contrato para cualquier adaptador de persistencia de Usuario.
# ==============================================================================
class IRepositorioUsuario(ABC):
    """
    Define los metodos CRUD necesarios para gestionar la entidad Usuario.
    La capa de Aplicacion dependera unicamente de esta interfaz (DIP).
    """

    @abstractmethod
    def obtener_por_id(self, id_usuario: str) -> Optional[Usuario]:
        """Recupera un usuario por su identificador unico."""
        pass

    @abstractmethod
    def obtener_por_email(self, email: str) -> Optional[Usuario]:
        """Busca un usuario por su correo electronico (usado en login y registro)."""
        pass

    @abstractmethod
    def guardar_usuario(self, usuario: Usuario) -> None:
        """Guarda un nuevo usuario o actualiza uno existente."""
        pass

    @abstractmethod
    def email_existe(self, email: str) -> bool:
        """Verifica si un correo electronico ya esta registrado."""
        pass

    # ---- Extensiones para verificación de cuenta por correo ----
    @abstractmethod
    def guardar_token_verificacion(self, id_usuario: str, token: str) -> None:
        """Guarda el token de verificación para un usuario."""
        pass

    @abstractmethod
    def verificar_cuenta_por_token(self, id_usuario: str, email: str, token: str) -> bool:
        """Marca la cuenta como verificada si el token y datos coinciden."""
        pass

    @abstractmethod
    def email_verificado(self, email: str) -> bool:
        """Retorna True si el email corresponde a un usuario con cuenta verificada."""
        pass
