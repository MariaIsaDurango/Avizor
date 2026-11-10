"""Endpoints de alertas del Tutor (Contrato v1.0.0).
Guardian alert endpoints (Contract v1.0.0).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbSession, GuardianToken
from app.schemas.alert import Alert, AlertPage, AlertUpdate
from app.schemas.enums import AlertStatus
from app.services import alerts as alert_service

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
def list_alerts(
    db: DbSession,
    token: GuardianToken,
    limit: Annotated[int, Query(ge=1, le=alert_service.MAX_LIMIT)] = 50,
    cursor: str | None = None,
    status: AlertStatus | None = None,
) -> AlertPage:
    """ES: Alertas del Tutor, más recientes primero (?limit=50&cursor=...).
    EN: Guardian alerts, newest first (?limit=50&cursor=...).
    """
    return alert_service.list_alerts(db, token.sub, limit, cursor, status)


@router.patch("/{alert_id}")
def update_alert(
    alert_id: uuid.UUID, body: AlertUpdate, db: DbSession, token: GuardianToken
) -> Alert:
    """ES: Marca la alerta como vista, fraude confirmado o falso positivo.
    EN: Marks the alert as seen, confirmed fraud or false positive.
    """
    return alert_service.update_alert(db, token.sub, alert_id, body)
