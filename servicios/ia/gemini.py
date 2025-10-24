from __future__ import annotations

import base64
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import requests


# Logger for Gemini integration (no secrets, no base64)
logger = logging.getLogger("servicios.ia.gemini")


SUPPORTED_MIME = {"image/png", "image/jpeg", "image/webp"}
MAX_IMAGE_BYTES = 4 * 1024 * 1024  # 4 MB


class GeminiError(Exception):
    def __init__(self, message: str, status: int = 500, category: str = "upstream") -> None:
        super().__init__(message)
        self.status = status
        self.category = category


class BadRequest(GeminiError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status=400, category="bad_request")


def _sniff_mime_from_bytes(data: bytes) -> Optional[str]:
    # PNG
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    # JPEG
    if len(data) >= 3 and data[:3] == b"\xFF\xD8\xFF":
        return "image/jpeg"
    # WEBP (RIFF....WEBP)
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _parse_data_url(uri: str) -> Tuple[Optional[str], bytes]:
    # data:[<mediatype>][;base64],<data>
    m = re.match(r"^data:([^;,]+)?;?base64?,(.+)$", uri, flags=re.IGNORECASE)
    if not m:
        raise BadRequest("Data URL inválida para imagen.")
    mime = m.group(1) or None
    try:
        b = base64.b64decode(m.group(2), validate=True)
    except Exception:
        raise BadRequest("Base64 inválido en Data URL.")
    return mime, b


def _read_local_file(path: str) -> bytes:
    if not os.path.exists(path) or not os.path.isfile(path):
        raise BadRequest("Ruta de imagen local inválida o no existente.")
    try:
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        raise BadRequest("No se pudo leer la imagen local.")


def _download_http_image(url: str, timeout: int = 15) -> Tuple[str, bytes]:
    try:
        # First try HEAD to check content-type quickly
        h = requests.head(url, timeout=timeout, allow_redirects=True)
        ct = h.headers.get("Content-Type") or h.headers.get("content-type")
    except Exception:
        ct = None
    try:
        r = requests.get(url, timeout=timeout, stream=True)
    except requests.exceptions.RequestException as e:
        raise BadRequest(f"No se pudo descargar la imagen: {e}")
    if r.status_code >= 400:
        raise BadRequest(f"No se pudo descargar la imagen (HTTP {r.status_code}).")
    # If HEAD had no content-type, try GET headers
    if not ct:
        ct = r.headers.get("Content-Type") or r.headers.get("content-type")
    if not ct or not ct.lower().startswith("image/"):
        observed = ct or "desconocido"
        raise BadRequest(f"URL remota no es una imagen. Content-Type encontrado: {observed}")
    try:
        data = r.content
    finally:
        r.close()
    return ct.split(";")[0].strip().lower(), data


@dataclass
class NormalizedImage:
    mime: str
    base64_data: str
    size_mb: float


def normalize_image_for_gemini(source: str) -> NormalizedImage:
    """
    Normaliza imagen de distintas fuentes (http(s) URL, ruta local, base64 crudo, Data URL)
    Validando MIME (png/jpeg/webp) y tamaño <= 4 MB.
    Retorna NormalizedImage {mime, base64_data, size_mb}.
    """
    if not source:
        raise BadRequest("Fuente de imagen vacía.")

    src = source.strip()
    data: Optional[bytes] = None
    mime: Optional[str] = None

    # Data URL
    if src.lower().startswith("data:"):
        mime, data = _parse_data_url(src)

    # HTTP(S) URL
    elif src.lower().startswith("http://") or src.lower().startswith("https://"):
        mime, data = _download_http_image(src)

    # Local path
    elif os.path.exists(src):
        data = _read_local_file(src)
        mime = _sniff_mime_from_bytes(data) or "image/jpeg"

    else:
        # Assume raw base64 without prefix
        try:
            data = base64.b64decode(src, validate=True)
        except Exception:
            raise BadRequest("Cadena base64 inválida para imagen.")
        mime = _sniff_mime_from_bytes(data) or "image/jpeg"

    if not data or len(data) == 0:
        raise BadRequest("Imagen vacía o no válida.")

    if len(data) > MAX_IMAGE_BYTES:
        raise BadRequest("Imagen excede el tamaño máximo de 4 MB.")

    mime = (mime or "image/jpeg").split(";")[0].strip().lower()

    if mime not in SUPPORTED_MIME:
        raise BadRequest(
            f"MIME no soportado: {mime}. Solo se permiten: {', '.join(sorted(SUPPORTED_MIME))}"
        )

    b64 = base64.b64encode(data).decode("ascii")
    size_mb = round(len(data) / (1024 * 1024), 4)
    return NormalizedImage(mime=mime, base64_data=b64, size_mb=size_mb)


def build_gemini_payload(prompt_text: str, normalized_image: Optional[NormalizedImage] = None) -> Dict[str, Any]:
    if not isinstance(prompt_text, str) or not prompt_text.strip():
        raise BadRequest("El prompt de texto es requerido.")

    parts: list = []
    if normalized_image is not None:
        parts.append({
            "inlineData": {
                "mimeType": normalized_image.mime,
                "data": normalized_image.base64_data,
            }
        })
    parts.append({"text": prompt_text})

    return {
        "contents": [
            {"parts": parts}
        ]
    }


def _endpoint_for_model(model: Optional[str]) -> Tuple[str, str]:
    # Forzar siempre el modelo solicitado
    model_name = "gemini-2.5-flash"
    base = "https://generativelanguage.googleapis.com/v1"
    endpoint = f"{base}/models/{model_name}:generateContent"
    return model_name, endpoint


def _map_status_category(status_code: int) -> str:
    if status_code in (401, 403):
        return "auth"
    if status_code == 404:
        return "model"
    if status_code == 429:
        return "rate_limit"
    if 400 <= status_code < 500:
        return "bad_request"
    return "upstream"


def call_gemini(
    prompt_text: str,
    image_source: Optional[str] = None,
    *,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: int = 15,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    Llama a la API REST v1 de Gemini (generateContent) con inlineData.
    Retorna { text, model, mime, size_mb, request_id }.
    
    Errores: BadRequest(400), GeminiError con categorías: auth, model, rate_limit, upstream.
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise BadRequest("Falta GEMINI_API_KEY en el entorno.")

    normalized_image: Optional[NormalizedImage] = None
    if image_source:
        normalized_image = normalize_image_for_gemini(image_source)

    payload = build_gemini_payload(prompt_text, normalized_image)
    model_name, endpoint = _endpoint_for_model(model)

    # Prepare request
    params = {"key": key}
    headers = {
        "Content-Type": "application/json",
    }

    attempt = 0
    backoff = 0.5
    start_overall = time.time()
    last_exc: Optional[Exception] = None
    while attempt < max_retries:
        attempt += 1
        start = time.time()
        status = None
        request_id = None
        try:
            resp = requests.post(endpoint, params=params, json=payload, headers=headers, timeout=timeout)
            status = resp.status_code
            request_id = resp.headers.get("x-goog-request-id") or resp.headers.get("X-Goog-Request-Id")
            latency_ms = int((time.time() - start) * 1000)

            # Logging (no secrets / no base64)
            mime = normalized_image.mime if normalized_image else None
            size_kb = int((normalized_image.size_mb * 1024)) if normalized_image else None
            logger.info(
                "provider=%s model=%s status=%s latency_ms=%s mime=%s size_kb=%s x-goog-request-id=%s",
                "gemini", model_name, status, latency_ms, mime, size_kb, request_id
            )

            if status >= 200 and status < 300:
                data = resp.json()
                # Expect candidates[0].content.parts[*].text
                text = ""
                try:
                    candidates = data.get("candidates") or []
                    if candidates:
                        parts = (candidates[0].get("content") or {}).get("parts") or []
                        for p in parts:
                            if "text" in p:
                                text += p.get("text") or ""
                except Exception:
                    text = ""
                return {
                    "text": text,
                    "model": model_name,
                    "mime": normalized_image.mime if normalized_image else None,
                    "size_mb": normalized_image.size_mb if normalized_image else None,
                    "request_id": request_id,
                    "status": status,
                }

            # Non-2xx: map and maybe retry
            category = _map_status_category(status)
            body_text = None
            try:
                body_text = resp.text
            except Exception:
                body_text = None

            # Retry only on 429 and 5xx
            if status == 429 or (500 <= status < 600):
                time.sleep(backoff)
                backoff = min(backoff * 2, 4.0)
                continue

            # Other errors -> raise
            raise GeminiError(
                message=f"Error {status} de Gemini ({category}).",
                status=status,
                category=category,
            )
        except requests.exceptions.Timeout as e:
            last_exc = e
            # Retry on timeout
            time.sleep(backoff)
            backoff = min(backoff * 2, 4.0)
            continue
        except requests.exceptions.RequestException as e:
            last_exc = e
            # Retry on connection errors up to max_retries
            time.sleep(backoff)
            backoff = min(backoff * 2, 4.0)
            continue

    # If we exit loop, treat as upstream timeout
    elapsed = int((time.time() - start_overall) * 1000)
    logger.info(
        "provider=%s model=%s status=%s latency_ms=%s mime=%s size_kb=%s x-goog-request-id=%s",
        "gemini", model_name, "timeout", elapsed, normalized_image.mime if normalized_image else None,
        int((normalized_image.size_mb * 1024)) if normalized_image else None, None
    )
    raise GeminiError("Timeout o error de red al consultar Gemini.", status=504, category="upstream")
