# configuracion.py
import os
from pathlib import Path
from urllib.parse import urlparse

try:
    # Cargar variables de entorno si existe .env (opcional)
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv())
except Exception:
    pass


class Config:
    """
    Configuración global de la aplicación Flask.
    Mantiene la base de datos SQLite 'db_libreria.sqlite' en la raíz del proyecto.
    """

    # -------------------- Flask / SQLAlchemy --------------------
    # Ruta a la base de datos (fija en la raíz del proyecto)
    BASE_DIR = Path(__file__).resolve().parent
    DB_PATH = BASE_DIR / "db_libreria.sqlite"
    # Prefer explicit SQLALCHEMY_DATABASE_URI, then DATABASE_URL (e.g., Neon), else local SQLite
    _db_url = (
        os.getenv("SQLALCHEMY_DATABASE_URI")
        or os.getenv("DATABASE_URL")
        or f"sqlite:///{DB_PATH}"
    )

    # Normalize Postgres URL to use psycopg3 driver if available
    try:
        import psycopg  # noqa: F401
        if _db_url.startswith("postgresql://") and "+" not in _db_url.split("://", 1)[0]:
            _db_url = _db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    except Exception:
        pass

    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False

    # -------------------- Seguridad / Sesiones --------------------
    SECRET_KEY = os.getenv("SECRET_KEY", "clave-secreta-para-prototipo")
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() == "true"

    # -------------------- APIs Externas --------------------
    GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY")

    # -------------------- Stripe (modo prueba) --------------------
    # Soporta tanto STRIPE_PUBLISHABLE_KEY como STRIPE_PUBLIC_KEY por compatibilidad
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", os.getenv("STRIPE_API_KEY"))
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", os.getenv("STRIPE_PUBLIC_KEY"))

    # -------------------- PayPal (Sandbox) --------------------
    PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
    PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")

    # -------------------- SMTP / Correo --------------------
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")  # tu correo SMTP
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")  # contraseña o App Password
    SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Librería Jehová Jiréh")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"   # STARTTLS (587)
    SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() == "true"  # SSL directo (465)
    SMTP_TIMEOUT = int(os.getenv("SMTP_TIMEOUT", "30"))

    # -------------------- reCAPTCHA (opcional) --------------------
    RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY")
    RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY")
    # Enterprise (Google Cloud) opcional
    RECAPTCHA_ENTERPRISE = os.getenv("RECAPTCHA_ENTERPRISE", "false").lower() in ("1", "true", "yes")
    RECAPTCHA_PROJECT_ID = os.getenv("RECAPTCHA_PROJECT_ID")
    RECAPTCHA_API_KEY = os.getenv("RECAPTCHA_API_KEY")
    # Acciones esperadas (solo si usas Enterprise con acciones; opcional)
    RECAPTCHA_ACTION_LOGIN = os.getenv("RECAPTCHA_ACTION_LOGIN", "login")
    RECAPTCHA_ACTION_REGISTER = os.getenv("RECAPTCHA_ACTION_REGISTER", "register")

    # -------------------- Enlaces y límites --------------------
    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(16 * 1024 * 1024)))  # 16MB

    # -------------------- Administración --------------------
    # Emails con acceso de administrador (separados por coma)
    # Por defecto incluye dos ejemplos; sobreescribe con ADMIN_EMAILS en .env
    ADMIN_EMAILS = [
        e.strip().lower()
        for e in os.getenv(
            "ADMIN_EMAILS",
            os.getenv("ADMIN_EMAIL", "admin@libreriajireh.com,tu_correo_admin@example.com"),
        ).split(",")
        if e.strip()
    ]
