# servicios/servicio_catalogo/presentacion/rutas.py
from flask import Blueprint, request, jsonify
from pathlib import Path

from servicios.servicio_catalogo.aplicacion.casos_uso.obtener_detalles_producto import ObtenerDetallesDelProducto
from servicios.servicio_catalogo.infraestructura.persistencia.pg_repositorio_producto import PGRepositorioProducto
from servicios.servicio_catalogo.infraestructura.clientes_api.google_books_cliente import GoogleBooksCliente

catalogo_bp = Blueprint('catalogo', __name__, url_prefix='/api/v1/catalogo')

BASE_DIR = Path(__file__).resolve().parents[3]
IMG_DIR = BASE_DIR / "static" / "img" / "productos"
IMG_DIR.mkdir(parents=True, exist_ok=True)

repositorio_producto = PGRepositorioProducto()
google_books_api = GoogleBooksCliente()
obtener_detalles_uc = ObtenerDetallesDelProducto(
    repositorio=repositorio_producto,
    api_libros=google_books_api,
)


# --------------------------------------------------------------------
# ENDPOINT: LISTAR PRODUCTOS (solo DB)
# --------------------------------------------------------------------
@catalogo_bp.route('/productos', methods=['GET'])
def buscar_productos():
    consulta = request.args.get('q', '').strip()
    try:
        if consulta:
            productos_db = obtener_detalles_uc.buscar_productos(consulta)
        else:
            productos_db = obtener_detalles_uc.ejecutar_todos()
        return jsonify([p.to_dict() for p in productos_db]), 200
    except Exception as e:
        print(f"Error al consultar DB: {e}")
        return jsonify([]), 200


# --------------------------------------------------------------------
# ENDPOINT: OBTENER DETALLE DE UN PRODUCTO (solo DB)
# --------------------------------------------------------------------
@catalogo_bp.route('/productos/<string:id_producto>', methods=['GET'])
def obtener_producto(id_producto: str):
    try:
        producto = obtener_detalles_uc.ejecutar_detalles(id_producto)
        if producto:
            return jsonify(producto.to_dict()), 200
    except Exception as e:
        print(f"Error al obtener producto desde DB: {e}")
    return jsonify({'error': f'Producto con ID {id_producto} no encontrado.'}), 404

