import os
from typing import Optional


def crear_payment_intent(total_en_centavos: int, moneda: str = "gtq", timeout: int = 10) -> str:
    """
    Crea un PaymentIntent en Stripe y devuelve client_secret.
    Lanza ValueError si falta clave o monto inválido.
    """
    if not isinstance(total_en_centavos, int) or total_en_centavos <= 0:
        raise ValueError("El monto debe ser un entero en centavos mayor a 0.")

    secret_key = os.getenv("STRIPE_SECRET_KEY") or os.getenv("STRIPE_API_KEY")
    if not secret_key:
        raise ValueError("Falta STRIPE_SECRET_KEY en el entorno.")

    try:
        import stripe
    except Exception as e:
        raise RuntimeError("La librería 'stripe' no está instalada.")

    stripe.api_key = secret_key
    # Opcional: setea timeout
    stripe.default_http_client = stripe.http_client.RequestsClient(timeout=timeout)
    intent = stripe.PaymentIntent.create(
        amount=total_en_centavos,
        currency=(moneda or "gtq").lower(),
        automatic_payment_methods={"enabled": True},
    )
    return intent.get("client_secret") or intent.client_secret

