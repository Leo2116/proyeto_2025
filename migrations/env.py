from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Try to load .env for DATABASE_URL/SQLALCHEMY_DATABASE_URI
try:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv())
except Exception:
    pass

# Import your SQLAlchemy Base metadata
try:
    from inicializar_db import Base
    target_metadata = Base.metadata
except Exception:
    target_metadata = None

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Helper: resolve database URL with env overrides
def _normalize_pg_url(url: str) -> str:
    """Ensure SQLAlchemy uses psycopg v3 if available.
    If the URL is plain 'postgresql://', swap to 'postgresql+psycopg://'.
    """
    try:
        import psycopg  # type: ignore
        has_psycopg3 = True
    except Exception:
        has_psycopg3 = False
    if has_psycopg3 and url.startswith("postgresql://") and "+" not in url.split("://", 1)[0]:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _resolve_database_url() -> str | None:
    # Prefer explicit env vars
    url = os.getenv("SQLALCHEMY_DATABASE_URI") or os.getenv("DATABASE_URL")
    if url:
        return _normalize_pg_url(url)
    # Fallback to alembic.ini value if present
    ini_url = config.get_main_option("sqlalchemy.url")
    return _normalize_pg_url(ini_url) if ini_url else None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = _resolve_database_url()
    if not url:
        raise RuntimeError(
            "No database URL configured. Set SQLALCHEMY_DATABASE_URI or DATABASE_URL in environment/.env, or alembic.ini sqlalchemy.url."
        )
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Ensure config has the resolved URL
    url = _resolve_database_url()
    if not url:
        raise RuntimeError(
            "No database URL configured. Set SQLALCHEMY_DATABASE_URI or DATABASE_URL in environment/.env, or alembic.ini sqlalchemy.url."
        )
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = url

    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
