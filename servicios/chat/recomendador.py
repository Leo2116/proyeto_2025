from __future__ import annotations

from typing import List, Dict, Any
import unicodedata


def _norm(s: Any) -> str:
    txt = (str(s or ""))
    txt = unicodedata.normalize("NFD", txt)
    txt = "".join(ch for ch in txt if unicodedata.category(ch) != "Mn")
    return txt.lower().strip()


KEYWORDS = {
    "biblia": ["biblia", "santa biblia", "testamento"],
    "cuaderno": ["cuaderno", "libreta", "libretas"],
    "mochila": ["mochila", "mochilas", "backpack"],
    "matematicas": ["matematicas", "matematica", "algebra", "geometria"],
    "lapiz": ["lapiz", "lapices", "lapicero", "lapiceros", "portaminas"],
    "pluma": ["pluma", "boligrafo", "boligrafos"],
    "borrador": ["borrador", "goma"],
    "regla": ["regla", "escuadra", "transportador"],
    "resaltador": ["resaltador", "resaltadores", "marcador", "marcadores"],
}


def _get(p: Any, key: str) -> Any:
    if isinstance(p, dict):
        return p.get(key)
    return getattr(p, key, None)


def recomendar(texto: str, productos: List[Any]) -> List[Dict]:
    """
    Recomendacion por palabras clave y tokens (acento-insensible).
    Soporta objetos o dicts. Devuelve hasta 8 sugerencias.
    """
    t = _norm(texto)
    if not t:
        candidatos = productos
    else:
        tokens = set(t.split())
        keys = [k for k, syns in KEYWORDS.items() if any(s in t for s in syns)]

        def matches(p):
            nombre = _norm(_get(p, "nombre"))
            categoria = _norm(_get(p, "categoria") or _get(p, "tipo"))
            autor = _norm(_get(p, "autor"))
            sku = _norm(_get(p, "sku") or _get(p, "isbn"))
            hay = " ".join(filter(None, [nombre, categoria, autor, sku]))
            return (
                any(k in hay for k in keys)
                or all(tok in hay for tok in tokens)
            )

        candidatos = [p for p in (productos or []) if matches(p)] or productos

    sugerencias: List[Dict] = []
    for p in (candidatos or [])[:8]:
        pid = _get(p, "id_producto") or _get(p, "id") or _get(p, "isbn") or _norm(_get(p, "nombre")).replace(" ", "_") or None
        nombre = _get(p, "nombre") or "Producto"
        precio = float(_get(p, "precio") or 0)
        portada = _get(p, "imagen_url") or _get(p, "portada_url")
        sugerencias.append({
            "id": pid or nombre.lower().replace(" ", "_"),
            "nombre": nombre,
            "precio": precio,
            "portada_url": portada,
        })
    return sugerencias
