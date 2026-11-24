"""Historial del Sénior sin Tutor (#175).
History of the senior without a guardian (#175).

ES: Solo metadatos del análisis (nivel, tipo, canal, plantilla, fecha). Nunca el
    texto del mensaje: la tabla analyses no lo guarda (contrato).
EN: Analysis metadata only (level, type, channel, template, date). Never the
    message text: the analyses table does not store it (contract).
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.models.user import Device
from app.schemas.analysis import MyAnalysesPage, MyAnalysis
from app.services.identity import senior_id_from_device

MAX_LIMIT = 100


def list_my_analyses(
    db: Session, device_id: uuid.UUID, limit: int, offset: int
) -> MyAnalysesPage:
    # ES: Todos los dispositivos de su cuenta (hoy uno). EN: All account devices.
    user_id = senior_id_from_device(db, device_id)
    devices = select(Device.id).where(Device.user_id == user_id)
    mine = Analysis.device_id.in_(devices)

    total = db.scalar(select(func.count()).select_from(Analysis).where(mine)) or 0
    rows = db.scalars(
        select(Analysis)
        .where(mine)
        .order_by(Analysis.created_at.desc(), Analysis.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return MyAnalysesPage(
        items=[
            MyAnalysis(
                analysis_id=row.id,
                risk_level=row.risk_level,
                threat_type=row.threat_type,
                channel=row.channel,
                block_template=row.block_template,
                created_at=row.created_at,
            )
            for row in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )
