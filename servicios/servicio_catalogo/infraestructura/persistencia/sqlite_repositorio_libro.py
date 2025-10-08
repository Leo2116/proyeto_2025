# servicios/servicio_catalogo/infraestructura/persistencia/sqlite_repositorio_producto.py

import sqlite3
from typing import List, Optional
from servicios.servicio_catalogo.dominio.producto import Producto, Libro, UtilEscolar
from servicios.servicio_catalogo.aplicacion.repositorios.repositorio_producto_interface import IRepositorioProducto

# Este adaptador implementa la interfaz IRepositorioProducto para interactuar con SQLite.
# Cumple el Principio de Inversión de Dependencias (DIP).
class SQLiteRepositorioProducto(IRepositorioProducto):
    
    def __init__(self, db_path: str):
        """Inicializa el repositorio con la ruta de la base de datos."""
        self.db_path = db_path
        
    def _ejecutar_consulta(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Método helper para ejecutar consultas y retornar resultados como filas."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        conn.close()
        return resultados

    def _reconstruir_producto(self, row: sqlite3.Row) -> Producto:
        """
        Reconstruye el objeto de Dominio (Libro o UtilEscolar) basado en el campo 'tipo' de la DB.
        """
        # Datos base de Producto
        datos_base = {
            'id': row['id'],
            'nombre': row['nombre'],
            'descripcion': row['descripcion'],
            'precio': row['precio'],
            'stock': row['stock'],
            'imagen_url': row['imagen_url']
        }
        
        # Lógica de herencia
        if row['tipo'] == 'Libro':
            return Libro(
                autor=row['atributo_extra_1'],  # Usamos campos genéricos para flexibilidad
                isbn=row['atributo_extra_2'],
                editorial=row['atributo_extra_3'],
                **datos_base
            )
        elif row['tipo'] == 'UtilEscolar':
            return UtilEscolar(
                material=row['atributo_extra_1'],
                color=row['atributo_extra_2'],
                **datos_base
            )
        
        # Retorna el Producto genérico si no se reconoce el tipo
        return Producto(**datos_base)


    def obtener_todos(self) -> List[Producto]:
        """Obtiene todos los productos de la tabla, reconstruyendo el objeto de Dominio correcto."""
        query = "SELECT * FROM productos"
        rows = self._ejecutar_consulta(query)
        return [self._reconstruir_producto(row) for row in rows]

    def buscar_por_id(self, producto_id: str) -> Optional[Producto]:
        """Busca un producto por ID."""
        query = "SELECT * FROM productos WHERE id = ?"
        row = self._ejecutar_consulta(query, (producto_id,))
        if row:
            return self._reconstruir_producto(row[0])
        return None

    def buscar_por_isbn(self, isbn: str) -> Optional[Libro]:
        """Busca un libro específicamente por ISBN (atributo_extra_2)."""
        query = "SELECT * FROM productos WHERE tipo = 'Libro' AND atributo_extra_2 = ?"
        row = self._ejecutar_consulta(query, (isbn,))
        if row:
            return self._reconstruir_producto(row[0])
        return None
