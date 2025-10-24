import os
from typing import Any, Iterable

import google.generativeai as genai
from flask import current_app


# Modelo fijo (siempre usar este)
_MODEL_ID = "gemini-2.5-flash"
_model = None  # Inicialización perezosa


def _get_model():
    global _model
    if _model is not None:
        return _model
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY no configurada")
    try:
        # Forzar REST para evitar incompatibilidades gRPC/v1beta
        genai.configure(api_key=key, transport="rest")
        _model = genai.GenerativeModel(_MODEL_ID)
        # Verificación liviana (no crítica)
        try:
            _model.count_tokens("ping")
        except Exception:
            pass
        return _model
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
        "Eres el asistente de 'Libreria Jehova Jireh'.\n"
        "Reglas estrictas:\n"
        "- SOLO puedes recomendar productos que aparezcan en el catalogo provisto en el contexto.\n"
        "- Si el usuario pide algo que NO aparece en ese listado, responde que no lo tenemos en este momento y sugiere alternativas DEL MISMO LISTADO.\n"
        "- Siempre expresa precios en quetzales guatemaltecos con el formato 'Q<numero>'. No uses USD ni otros simbolos.\n"
        "- Responde en español, breve y accionable (3–5 opciones como maximo).\n"
        "- Si el contexto esta vacio, pide 1 dato mas (tipo, autor/marca, presupuesto) y evita inventar.\n"
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
                current_app.logger.error("Modelo de Gemini no encontrado: gemini-2.5-flash")
        except Exception:
            pass
        return (
            "Puedo ayudarte a encontrar opciones de nuestro catalogo. "
            "Por favor indica si buscas libro o util escolar, autor/marca o tu presupuesto aproximado."
        )
