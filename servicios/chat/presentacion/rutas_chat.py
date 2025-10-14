from flask import Blueprint, request, jsonify
from pathlib import Path
import unicodedata

from inicializar_db import resolve_db_uri, get_engine_and_session, ProductoORM, LogisticaORM
from servicios.chat.recomendador import recomendar


chat_bp = Blueprint("chat_bp", __name__, url_prefix="/api/v1/chat")

# Paths para vitrina (imagenes locales)
BASE_DIR = Path(__file__).resolve().parents[3]
IMG_DIR = BASE_DIR / "static" / "img" / "productos"

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
    "pluma": 8.00,
}


def _norm(s: str) -> str:
    nf = unicodedata.normalize("NFD", str(s or ""))
    return "".join(ch for ch in nf if unicodedata.category(ch) != "Mn").lower().strip()


def productos_vitrina(consulta: str | None = None) -> list[dict]:
    exts = (".png", ".jpg", ".jpeg", ".webp")
    out: list[dict] = []
    q = _norm(consulta) if consulta else ""
    toks = [t for t in q.split() if t]
    try:
        for file in sorted(IMG_DIR.iterdir()):
            if not file.is_file() or file.suffix.lower() not in exts:
                continue
            stem = file.stem.lower()
            nombre = stem.replace("_", " ").replace("-", " ").strip().title()
            if toks:
                ns = _norm(stem + " " + nombre)
                if not all(t in ns for t in toks):
                    continue
            precio = PRECIOS_ESPECIFICOS.get(stem, 10.0)
            out.append({
                "id": stem,
                "nombre": nombre,
                "precio": float(precio),
                "tipo": "UtilEscolar",
                "categoria": "Utiles",
                "portada_url": f"/static/img/productos/{file.name}",
            })
    except Exception:
        pass
    return out


def detectar_intencion(t: str) -> str:
    n = _norm(t)
    if any(k in n for k in ["envio", "entrega", "tarifa", "domicilio", "delivery", "envios"]):
        return "shipping"
    if any(k in n for k in ["pago", "paypal", "stripe", "tarjeta", "factura", "comprar", "checkout"]):
        return "payment"
    if any(k in n for k in ["hola", "buenas", "buenos dias", "buenas tardes", "hey"]):
        return "greeting"
    if any(k in n for k in ["ayuda", "como", "necesito", "busco", "buscar", "recomienda", "sugerir"]):
        return "help"
    return "product"


# Detección simple de mensajes fuera de alcance (no relacionados con la librería)
DOMAIN_TOKENS = {
    # Productos y categorías
    "libro", "libros", "biblia", "santa", "testamento",
    "cuaderno", "cuadernos", "libreta", "libretas",
    "util", "utiles", "escolar", "escolares",
    "lapiz", "lapices", "pluma", "plumas", "boligrafo", "boligrafos", "lapicero", "lapiceros",
    "resaltador", "resaltadores", "marcador", "marcadores",
    "borrador", "goma", "regla", "escuadra", "transportador", "tijera", "tijeras", "sacapuntas",
    "papel", "hojas", "mochila", "mochilas", "pegamento",
    # Atributos / meta
    "precio", "catalogo", "isbn", "autor",
    # Acciones
    "comprar", "compra", "carrito",
    # Servicios
    "envio", "envios", "entrega", "pago", "pagos", "factura", "facturacion", "stripe", "paypal"
}

def es_fuera_alcance(t: str) -> bool:
    n = _norm(t)
    if not n:
        return False
    tokens = set(n.split())
    return tokens.isdisjoint(DOMAIN_TOKENS)


@chat_bp.post("/recomendar")
def api_chat_recomendar():
    data = request.get_json(silent=True) or {}
    mensaje = (data.get("mensaje") or data.get("text") or "").strip()

    # Crear sesion a la DB SQLite
    db_uri = resolve_db_uri()
    engine, SessionLocal = get_engine_and_session(db_uri)
    session = SessionLocal()
    try:
        intent = detectar_intencion(mensaje)

        if intent == "shipping":
            zonas = session.query(LogisticaORM).all()
            parts = ["Opciones de envios (GT):"]
            for z in zonas:
                parts.append(f"- {z.zona_nombre}: Q{float(z.tarifa_gtq):.2f}, {int(z.tiempo_estimado_dias)} dia(s)")
            parts.append("Puedes decirme tu codigo postal para estimar la zona.")
            return jsonify({"intent": intent, "message": "\n".join(parts), "suggestions": []}), 200

        if intent == "payment":
            msg = (
                "Aceptamos pagos con tarjeta via Stripe y PayPal. "
                "En esta demo, el pago esta simulado; al comprar se genera una factura local."
            )
            return jsonify({"intent": intent, "message": msg, "suggestions": []}), 200

        if intent in ("greeting", "help"):
            base = "Hola! Soy tu asistente de la libreria. Puedes pedirme libros o utiles (ej. 'lapiz', 'cuaderno', 'biblia')."
            vit = productos_vitrina(None)[:4]
            sugs = recomendar("cuaderno lapiz biblia", vit)
            return jsonify({"intent": intent, "message": base, "suggestions": sugs}), 200

        # product (default): mezclar DB + vitrina
        productos_db = session.query(ProductoORM).limit(300).all()
        vit = productos_vitrina(mensaje)
        merged = list(productos_db) + vit
        sugerencias = recomendar(mensaje, merged)

        # Si el mensaje parece fuera de alcance, responder disculpa + recomendación básica (siempre)
        if es_fuera_alcance(mensaje):
            fallback_list = productos_vitrina(None)[:6] or vit[:6] or merged[:6]
            msg = (
                "Lo siento, no puedo darte ese tipo de información. "
                "Puedo ayudarte con libros, útiles, envíos y pagos. "
                "Escribe una categoría (cuaderno, biblia) o un artículo (lápiz); "
                "también puedo informarte sobre envíos o pagos."
            )
            return jsonify({
                "intent": "oos",  # out-of-scope
                "message": msg,
                "suggestions": recomendar("cuaderno lapiz biblia", fallback_list) if fallback_list else []
            }), 200

        msg = "Esto te puede interesar:" if sugerencias else "No encontré coincidencias. Prueba con otra palabra o explora categorías."
        return jsonify({"intent": "product", "message": msg, "suggestions": sugerencias}), 200
    except Exception:
        return jsonify({"error": "Error al recomendar productos."}), 500
    finally:
        session.close()
