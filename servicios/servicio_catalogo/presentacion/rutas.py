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
    consulta = (request.args.get('q') or '').strip()
    categoria = (request.args.get('categoria') or '').strip()
    tipo = (request.args.get('tipo') or '').strip()  # 'Libro' | 'UtilEscolar'
    try:
        # Filtrado por categoria/tipo si se solicita
        if categoria or tipo:
            productos_db = obtener_detalles_uc.ejecutar_todos()
            # Normalizar comparaciones
            c_norm = categoria.lower()
            t_norm = tipo.lower()
            filtrados = []
            for p in productos_db:
                # Tipo
                if t_norm:
                    pt = (p.__class__.__name__ or '').lower()
                    if pt != t_norm:
                        continue
                # Categoria (solo aplica a UtilEscolar que define 'categoria')
                if c_norm:
                    pc = (getattr(p, 'categoria', '') or '').lower()
                    if pc != c_norm:
                        continue
                filtrados.append(p)
            return jsonify([p.to_dict() for p in filtrados]), 200
        # Búsqueda por 'q'
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


# --------------------------------------------------------------------
# ENDPOINT: LISTAR CATEGORIAS (distintas en DB)
# --------------------------------------------------------------------
@catalogo_bp.route('/categorias', methods=['GET'])
def listar_categorias():
    """Devuelve categorías distintas de productos (principalmente UtilEscolar).
    Respuesta: { items: [ { categoria: str, total: int } ] }
    """
    try:
        items = {}
        for p in repositorio_producto.obtener_todos():
            cat = (getattr(p, 'categoria', None) or '').strip()
            if not cat:
                continue
            items[cat] = items.get(cat, 0) + 1
        out = [{ 'categoria': k, 'total': v } for k, v in sorted(items.items(), key=lambda kv: kv[0].lower())]
        return jsonify({ 'items': out }), 200
    except Exception as e:
        print(f"Error al listar categorias: {e}")
        return jsonify({ 'items': [] }), 200
