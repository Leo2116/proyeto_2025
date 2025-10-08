import sqlite3
import json
from typing import List, Optional, Dict, Any
# Importamos las entidades y la interfaz de las capas internas (Dominio y Aplicación)
from servicios.servicio_pedidos.dominio.orden import Orden, OrdenItem
from servicios.servicio_pedidos.aplicacion.repositorios.repositorio_orden_interface import IRepositorioOrden

# Adaptador de persistencia que implementa el contrato (Interfaz) definido en la capa de Aplicación.
# Esto asegura que la lógica de negocio no tenga dependencia con sqlite3.
class SQLiteRepositorioOrden(IRepositorioOrden):
    
    def __init__(self, db_path: str):
        """Inicializa el repositorio con la ruta de la base de datos."""
        self.db_path = db_path
        # Nota: La conexión se establece y cierra en cada operación para mantener la seguridad.

    def _ejecutar_consulta(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Método helper para ejecutar consultas de lectura y retornar resultados como filas."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        conn.close()
        return resultados

    def _ejecutar_comando(self, query: str, params: tuple = ()):
        """Método helper para ejecutar comandos (INSERT, UPDATE, DELETE)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        conn.close()

    def _reconstruir_orden(self, row: sqlite3.Row) -> Orden:
        """
        Convierte una fila de la DB en una entidad de Dominio Orden. 
        Maneja la deserialización del campo 'items_json' que guarda la lista de productos.
        """
        
        # El campo items se guarda como JSON (string) en SQLite. Lo deserializamos.
        items_json = row['items_json']
        items_data = json.loads(items_json)
        
        items = []
        for item in items_data:
            items.append(OrdenItem(
                producto_id=item['producto_id'],
                nombre=item['nombre'],
                cantidad=item['cantidad'],
                precio_unitario=item['precio_unitario']
            ))

        return Orden(
            id=row['id'],
            usuario_id=row['usuario_id'],
            items=items,
            subtotal=row['subtotal'],
            costo_envio=row['costo_envio'],
            total=row['total'],
            estado=row['estado'],
            fecha_creacion=row['fecha_creacion']
        )

    def guardar(self, orden: Orden) -> None:
        """Guarda una nueva orden en la tabla 'ordenes'."""
        
        # Serializar la lista de OrdenItem a JSON para guardarla en una sola columna.
        # Esto es necesario para guardar objetos complejos en SQLite.
        items_data = [item.__dict__ for item in orden.items]
        items_json = json.dumps(items_data)

        query = """
        INSERT OR REPLACE INTO ordenes 
        (id, usuario_id, items_json, subtotal, costo_envio, total, estado, fecha_creacion)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            orden.id,
            orden.usuario_id,
            items_json,
            orden.subtotal,
            orden.costo_envio,
            orden.total,
            orden.estado,
            orden.fecha_creacion
        )
        self._ejecutar_comando(query, params)

    def buscar_por_id(self, orden_id: str) -> Optional[Orden]:
        """Busca y retorna una orden por su ID."""
        query = "SELECT * FROM ordenes WHERE id = ?"
        row = self._ejecutar_consulta(query, (orden_id,))
        if row:
            return self._reconstruir_orden(row[0])
        return None

    def obtener_todas(self) -> List[Orden]:
        """Retorna una lista de todas las órdenes."""
        query = "SELECT * FROM ordenes ORDER BY fecha_creacion DESC"
        rows = self._ejecutar_consulta(query)
        return [self._reconstruir_orden(row) for row in rows]
