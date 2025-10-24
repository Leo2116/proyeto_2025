# servicios/servicio_catalogo/presentacion/rutas.py
from flask import Blueprint, request, jsonify
from pathlib import Path

# Importaciones del caso de uso y repositorio (para compatibilidad)
from servicios.servicio_catalogo.aplicacion.casos_uso.obtener_detalles_producto import ObtenerDetallesDelProducto
from servicios.servicio_catalogo.infraestructura.persistencia.pg_repositorio_producto import PGRepositorioProducto
from servicios.servicio_catalogo.infraestructura.clientes_api.google_books_cliente import GoogleBooksCliente

catalogo_bp = Blueprint('catalogo', __name__, url_prefix='/api/v1/catalogo')

# --------------------------------------------------------------------
# CONFIGURACIÓN DE RUTAS Y DIRECTORIOS
# --------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[3]  # raíz del proyecto (donde está app.py)
IMG_DIR = BASE_DIR / "static" / "img" / "productos"
IMG_DIR.mkdir(parents=True, exist_ok=True)

repositorio_producto = PGRepositorioProducto()
google_books_api = GoogleBooksCliente()

obtener_detalles_uc = ObtenerDetallesDelProducto(
    repositorio=repositorio_producto,
    api_libros=google_books_api
)

# --------------------------------------------------------------------
# LISTA DE PRECIOS Y PRODUCTOS (solo para vitrina)
# --------------------------------------------------------------------
PRECIOS_ESPECIFICOS = {
    "cuaderno": 18.00,
    "borrador": 2.00,
    "lapiz": 1.50,
    "sacapuntas": 2.00,
    "marcadores": 25.00,
    "pegamento": 5.00,
    "regla": 7.00,
    "tijera": 5.00,
    "hojas_blancas": 15.00,
    "hojas_de_colores": 20.00,
    "papel_crepe": 10.00,
    "pluma": 8.00
}

# --------------------------------------------------------------------
# FUNCIÓN PARA LEER IMÁGENES Y CREAR PRODUCTOS "MOCK"
# --------------------------------------------------------------------
def productos_mock_desde_static(consulta: str | None = None) -> list[dict]:
    """
    Crea una lista de productos basada en los archivos dentro de static/img/productos.
    Si existe un precio en PRECIOS_ESPECIFICOS, lo usa.
    """
    exts = (".png", ".jpg", ".jpeg", ".webp")
    productos = []
    DEFAULT_PRICE = 10.00

    for file in sorted(IMG_DIR.iterdir()):
        if not file.is_file() or file.suffix.lower() not in exts:
            continue

        stem = file.stem.lower()  # nombre sin extensión
        nombre = stem.replace("_", " ").replace("-", " ").strip().title()

        # Filtrado por búsqueda
        if consulta and consulta.lower() not in stem and consulta.lower() not in nombre.lower():
            continue

        precio = PRECIOS_ESPECIFICOS.get(stem, DEFAULT_PRICE)

        productos.append({
            "id": stem,
            "nombre": nombre,
            "precio": precio,
            "tipo": "UtilEscolar",
            "marca": "Genérico",
            "portada_url": f"/static/img/productos/{file.name}"
        })
    return productos


# --------------------------------------------------------------------
# ENDPOINT: LISTAR PRODUCTOS (DB + VITRINA)
# --------------------------------------------------------------------
@catalogo_bp.route('/productos', methods=['GET'])
def buscar_productos():
    consulta = request.args.get('q', '').strip()

    # Intentar productos desde DB (por compatibilidad)
    try:
        if consulta:
            productos_db = obtener_detalles_uc.buscar_productos(consulta)
        else:
            productos_db = obtener_detalles_uc.ejecutar_todos()
        productos_db_json = [p.to_dict() for p in productos_db]
    except Exception as e:
        print(f"Error al consultar DB (se ignorará): {e}")
        productos_db_json = []

    # Añadir productos de vitrina (basados en imágenes)
    productos_vitrina = productos_mock_desde_static(consulta)

    # Combinar resultados (DB + mock)
    productos = productos_db_json + productos_vitrina

    return jsonify(productos), 200


# --------------------------------------------------------------------
# ENDPOINT: OBTENER DETALLE DE UN PRODUCTO
# --------------------------------------------------------------------
@catalogo_bp.route('/productos/<string:id_producto>', methods=['GET'])
def obtener_producto(id_producto: str):
    """
    Primero intenta en la base de datos; si no existe, busca en los mock generados.
    """
    # DB
    try:
        producto = obtener_detalles_uc.ejecutar_detalles(id_producto)
        if producto:
            return jsonify(producto.to_dict()), 200
    except Exception as e:
        print(f"Error al obtener producto desde DB: {e}")

    # Vitrina (mock)
    for item in productos_mock_desde_static():
        if item["id"] == id_producto:
            return jsonify(item), 200

    return jsonify({'error': f'Producto con ID {id_producto} no encontrado.'}), 404
