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
    Envía un mensaje al modelo de ChatGPT (OpenAI) y devuelve {texto, usage}.
    Requiere OPENAI_API_KEY en el entorno. Soporta OPENAI_BASE_URL/OPENAI_ORG/OPENAI_MODEL.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Falta OPENAI_API_KEY en el entorno.")

    base_url = os.getenv("OPENAI_BASE_URL")  # opcional (Azure/self-hosted compatible)
    org = os.getenv("OPENAI_ORG")
    model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Importación perezosa para evitar dependencia si no se usa
    try:
        from openai import OpenAI
        from openai import APIError, APITimeoutError, APIConnectionError, RateLimitError
    except Exception as e:
        raise RuntimeError("La librería 'openai' no está instalada.")

    client = OpenAI(api_key=api_key, base_url=base_url, organization=org, timeout=timeout)

    messages = [
        {
            "role": "system",
            "content": system_prompt
            or "Eres un asistente de una librería de Guatemala. Responde en español y sé conciso.",
        },
        {"role": "user", "content": mensaje},
    ]

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        choice = (resp.choices or [{}])[0]
        texto = (choice.get("message") or {}).get("content") or ""
        usage = getattr(resp, "usage", None)
        if usage and hasattr(usage, "model_dump"):
            usage = usage.model_dump()
        return {"texto": texto, "usage": usage}
    except (APITimeoutError, RateLimitError, APIConnectionError, APIError) as e:
        raise RuntimeError(f"Error de OpenAI: {e}")

