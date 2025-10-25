import os
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired


def _get_serializer():
    secret = os.getenv("FLASK_SECRET_KEY") or os.getenv("SECRET_KEY", "change-me")
    salt = os.getenv("EMAIL_VERIFY_SALT", "verify-email-v1")
    return URLSafeTimedSerializer(secret, salt=salt)


def gen_verify_token(user_id: str) -> str:
    s = _get_serializer()
    return s.dumps(str(user_id))


def verify_token(token: str) -> str | None:
    if not token:
        return None
    s = _get_serializer()
    max_age = int(os.getenv("EMAIL_VERIFY_MAXAGE", "86400"))
    try:
        uid = s.loads(token, max_age=max_age)
        return str(uid)
    except (BadSignature, SignatureExpired):
        return None

