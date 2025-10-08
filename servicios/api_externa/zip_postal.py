from typing import Dict, Optional
import requests


ZIPPOTAM_BASE = "https://api.zippopotam.us"


def buscar_codigo_postal_gt(codigo: str, timeout: int = 10) -> Optional[Dict]:
    """
    Consulta Zippopotam.us para un código postal de Guatemala (GT).
    Devuelve dict normalizado: {codigo, pais, estado, ciudad} o None si no existe.
    """
    codigo = (codigo or "").strip()
    if not codigo:
        return None

    url = f"{ZIPPOTAM_BASE}/GT/{codigo}"
    resp = requests.get(url, timeout=timeout)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    data = resp.json() or {}
    places = data.get("places") or []
    if not places:
        return None
    place = places[0] or {}
    return {
        "codigo": data.get("'post code'", codigo) if "'post code'" in data else (data.get("post code") or codigo),
        "pais": data.get("country") or "Guatemala",
        "estado": place.get("state") or place.get("state abbreviation"),
        "ciudad": place.get("place name") or place.get("state") or "",
    }

