import os
from typing import List, Dict
import requests


GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"


def _normalize_item(item: dict) -> Dict:
    info = item.get("volumeInfo", {}) if isinstance(item, dict) else {}
    title = info.get("title") or "Sin título"
    authors = info.get("authors") or []
    images = info.get("imageLinks", {}) or {}
    portada = images.get("thumbnail") or images.get("smallThumbnail")
    preview = info.get("previewLink") or info.get("infoLink")
    # Asegurar https
    if isinstance(portada, str) and portada.startswith("http:"):
        portada = portada.replace("http:", "https:", 1)
    if isinstance(preview, str) and preview.startswith("http:"):
        preview = preview.replace("http:", "https:", 1)

    return {
        "titulo": title,
        "autores": authors,
        "portada_url": portada,
        "preview_url": preview,
    }


def buscar_libros(q: str, api_key: str, max_results: int = 10, timeout: int = 10) -> List[Dict]:
    """
    Busca libros en Google Books por texto.
    Devuelve lista normalizada de dicts: {titulo, autores, portada_url, preview_url}.

    Levanta ValueError si falta API key.
    Puede levantar requests.exceptions.RequestException en errores de red.
    """
    if not api_key:
        raise ValueError("Falta GOOGLE_BOOKS_API_KEY en el entorno.")
    q = (q or "").strip()
    if not q:
        return []

    params = {
        "q": q,
        "maxResults": max(1, min(int(max_results or 10), 40)),
        "key": api_key,
        "printType": "books",
    }
    resp = requests.get(GOOGLE_BOOKS_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    data = resp.json() or {}
    items = data.get("items") or []
    return [_normalize_item(it) for it in items]

