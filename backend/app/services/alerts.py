"""Alertas para el Tutor: listado paginado y cambio de estado.
Guardian alerts: paginated list and status change.

ES: Cada Tutor solo ve sus propias alertas. Paginación por cursor (contrato).
EN: Each guardian only sees their own alerts. Cursor pagination (contract).
"""

import base64
import uuid
from datetime import datetime

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models.alert import Alert
from app.models.analysis import Analysis
from app.models.user import Device, User
from app.schemas.alert import Alert as AlertSchema
from app.schemas.alert import AlertPage, AlertUpdate
from app.schemas.enums import AlertStatus, ErrorCode

MAX_LIMIT = 100


def _encode_cursor(created_at: datetime, alert_id: uuid.UUID) -> str:
    raw = f"{created_at.isoformat()}|{alert_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """ES: El cursor es opaco para la app; si está manipulado, 422.
    EN: The cursor is opaque to the app; if tampered with, 422.
    """
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        created_at, alert_id = raw.split("|")
        return datetime.fromisoformat(created_at), uuid.UUID(alert_id)
    except (ValueError, UnicodeDecodeError):
        raise ApiError(
            422, ErrorCode.VALIDATION_ERROR, "El cursor no es válido."
        ) from None


def _base_query(guardian_id: uuid.UUID) -> Select:
    """ES: Alerta + datos del análisis + nombre del Sénior (sin texto del mensaje).
    EN: Alert + analysis data + senior name (no message text).
    """
    return (
        select(Alert, Analysis, User)
        .join(Analysis, Analysis.id == Alert.analysis_id)
        .join(Device, Device.id == Analysis.device_id)
        .join(User, User.id == Device.user_id)
        .where(Alert.guardian_id == guardian_id)
    )


def _to_schema(alert: Alert, analysis: Analysis, senior: User) -> AlertSchema:
    return AlertSchema(
        id=alert.id,
        analysis_id=alert.analysis_id,
        senior_id=senior.id,
        senior_name=senior.display_name,
        risk_level=analysis.risk_level,
        threat_type=analysis.threat_type,
        channel=analysis.channel,
        summary=alert.summary,
        explanation=alert.explanation,
        evidence=alert.evidence,
        status=alert.status,
        created_at=alert.created_at,
    )


def list_alerts(
    db: Session,
    guardian_id: uuid.UUID,
    limit: int,
    cursor: str | None,
    status: AlertStatus | None,
) -> AlertPage:
    query = _base_query(guardian_id)
    if status:
        query = query.where(Alert.status == status)
    if cursor:
        created_at, alert_id = _decode_cursor(cursor)
        # ES: Más recientes primero; el id desempata alertas del mismo instante.
        # EN: Newest first; the id breaks ties between alerts at the same instant.
        query = query.where(
            or_(
                Alert.created_at < created_at,
                and_(Alert.created_at == created_at, Alert.id < alert_id),
            )
        )
    rows = db.execute(
        query.order_by(Alert.created_at.desc(), Alert.id.desc()).limit(limit + 1)
    ).all()

    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = (
        _encode_cursor(rows[-1].Alert.created_at, rows[-1].Alert.id)
        if has_more
        else None
    )
    return AlertPage(
        items=[_to_schema(row.Alert, row.Analysis, row.User) for row in rows],
        next_cursor=next_cursor,
    )


def update_alert(
    db: Session, guardian_id: uuid.UUID, alert_id: uuid.UUID, body: AlertUpdate
) -> AlertSchema:
    row = db.execute(_base_query(guardian_id).where(Alert.id == alert_id)).first()
    # ES: 404 también si es de otro Tutor: no revela que existe.
    # EN: 404 also if it belongs to another guardian: does not reveal it exists.
    if row is None:
        raise ApiError(404, ErrorCode.NOT_FOUND, "Alerta no encontrada.")
    row.Alert.status = body.status
    db.commit()
    return _to_schema(row.Alert, row.Analysis, row.User)
