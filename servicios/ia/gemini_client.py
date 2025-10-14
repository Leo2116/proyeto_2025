from __future__ import annotations

import os
from typing import Optional, Dict, Any


def chat_completion(
    mensaje: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.3,
    timeout: int = 15,
) -> Dict[str, Any]:
    """
    Envía un mensaje a Gemini y devuelve {texto, usage}.
    Requiere GEMINI_API_KEY. Soporta GEMINI_MODEL.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Falta GEMINI_API_KEY en el entorno.")

    try:
        import google.generativeai as genai
    except Exception:
        raise RuntimeError("La librería 'google-generativeai' no está instalada.")

    genai.configure(api_key=api_key)
    model_name = model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    # system_prompt como instrucción del sistema
    generation_config = {
        "temperature": float(temperature or 0.3),
    }

    try:
        gmodel = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt
            or "Eres un asistente de una librería de Guatemala. Responde en español y sé conciso.",
            generation_config=generation_config,
        )

        # Algunos clientes permiten timeout en request_options
        try:
            resp = gmodel.generate_content(mensaje, request_options={"timeout": timeout})
        except TypeError:
            resp = gmodel.generate_content(mensaje)

        texto = getattr(resp, "text", None) or ""
        usage = getattr(resp, "usage_metadata", None)
        if usage and hasattr(usage, "__dict__"):
            usage = dict(usage.__dict__)
        return {"texto": texto, "usage": usage}
    except Exception as e:
        raise RuntimeError(f"Error de Gemini: {e}")

