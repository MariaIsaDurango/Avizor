"""Entorno de Alembic: lee DATABASE_URL del .env y los modelos de app.db.
Alembic environment: reads DATABASE_URL from .env and models from app.db.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

# ES: Importar app.models registra las 11 tablas en Base.metadata.
# EN: Importing app.models registers the 11 tables in Base.metadata.
import app.models  # noqa: F401
from app.core.config import settings
from app.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ES: Metadatos de los modelos para --autogenerate.
# EN: Model metadata for --autogenerate.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """ES: Genera el SQL sin conectarse. EN: Generates SQL without connecting."""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """ES: Aplica las migraciones en la base de datos. EN: Applies migrations to the DB."""
    engine = create_engine(settings.DATABASE_URL, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
