import os
from typing import Tuple, Dict
import requests


PAYPAL_BASE = os.getenv("PAYPAL_API_BASE", "https://api-m.sandbox.paypal.com").rstrip("/")


def _obtener_token(timeout: int = 10) -> str:
    cid = os.getenv("PAYPAL_CLIENT_ID")
    secret = os.getenv("PAYPAL_CLIENT_SECRET")
    if not cid or not secret:
        raise ValueError("Faltan PAYPAL_CLIENT_ID o PAYPAL_CLIENT_SECRET.")

    url = f"{PAYPAL_BASE}/v1/oauth2/token"
    resp = requests.post(
        url,
        auth=(cid, secret),
        data={"grant_type": "client_credentials"},
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json() or {}
    token = data.get("access_token")
    if not token:
        raise RuntimeError("No se pudo obtener token de PayPal.")
    return token


def crear_orden(total: float, currency: str = "GTQ", timeout: int = 10) -> Dict:
    if not isinstance(total, (int, float)) or total <= 0:
        raise ValueError("Total inválido.")
    token = _obtener_token(timeout=timeout)
    url = f"{PAYPAL_BASE}/v2/checkout/orders"
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {
                    "currency_code": (currency or "GTQ").upper(),
                    "value": f"{total:.2f}",
                }
            }
        ],
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    data = resp.json() or {}
    return data

