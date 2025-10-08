# servicios/servicio_catalogo/aplicacion/repositorios/repositorio_producto_interface.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional
from servicios.servicio_catalogo.dominio.producto import Producto

class IRepositorioProducto(ABC):
    """Interfaz del repositorio de productos."""

    @abstractmethod
    def buscar_productos(self, consulta: str) -> List[Producto]:
        """Buscar por nombre/autor/isbn/marca/sku…"""
        raise NotImplementedError

    @abstractmethod
    def guardar_producto(self, p: Producto) -> None:
        """Crear/actualizar un producto."""
        raise NotImplementedError

    @abstractmethod
    def obtener_por_id(self, producto_id: str) -> Optional[Producto]:
        """Obtener un producto por ID."""
        raise NotImplementedError

    # Métodos opcionales/conveniencia usados por tu caso de uso:
    def obtener_todos(self) -> List[Producto]:
        """Listado completo (puede tener implementación por defecto y ser opcional)."""
        return []

    # Alias que tu caso de uso invoca:
    def buscar_por_consulta(self, consulta: str) -> List[Producto]:
        return self.buscar_productos(consulta)

    def buscar_por_id(self, producto_id: str) -> Optional[Producto]:
        return self.obtener_por_id(producto_id)
