# servicios/servicio_autenticacion/dominio/usuario.py

import uuid
from dataclasses import dataclass

# ==============================================================================
# ENTIDAD DE DOMINIO: USUARIO
# Define la estructura y las reglas de negocio de un usuario.
# Es independiente de la tecnologia (SQLite, Flask, etc.).
# ==============================================================================
@dataclass
class Usuario:
    """
    Representa un usuario registrado en la libreria.
    Utiliza dataclass para una definicion concisa de propiedades.
    """
    # Identificador unico para el usuario (generado al crearse)
    id_usuario: str
    
    # Informacion basica de contacto
    nombre: str
    email: str
    
    # Credenciales (la contraseña ya debe estar hasheada al llegar aqui)
    password_hash: str 
    
    # Roles y estados
    es_admin: bool = False
    activo: bool = True
    
    @classmethod
    def crear_nuevo(cls, nombre: str, email: str, password_hash: str):
        """
        Metodo factory para crear una nueva instancia de Usuario con un ID unico.
        """
        return cls(
            id_usuario=str(uuid.uuid4()),
            nombre=nombre,
            email=email,
            password_hash=password_hash
        )

    def actualizar_nombre(self, nuevo_nombre: str):
        """Regla de negocio: Actualiza el nombre del usuario."""
        if not nuevo_nombre or len(nuevo_nombre) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres.")
        self.nombre = nuevo_nombre

    def __str__(self):
        return f"Usuario(ID: {self.id_usuario}, Email: {self.email})"