# servicios/servicio_pedidos/aplicacion/repositorios/repositorio_orden_interface.py

from abc import ABC, abstractmethod
from typing import List, Optional
from servicios.servicio_pedidos.dominio.orden import Orden

# Esta es la Interfaz (Contrato) que toda implementación de repositorio de Orden debe seguir.
# Cumple con el Principio de Inversión de Dependencias (DIP).
class IRepositorioOrden(ABC):

    @abstractmethod
    def guardar(self, orden: Orden) -> None:
        """Guarda una nueva orden o actualiza una existente en la persistencia."""
        pass

    @abstractmethod
    def buscar_por_id(self, orden_id: str) -> Optional[Orden]:
        """Busca y retorna una orden por su ID."""
        pass

    @abstractmethod
    def obtener_todas(self) -> List[Orden]:
        """Retorna una lista de todas las órdenes en el sistema."""
        pass