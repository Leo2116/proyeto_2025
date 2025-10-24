import os
from typing import Any, Iterable

import google.generativeai as genai
from flask import current_app


# Cargar clave de API desde entorno
_MODEL_ID = os.getenv("GEMINI_MODEL_ID", "gemini-1.5-flash")
_model = None  # Se inicializa perezosamente para evitar fallos en import


def _get_model():
    global _model
    if _model is not None:
        return _model
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        # No levantar la app; se manejará en la llamada
        raise RuntimeError("GEMINI_API_KEY no configurada")
    try:
        genai.configure(api_key=key)
        model_id = os.getenv("GEMINI_MODEL_ID", _MODEL_ID)
        _m = genai.GenerativeModel(model_id)
        _model = _m
        return _m
    except Exception:
        # Dejar traza al primer uso
        try:
            current_app.logger.exception("Error inicializando modelo Gemini")
        except Exception:
            pass
        raise


def _context_to_text(contexto: Any) -> str:
    """Convierte una lista/dict de productos a texto simple para el prompt."""
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
            # Soporte muy básico para objetos con .to_dict()
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
                # No romper por un item defectuoso
                continue
        if not lines:
            return ""
        return "Catálogo:
" + "\n".join(lines[:8])
    except Exception:
        return ""


def generar_respuesta_catalogo(prompt: str, contexto: Any | None = None) -> str:
    """
    Genera respuesta usando Gemini enfocada en el catálogo de la librería.
    Aplica un system prompt de dominio, usa contexto si está disponible
    y maneja errores con logging. Puede retornar un fallback útil sólo si falla.
    """
    if not (prompt or "").strip():
        raise ValueError("prompt requerido")

    system_prompt = (
        "Eres un asistente de una librería llamada \"Librería Jehová Jiréh\".\n"
        "Responde en español, breve y accionable.\n"
        "Prioriza: catálogo, productos, ISBN, stock, categorías, envíos, pedidos y endpoints de la app.\n"
        "Si el usuario pide algo fuera de este dominio, redirígelo amablemente a temas de libros/útiles.\n"
        "Si hay contexto de catálogo, úsalo para recomendar con 3–5 opciones con nombre y precio."
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
        # El SDK puede devolver .text directamente
        texto = (getattr(resp, "text", None) or "").strip()
        if not texto and hasattr(resp, "candidates"):
            try:
                # Fallback defensivo por si cambia estructura
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
    except Exception:
        # Log de excepción completo en producción
        try:
            current_app.logger.exception("Fallo al generar respuesta de catálogo con Gemini")
        except Exception:
            pass
        # Fallback útil (solo si falla)
        return (
            "Puedo ayudarte a encontrar opciones de nuestro catálogo. "
            "Por favor indica si buscas libro o útil escolar, autor/marca o tu presupuesto aproximado."
        )
