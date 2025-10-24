import os
from typing import Any, Iterable

import google.generativeai as genai
from flask import current_app


# Modelo por defecto (rápido / free tier)
# Usamos alias "-latest" para compatibilidad entre v1/v1beta
_MODEL_ID = os.getenv("GEMINI_MODEL_ID", "gemini-1.5-flash-latest")
_model = None  # Inicialización perezosa


def _get_model():
    global _model
    if _model is not None:
        return _model
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY no configurada")
    try:
        # Forzar REST para evitar incompatibilidades gRPC/v1beta en algunos entornos
        transport = os.getenv("GEMINI_TRANSPORT", "rest")
        genai.configure(api_key=key, transport=transport)

        # Intentar con una lista de modelos compatibles
        candidates = []
        wanted = os.getenv("GEMINI_MODEL_ID") or _MODEL_ID
        candidates.append(wanted)
        # Fallbacks comunes
        fallbacks = [
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash-001",
            "gemini-1.5-pro-latest",
            "gemini-1.5-pro-001",
        ]
        for fid in fallbacks:
            if fid not in candidates:
                candidates.append(fid)

        last_exc: Exception | None = None
        for mid in candidates:
            try:
                m = genai.GenerativeModel(mid)
                # Verificación rápida sin costo alto
                try:
                    m.count_tokens("ping")
                except Exception:
                    pass
                _model = m
                return _model
            except Exception as e:
                last_exc = e
                continue
        if last_exc:
            raise last_exc
        raise RuntimeError("No se pudo inicializar modelo Gemini")
    except Exception:
        try:
            current_app.logger.exception("Error inicializando modelo Gemini")
        except Exception:
            pass
        raise


def _context_to_text(contexto: Any) -> str:
    """Convierte productos/categorías a texto plano para el prompt."""
    if not contexto:
        return ""
    try:
        lines: list[str] = []
        items: Iterable[Any]
        if isinstance(contexto, dict):
            items = [contexto]
        elif isinstance(contexto, (list, tuple)):
            items = contexto
        else:
            if hasattr(contexto, "to_dict"):
                items = [contexto.to_dict()]  # type: ignore[attr-defined]
            else:
                return str(contexto)
        for it in items:
            try:
                if hasattr(it, "to_dict"):
                    it = it.to_dict()  # type: ignore[attr-defined]
                nombre = (it.get("nombre") if isinstance(it, dict) else getattr(it, "nombre", None)) or "-"
                precio = (it.get("precio") if isinstance(it, dict) else getattr(it, "precio", 0)) or 0
                tipo = (it.get("tipo") if isinstance(it, dict) else getattr(it, "tipo", None)) or "-"
                autor = (it.get("autor") if isinstance(it, dict) else getattr(it, "autor", None))
                marca = (it.get("marca") if isinstance(it, dict) else getattr(it, "marca", None))
                extra = autor or marca
                line = f"- {nombre} | {tipo} | Q{float(precio):.2f}"
                if extra:
                    line += f" | {extra}"
                lines.append(line)
            except Exception:
                continue
        if not lines:
            return ""
        return "Catalogo:\n" + "\n".join(lines[:8])
    except Exception:
        return ""


def generar_respuesta_catalogo(prompt: str, contexto: Any | None = None) -> str:
    """
    Genera respuesta usando Gemini para el catálogo de la librería.
    """
    if not (prompt or "").strip():
        raise ValueError("prompt requerido")

    system_prompt = (
        "Eres un asistente de una libreria llamada 'Libreria Jehova Jireh'.\n"
        "Responde en español, breve y accionable.\n"
        "Prioriza: catalogo, productos, ISBN, stock, categorias, envios, pedidos y endpoints de la app.\n"
        "Si el usuario pide algo fuera de este dominio, redirigelo amablemente a temas de libros/utiles.\n"
        "Si hay contexto de catalogo, usalo para recomendar con 3-5 opciones con nombre y precio."
    )

    contexto_txt = _context_to_text(contexto) if contexto is not None else ""

    try:
        model = _get_model()
        resp = model.generate_content(
            [system_prompt, prompt, contexto_txt],
            generation_config={
                "temperature": 0.6,
                "max_output_tokens": 512,
            },
            request_options={
                "timeout": int(os.getenv("GEMINI_TIMEOUT", "15")),
            },
        )
        texto = (getattr(resp, "text", None) or "").strip()
        if not texto and hasattr(resp, "candidates"):
            try:
                cands = getattr(resp, "candidates", []) or []
                for c in cands:
                    parts = (((c.get("content") or {}).get("parts")) if isinstance(c, dict) else None) or []
                    for p in parts:
                        if isinstance(p, dict) and "text" in p:
                            texto += p.get("text") or ""
            except Exception:
                texto = texto or ""
        if not texto:
            raise RuntimeError("Gemini sin contenido")
        return texto
    except Exception as e:
        try:
            current_app.logger.exception("Fallo al generar respuesta de catalogo con Gemini")
            # Pista útil en logs si es 404/NotFound o v1beta
            msg = str(e)
            if "NotFound" in msg or "404" in msg:
                current_app.logger.error("Modelo de Gemini no encontrado. Prueba con GEMINI_MODEL_ID=gemini-1.5-flash-latest o -001")
        except Exception:
            pass
        return (
            "Puedo ayudarte a encontrar opciones de nuestro catalogo. "
            "Por favor indica si buscas libro o util escolar, autor/marca o tu presupuesto aproximado."
        )
