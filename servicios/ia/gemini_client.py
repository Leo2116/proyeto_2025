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
    # Incluir instrucciones del sistema al prompt si vienen (modo "context+instrucciones")
    # Gemini v1 REST no tiene campo system dedicado; se concatena texto de control.
    sys_txt = (system_prompt or "").strip()
    if sys_txt:
        prompt = f"{sys_txt}\n\nUsuario: {mensaje}\nAsistente:"
    else:
        prompt = mensaje

    # temperature no se usa en esta llamada REST básica (sin tuning)
    del temperature

    try:
        result = call_gemini(prompt_text=prompt, image_source=None, model=model, timeout=timeout)
        return {"texto": result.get("text", ""), "usage": None}
    except BadRequest as ve:
        # Mantener compatibilidad con rutas actuales
        raise ValueError(str(ve))
    except GeminiError as ge:
        # Enrutar como 502 hacia capas superiores
        raise RuntimeError(f"Error de Gemini: {ge}")
