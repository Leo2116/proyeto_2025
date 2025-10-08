# servicios/servicio_catalogo/dominio/producto.py

from typing import List, Dict, Any, Optional 
import uuid

# ==============================================================================
# CLASE BASE DEL DOMINIO: PRODUCTO
# Define las propiedades comunes que todo lo que se vende en la librería debe tener.
# ==============================================================================
class Producto:
    """Entidad base de dominio para cualquier producto del catálogo."""
    def __init__(self, 
                 nombre: str, 
                 precio: float, 
                 stock: int, 
                 id: Optional[str] = None): # Ahora Optional está definido
        
        # El ID se genera automáticamente si no se provee (útil para nuevos productos)
        self.id = id if id is not None else str(uuid.uuid4())
        self.nombre = nombre
        self.precio = precio
        self.stock = stock

    def to_dict(self) -> Dict[str, Any]:
        """Convierte la entidad en un diccionario para serialización (ej: JSON o DB)."""
        return {
            'id': self.id,
            'nombre': self.nombre,
            'precio': self.precio,
            'stock': self.stock,
            # Añade el tipo de producto para poder recrear la subclase
            'tipo': self.__class__.__name__ 
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}, nombre='{self.nombre}'>"

# ==============================================================================
# SUBCLASE: LIBRO (Hereda de Producto)
# Agrega atributos específicos de un libro (ISBN, autor).
# ==============================================================================
class Libro(Producto):
    """Representa un libro en el catálogo."""
    def __init__(self, 
                 nombre: str, 
                 precio: float, 
                 stock: int, 
                 isbn: str, # Identificador específico de libros
                 autor: str, 
                 id: Optional[str] = None, 
                 descripcion: str = None, 
                 paginas: int = None, 
                 editor: str = None):
        
        # Inicializa las propiedades de la clase base Producto
        super().__init__(nombre, precio, stock, id)
        
        # Propiedades específicas de Libro
        self.isbn = isbn
        self.autor = autor
        # Propiedades opcionales que se pueden enriquecer con la API de Google Books
        self.descripcion = descripcion
        self.paginas = paginas
        self.editor = editor
        
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'isbn': self.isbn,
            'autor': self.autor,
            'descripcion': self.descripcion,
            'paginas': self.paginas,
            'editor': self.editor,
        })
        return data

# ==============================================================================
# SUBCLASE: UTIL ESCOLAR (Hereda de Producto)
# Agrega atributos específicos de útiles (material, marca).
# ==============================================================================
class UtilEscolar(Producto):
    """Representa un útil escolar en el catálogo."""
    def __init__(self, 
                 nombre: str, 
                 precio: float, 
                 stock: int, 
                 sku: str, # Identificador específico de útiles (Stock Keeping Unit)
                 categoria: str, 
                 marca: str, 
                 id: Optional[str] = None): # Ahora Optional está definido

        # Inicializa las propiedades de la clase base Producto
        super().__init__(nombre, precio, stock, id)

        # Propiedades específicas de UtilEscolar
        self.sku = sku
        self.categoria = categoria
        self.marca = marca

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'sku': self.sku,
            'categoria': self.categoria,
            'marca': self.marca,
        })
        return data
