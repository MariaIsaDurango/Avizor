"""Tarea de limpieza: una vez (CLI) o cada N minutos (dentro de la API).
Purge job: once (CLI) or every N minutes (inside the API).

ES: Uso manual / EN: Manual usage:
    cd backend && python -m app.jobs.purge
"""

import asyncio
import logging

from sqlalchemy import text

from app.db.session import SessionLocal
from app.services.retention import PurgeResult, purge_expired

logger = logging.getLogger(__name__)

# ES: Bloqueo de PostgreSQL: si hay varias copias de la API, solo una limpia.
# EN: PostgreSQL lock: with several API copies, only one runs the purge.
PURGE_LOCK_ID = 7_421_001


def run_purge_once() -> PurgeResult | None:
    """ES: None si otra instancia ya está limpiando. EN: None if another runs it."""
    with SessionLocal() as db:
        locked = db.scalar(
            text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
            {"lock_id": PURGE_LOCK_ID},
        )
        if not locked:
            return None
        return purge_expired(db)


async def purge_loop(interval_minutes: int) -> None:
    """ES: Bucle en segundo plano; un fallo no tumba la API.
    EN: Background loop; a failure does not bring down the API.
    """
    while True:
        try:
            result = await asyncio.to_thread(run_purge_once)
            if result:
                logger.info("Retention purge: %s", result)
        except Exception:
            logger.exception("Retention purge failed")
        await asyncio.sleep(interval_minutes * 60)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run_purge_once())
