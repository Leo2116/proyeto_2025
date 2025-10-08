class ExcepcionDominio(Exception):
    """Clase base para todas las excepciones de dominio."""
    pass

class ProductoNoEncontradoError(ExcepcionDominio):
    """Excepción lanzada cuando un producto no existe en el catálogo."""
    def __init__(self, mensaje="El producto solicitado no fue encontrado."):
        self.mensaje = mensaje
        super().__init__(self.mensaje)

class DatosDeProductoInvalidosError(ExcepcionDominio):
    """Excepción lanzada cuando los datos de entrada para un producto son inválidos."""
    def __init__(self, mensaje="Los datos de producto proporcionados son inválidos."):
        self.mensaje = mensaje
        super().__init__(self.mensaje)
