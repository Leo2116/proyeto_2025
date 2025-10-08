# servicios/servicio_catalogo/aplicacion/casos_uso/obtener_detalles_producto.py
from typing import List, Optional
from dataclasses import dataclass

# Dominio
from servicios.servicio_catalogo.dominio.producto import Producto, Libro, UtilEscolar
from servicios.servicio_catalogo.dominio.excepciones import ProductoNoEncontradoError

# Interfaces (Aplicación)
from servicios.servicio_catalogo.aplicacion.repositorios.repositorio_producto_interface import IRepositorioProducto
from servicios.servicio_catalogo.infraestructura.clientes_api.google_books_cliente import GoogleBooksCliente


@dataclass
class ObtenerDetallesDelProducto:
    """
    Caso de uso para obtener detalles de un producto.
    Si es Libro y no hay datos locales suficientes, intenta enriquecer con Google Books.
    """
    repositorio: IRepositorioProducto
    api_libros: GoogleBooksCliente

    def ejecutar_detalles(self, producto_id: str) -> Optional[Producto]:
        try:
            # 1) Buscar localmente
            producto = self.repositorio.buscar_por_id(producto_id)

            if producto and isinstance(producto, Libro):
                # 2) Enriquecer con API externa si procede
                datos_extra = self.api_libros.obtener_datos_libro(producto.isbn)
                if datos_extra:
                    if datos_extra.get('sinopsis'):
                        producto.sinopsis = datos_extra['sinopsis']
                    if datos_extra.get('portada_url'):
                        producto.portada_url = datos_extra['portada_url']
                return producto

            elif producto:
                # Útil escolar u otro tipo
                return producto

            # 3) Si no existe localmente pero parece ISBN → intenta API externa
            elif Libro.es_isbn_valido(producto_id):
                datos_externos = self.api_libros.obtener_datos_libro(producto_id)
                if datos_externos:
                    return Libro(
                        id=producto_id,
                        nombre=datos_externos.get('titulo', 'Libro sin título'),
                        precio=0.0,
                        isbn=producto_id,
                        autor=datos_externos.get('autor', 'Desconocido'),
                        sinopsis=datos_externos.get('sinopsis'),
                        portada_url=datos_externos.get('portada_url')
                    )

            # 4) No hubo suerte
            return None

        except Exception as e:
            print(f"Error al ejecutar detalles del producto: {e}")
            raise ProductoNoEncontradoError(f"Fallo al obtener producto {producto_id}. Causa: {e}")

    def ejecutar_todos(self) -> List[Producto]:
        return self.repositorio.obtener_todos()

    def buscar_productos(self, consulta: str) -> List[Producto]:
        return self.repositorio.buscar_por_consulta(consulta)


# 👉 Compatibilidad por si alguna parte del código aún usa el nombre antiguo
ObtenerDetallesProducto = ObtenerDetallesDelProducto
__all__ = ["ObtenerDetallesDelProducto", "ObtenerDetallesProducto"]
