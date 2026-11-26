"""Reporte manual de números por el Sénior (#170).
Manual number reports by the senior (#170).

ES: Cada dispositivo cuenta una sola vez por número (tabla indicator_reports),
    así report_count mide personas y no repeticiones (ADR 0005). El número se
    guarda solo como HMAC y enmascarado. Con 1 reporte la vía rápida marca el
    número en ámbar y con 5 en rojo (REPORTS_RED); con 5 entra en el ranking.
EN: Each device counts once per number (indicator_reports table), so
    report_count measures people, not repetitions (ADR 0005). The number is
    stored only as HMAC and masked. With 1 report the fast path marks it amber
    and with 5 red (REPORTS_RED); with 5 it enters the ranking.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.privacy import (
    InvalidPhoneError,
    hash_indicator,
    normalize_phone,
    public_value,
)
from app.core.security import TokenPayload
from app.models.indicator import Indicator, IndicatorReport
from app.schemas.enums import ErrorCode, IndicatorType
from app.schemas.indicator import IndicatorReportCreate, IndicatorReportRead
from app.services.devices import touch_device
from app.services.identity import request_device_id, senior_id_from_device


def report_indicator(
    db: Session, token: TokenPayload, body: IndicatorReportCreate
) -> IndicatorReportRead:
    device_id = request_device_id(token, body.device_id)
    senior_id_from_device(db, device_id)
    try:
        phone = normalize_phone(body.value)
    except InvalidPhoneError:
        raise ApiError(
            422, ErrorCode.VALIDATION_ERROR, "El número no es válido."
        ) from None

    now = datetime.now(UTC)
    kind = IndicatorType.PHONE
    value_hash = hash_indicator(kind, phone)

    # ES: Crea el indicador si no existe; report_count empieza en 0 y solo sube
    #     con un reporte nuevo de un dispositivo.
    # EN: Creates the indicator if missing; report_count starts at 0 and only
    #     grows with a new report from a device.
    db.execute(
        insert(Indicator)
        .values(
            type=kind,
            value_hash=value_hash,
            public_value=public_value(kind, phone),
            report_count=0,
            first_seen_at=now,
            last_seen_at=now,
        )
        .on_conflict_do_nothing(index_elements=["type", "value_hash"])
    )
    indicator_id: uuid.UUID = db.scalar(
        select(Indicator.id).where(
            Indicator.type == kind, Indicator.value_hash == value_hash
        )
    )
    report_id = db.scalar(
        insert(IndicatorReport)
        .values(
            indicator_id=indicator_id,
            device_id=device_id,
            threat_type=body.threat_type,
        )
        .on_conflict_do_nothing(index_elements=["indicator_id", "device_id"])
        .returning(IndicatorReport.id)
    )
    counted = report_id is not None
    if counted:
        db.execute(
            update(Indicator)
            .where(Indicator.id == indicator_id)
            .values(report_count=Indicator.report_count + 1, last_seen_at=now)
        )
    touch_device(db, device_id, now)
    db.commit()
    return IndicatorReportRead(
        type="phone",
        public_value=public_value(kind, phone),
        threat_type=body.threat_type,
        counted=counted,
    )
