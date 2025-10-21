from __future__ import annotations

from typing import Optional, Dict, Any

from .gemini import call_gemini, BadRequest, GeminiError


def chat_completion(
    mensaje: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.3,
    timeout: int = 15,
) -> Dict[str, Any]:
    """
    Envía un mensaje a Gemini v1 REST y devuelve {texto, usage}.
    Usa inlineData cuando haya imagen (no aplica aquí) y endpoint v1.
    """
    del system_prompt  # no se usa en este flujo simplificado
    del temperature    # no usado en la llamada REST básica

    try:
        result = call_gemini(prompt_text=mensaje, image_source=None, model=model, timeout=timeout)
        return {"texto": result.get("text", ""), "usage": None}
    except BadRequest as ve:
        # Mantener compatibilidad con rutas actuales
        raise ValueError(str(ve))
    except GeminiError as ge:
        # Enrutar como 502 hacia capas superiores
        raise RuntimeError(f"Error de Gemini: {ge}")

