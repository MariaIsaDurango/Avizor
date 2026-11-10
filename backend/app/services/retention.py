"""Retención mínima de datos (RGPD): borra lo que ya no es necesario.
Minimum data retention (GDPR): deletes what is no longer needed.

ES: Plazos del contrato (sección "Privacidad, retención"):
    - temp_content: hasta delete_at (amber 7 d, red 30 d); si hay un caso
      abierto, se conserva hasta 90 d después de cerrarlo.
    - unlocks pendientes vencidos (24 h) → expired.
    - indicators sin reportes en 12 meses → borrado (si no tienen casos).
EN: Contract periods ("Privacy, retention" section):
    - temp_content: until delete_at (amber 7 d, red 30 d); with an open case,
      kept until 90 d after it is closed.
    - expired pending unlocks (24 h) → expired.
    - indicators with no reports in 12 months → deleted (if they have no cases).
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, exists, or_, select, update
from sqlalchemy.orm import Session

from app.models.alert import Unlock
from app.models.analysis import TempContent
from app.models.indicator import Case, Indicator
from app.schemas.enums import UnlockStatus

CASE_GRACE = timedelta(days=90)
INDICATOR_RETENTION = timedelta(days=365)


@dataclass(frozen=True)
class PurgeResult:
    """ES: Solo contadores, nunca datos. EN: Counters only, never data."""

    temp_content_deleted: int
    unlocks_expired: int
    indicators_deleted: int


def purge_expired(db: Session, now: datetime | None = None) -> PurgeResult:
    now = now or datetime.now(UTC)

    # ES: Un caso abierto (o cerrado hace < 90 d) retiene el texto.
    # EN: An open case (or closed < 90 d ago) keeps the text.
    case_holds_text = exists(
        select(Case.id).where(
            Case.analysis_id == TempContent.analysis_id,
            or_(Case.closed_at.is_(None), Case.closed_at > now - CASE_GRACE),
        )
    )
    temp_deleted = db.execute(
        delete(TempContent).where(TempContent.delete_at <= now, ~case_holds_text)
    ).rowcount

    unlocks_expired = db.execute(
        update(Unlock)
        .where(
            Unlock.status == UnlockStatus.PENDING_GUARDIAN,
            Unlock.expires_at <= now,
        )
        .values(status=UnlockStatus.EXPIRED)
    ).rowcount

    has_case = exists(select(Case.id).where(Case.indicator_id == Indicator.id))
    indicators_deleted = db.execute(
        delete(Indicator).where(
            Indicator.last_seen_at <= now - INDICATOR_RETENTION, ~has_case
        )
    ).rowcount

    db.commit()
    return PurgeResult(temp_deleted, unlocks_expired, indicators_deleted)
