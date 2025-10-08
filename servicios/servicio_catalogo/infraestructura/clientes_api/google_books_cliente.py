# servicios/servicio_catalogo/infraestructura/clientes_api/google_books_cliente.py

import requests
from typing import Optional, List
from servicios.servicio_catalogo.dominio.producto import Libro
from urllib.parse import quote

# ==============================================================================
# ADAPTADOR DE API EXTERNA
# Convierte datos JSON de Google Books a la entidad de Dominio 'Libro'.
# ==============================================================================
class GoogleBooksCliente:
    BASE_URL = "https://www.googleapis.com/books/v1/volumes"

    def buscar_libro_por_isbn(self, isbn: str) -> Optional[Libro]:
        """
        Busca un libro por ISBN y lo convierte a la entidad Libro del Dominio.
        """
        # q=isbn: se asegura de que la busqueda sea por ISBN.
        url = f"{self.BASE_URL}?q=isbn:{isbn}"
        
        try:
            respuesta = requests.get(url, timeout=5)
            respuesta.raise_for_status() # Lanza excepcion para codigos 4xx/5xx
            data = respuesta.json()

            if data.get('totalItems', 0) > 0:
                # Tomamos el primer resultado
                item = data['items'][0]['volumeInfo']
                
                # Extraccion segura de datos
                nombre = item.get('title', 'Título Desconocido')
                autor_list = item.get('authors', ['Autor Desconocido'])
                autor = ", ".join(autor_list)
                editorial = item.get('publisher', 'Editorial Desconocida')
                
                # Precio y Stock son MOCKS, ya que Google Books no da datos de venta en GT.
                precio = 99.99
                stock = 100 
                
                # Imagen de portada (preferimos la grande)
                imagen_url_data = item.get('imageLinks', {})
                imagen_url = imagen_url_data.get('thumbnail', 'https://placehold.co/128x192/EEEEEE/333333?text=No+Cover')
                
                paginas = item.get('pageCount', 0)

                # Creamos y retornamos la entidad de Dominio
                return Libro(
                    id_producto=isbn,
                    nombre=nombre,
                    precio=precio,
                    stock=stock,
                    imagen_url=imagen_url,
                    autor=autor,
                    editorial=editorial,
                    isbn=isbn,
                    paginas=paginas
                )

        except requests.exceptions.RequestException as e:
            print(f"Error de conexion al buscar ISBN {isbn} en Google Books: {e}")
        except Exception as e:
            print(f"Error al procesar la respuesta de Google Books para ISBN {isbn}: {e}")
            
        return None