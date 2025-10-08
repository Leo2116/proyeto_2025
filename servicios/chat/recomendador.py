from __future__ import annotations

from typing import List, Dict


KEYWORDS = {
    "biblia": ["biblia", "santa biblia"],
    "cuaderno": ["cuaderno", "libreta"],
    "mochila": ["mochila", "backpack"],
    "matematicas": ["matemáticas", "matematica", "matemáticas", "álgebra", "geometría"],
    "lapiz": ["lapiz", "lápiz"],
    "pluma": ["pluma", "bolígrafo", "boligrafo"],
}


def recomendar(texto: str, productos: List) -> List[Dict]:
    """
    Recomendación simple por coincidencia de palabras clave.
    Devuelve hasta 5 sugerencias {id, nombre, precio, portada_url}.
    """
    t = (texto or "").lower()
    if not t:
        candidatos = productos
    else:
        tokens = set(t.split())
        keys = [k for k, syns in KEYWORDS.items() if any(s in t for s in syns)]

        def matches(p):
            nombre = (getattr(p, "nombre", "") or "").lower()
            categoria = (getattr(p, "categoria", "") or "").lower()
            # Coincide si alguna keyword aparece en nombre o categoria
            return (
                any(k in nombre for k in keys)
                or any(k in categoria for k in keys)
                or any(tok in nombre for tok in tokens)
            )

        candidatos = [p for p in productos if matches(p)] or productos

    sugerencias = []
    for p in candidatos[:5]:
        sugerencias.append({
            "id": getattr(p, "id_producto", None) or getattr(p, "id", None) or getattr(p, "isbn", None) or getattr(p, "nombre", "").lower().replace(" ", "_"),
            "nombre": getattr(p, "nombre", "Producto"),
            "precio": float(getattr(p, "precio", 0) or 0),
            "portada_url": getattr(p, "imagen_url", None) or getattr(p, "portada_url", None),
        })
    return sugerencias

