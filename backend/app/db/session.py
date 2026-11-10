"""Conexión a PostgreSQL y sesión por petición.
PostgreSQL connection and per-request session.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# ES: pool_pre_ping evita errores si la conexión se cortó.
# EN: pool_pre_ping avoids errors if the connection dropped.
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """ES: Dependencia de FastAPI: abre una sesión y la cierra al terminar.
    EN: FastAPI dependency: opens a session and closes it when done.
    """
    with SessionLocal() as session:
        yield session
