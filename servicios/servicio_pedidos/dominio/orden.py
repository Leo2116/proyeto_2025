# servicios/servicio_pedidos/dominio/orden.py

from typing import List
from datetime import datetime

# ==============================================================================
# ENTIDAD ORDEN ITEM (Detalle del Carrito)
# ==============================================================================
class OrdenItem:
    """Representa un producto dentro de una orden (carrito)."""
    def __init__(self, id_producto: str, nombre: str, precio: float, cantidad: int):
        self.id_producto = id_producto
        self.nombre = nombre
        self.precio = precio
        self.cantidad = cantidad

    def calcular_subtotal(self) -> float:
        """Calcula el costo total de este item."""
        return self.precio * self.cantidad
    
    def to_dict(self) -> dict:
        return {
            'id_producto': self.id_producto,
            'nombre': self.nombre,
            'precio': self.precio,
            'cantidad': self.cantidad,
            'subtotal': self.calcular_subtotal()
        }

# ==============================================================================
# ENTIDAD ORDEN
# ==============================================================================
class Orden:
    """Representa el pedido completo realizado por un usuario."""
    def __init__(self, id_orden: str, id_usuario: str, items: List[OrdenItem], costo_envio: float, 
                 total_final: float, direccion_envio: str, estado: str = "PENDIENTE", 
                 fecha_creacion: datetime = None):
        
        self.id_orden = id_orden
        self.id_usuario = id_usuario
        self.items = items
        self.costo_envio = costo_envio
        self.total_final = total_final
        self.direccion_envio = direccion_envio
        self.estado = estado
        self.fecha_creacion = fecha_creacion if fecha_creacion else datetime.now()

    def calcular_subtotal_productos(self) -> float:
        """Suma los subtotales de todos los items en la orden."""
        return sum(item.calcular_subtotal() for item in self.items)

    def to_dict(self) -> dict:
        return {
            'id_orden': self.id_orden,
            'id_usuario': self.id_usuario,
            'items': [item.to_dict() for item in self.items],
            'subtotal_productos': self.calcular_subtotal_productos(),
            'costo_envio': self.costo_envio,
            'total_final': self.total_final,
            'direccion_envio': self.direccion_envio,
            'estado': self.estado,
            'fecha_creacion': self.fecha_creacion.isoformat()
        }
