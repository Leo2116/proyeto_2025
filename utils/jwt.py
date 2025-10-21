import base64
import hmac
import hashlib
import json
import time
from typing import Any, Dict, Tuple


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(message: bytes, secret: str) -> str:
    sig = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
    return _b64url_encode(sig)


def create_jwt(payload: Dict[str, Any], secret: str, expires_in: int = 3600) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())

    body = dict(payload)
    if "iat" not in body:
        body["iat"] = now
    if "exp" not in body and expires_in:
        body["exp"] = now + int(expires_in)

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(body, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = _sign(signing_input, secret)
    return f"{header_b64}.{payload_b64}.{signature}"


class JWTError(ValueError):
    pass


def decode_jwt(token: str, secret: str) -> Dict[str, Any]:
    try:
        header_b64, payload_b64, signature = token.split(".")
    except ValueError:
        raise JWTError("Token malformado")

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = _sign(signing_input, secret)
    if not hmac.compare_digest(signature, expected_sig):
        raise JWTError("Firma inválida")

    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception:
        raise JWTError("Payload inválido")

    exp = payload.get("exp")
    if exp is not None and int(time.time()) > int(exp):
        raise JWTError("Token expirado")

    return payload

