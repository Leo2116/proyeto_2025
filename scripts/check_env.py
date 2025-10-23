import os
from dotenv import load_dotenv, find_dotenv


def mask(v: str | None, keep: int = 4) -> str:
    if not v:
        return "<EMPTY>"
    if len(v) <= keep * 2:
        return v[0:keep] + "…"
    return v[0:keep] + "…" + v[-keep:]


def main() -> None:
    try:
        load_dotenv(find_dotenv())
    except Exception:
        pass
    keys = [
        "DATABASE_URL",
        "SQLALCHEMY_DATABASE_URI",
        "RECAPTCHA_SITE_KEY",
        "RECAPTCHA_SECRET_KEY",
        "RECAPTCHA_ENTERPRISE",
        "GOOGLE_BOOKS_API_KEY",
        "STRIPE_PUBLISHABLE_KEY",
        "STRIPE_SECRET_KEY",
        "PAYPAL_CLIENT_ID",
        "PAYPAL_CLIENT_SECRET",
        "GEMINI_API_KEY",
        "SMTP_SERVER",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASSWORD",
    ]
    print("Loaded environment summary:")
    for k in keys:
        v = os.getenv(k)
        print(f"- {k}: {'SET' if v else 'MISSING'} ({mask(v) if v else ''})")


if __name__ == "__main__":
    main()

