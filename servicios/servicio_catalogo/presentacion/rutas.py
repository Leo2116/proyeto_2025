# servicios/servicio_catalogo/presentacion/rutas.py
from flask import Blueprint, request, jsonify
from pathlib import Path

from servicios.servicio_catalogo.aplicacion.casos_uso.obtener_detalles_producto import ObtenerDetallesDelProducto
from servicios.servicio_catalogo.infraestructura.persistencia.pg_repositorio_producto import PGRepositorioProducto
import unicodedata
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
def _norm(s: str) -> str:
    try:
        nf = unicodedata.normalize('NFD', str(s or ''))
        return ''.join(ch for ch in nf if unicodedata.category(ch) != 'Mn').lower().strip()
    except Exception:
        return (str(s or '')).lower().strip()


CANON_CATS = [
    'libros y textos',
    'insumos de oficina',
    'arte, manualidades, escritura y colorear',
    'escolar',
]


def _bucket_category(p) -> str:
    # Libros siempre a "libros y textos"
    if p.__class__.__name__ == 'Libro':
        return 'libros y textos'
    txt = ' '.join([
        str(getattr(p, 'nombre', '') or ''),
        str(getattr(p, 'categoria', '') or ''),
        str(getattr(p, 'material', '') or ''),
    ])
    nt = _norm(txt)
    # Palabras clave por bucket
    office = {'pluma', 'boligrafo', 'boligrafos', 'folder', 'clip', 'clips', 'folders', 'oficina', 'marcador', 'marcadores', 'resaltador'}
    art = {'arte', 'manualidad', 'manualidades', 'pegamento', 'silicon', 'silicona', 'pincel', 'pintura', 'tempera', 'temperas', 'acrilico', 'acrilicos', 'papel crepe', 'crepe', 'cartulina', 'colores', 'crayola', 'crayolas'}
    school = {'cuaderno', 'cuadernos', 'lapiz', 'lapices', 'lápiz', 'borrador', 'goma', 'sacapuntas', 'regla', 'tijera', 'tijeras', 'hoja', 'hojas', 'libreta'}
    if any(k in nt for k in office):
        return 'insumos de oficina'
    if any(k in nt for k in art):
        return 'arte, manualidades, escritura y colorear'
    if any(k in nt for k in school):
        return 'escolar'
    # Por defecto, si es util, caer en 'escolar'
    return 'escolar'


@catalogo_bp.route('/productos', methods=['GET'])
def buscar_productos():
    consulta = (request.args.get('q') or '').strip()
    categoria = (request.args.get('categoria') or '').strip()
    tipo = (request.args.get('tipo') or '').strip()  # 'Libro' | 'UtilEscolar'
    try:
        # Filtrado por categoria/tipo si se solicita
        if categoria or tipo:
            productos_db = obtener_detalles_uc.ejecutar_todos()
            c_norm = _norm(categoria)
            t_norm = _norm(tipo)
            filtrados = []
            for p in productos_db:
                if t_norm:
                    pt = _norm(p.__class__.__name__)
                    if pt != t_norm:
                        continue
                if c_norm:
                    # Si la categoria solicitada es una de las canónicas, usar bucketing
                    if c_norm in [_norm(x) for x in CANON_CATS]:
                        if _bucket_category(p) != categoria:
                            continue
                    else:
                        pc = _norm(getattr(p, 'categoria', '') or '')
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
    """Devuelve las categorías canónicas con totales calculados.
    Respuesta: { items: [ { categoria: str, total: int } ] }
    """
    try:
        totals = {c: 0 for c in CANON_CATS}
        for p in repositorio_producto.obtener_todos():
            b = _bucket_category(p)
            if b in totals:
                totals[b] += 1
        out = [{ 'categoria': k, 'total': totals[k] } for k in CANON_CATS]
        return jsonify({ 'items': out }), 200
    except Exception as e:
        print(f"Error al listar categorias: {e}")
        return jsonify({ 'items': [] }), 200
