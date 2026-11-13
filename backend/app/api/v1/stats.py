"""Estadísticas agregadas y anonimizadas para el portal web.
Aggregated and anonymised statistics for the web portal.

ES: Los datos son siempre contadores: nunca IDs ni contenido de mensajes.
EN: Data is always counters: never IDs or message content.
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import DbSession
from app.models.analysis import Analysis

router = APIRouter(prefix="/stats", tags=["stats"])

Period = Literal[7, 30, 90]


class DailyRow(BaseModel):
    date: str  # YYYY-MM-DD
    green: int = 0
    amber: int = 0
    red: int = 0


class DailyStatsResponse(BaseModel):
    period_days: int
    rows: list[DailyRow]


class SummaryStatsResponse(BaseModel):
    period_days: int
    total: int
    by_threat_type: dict[str, int]
    by_channel: dict[str, int]


def _since(period_days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=period_days)


@router.get("/daily", response_model=DailyStatsResponse)
def get_daily_stats(
    db: DbSession,
    period: Annotated[Period, Query()] = 7,
) -> DailyStatsResponse:
    """ES: Ataques diarios agrupados por nivel de riesgo (green/amber/red).
    EN: Daily attacks grouped by risk level (green/amber/red).
    """
    since = _since(period)
    rows = db.execute(
        select(
            func.date(Analysis.created_at).label("day"),
            Analysis.risk_level,
            func.count().label("n"),
        )
        .where(Analysis.created_at >= since)
        .group_by(func.date(Analysis.created_at), Analysis.risk_level)
        .order_by(func.date(Analysis.created_at))
    ).all()

    # ES: Pivota (día, risk_level, n) → {día: {green, amber, red}}.
    # EN: Pivot (day, risk_level, n) → {day: {green, amber, red}}.
    pivoted: dict[str, dict[str, int]] = {}
    for day, risk_level, n in rows:
        key = str(day)
        if key not in pivoted:
            pivoted[key] = {"green": 0, "amber": 0, "red": 0}
        pivoted[key][risk_level] = n

    return DailyStatsResponse(
        period_days=period,
        rows=[DailyRow(date=d, **counts) for d, counts in sorted(pivoted.items())],
    )


@router.get("/summary", response_model=SummaryStatsResponse)
def get_summary_stats(
    db: DbSession,
    period: Annotated[Period, Query()] = 7,
) -> SummaryStatsResponse:
    """ES: Totales por tipo de amenaza y canal en el período indicado.
    EN: Totals by threat type and channel for the given period.
    """
    since = _since(period)

    total = (
        db.scalar(select(func.count(Analysis.id)).where(Analysis.created_at >= since))
        or 0
    )

    by_threat = db.execute(
        select(Analysis.threat_type, func.count().label("n"))
        .where(Analysis.created_at >= since)
        .group_by(Analysis.threat_type)
    ).all()

    by_channel = db.execute(
        select(Analysis.channel, func.count().label("n"))
        .where(Analysis.created_at >= since)
        .group_by(Analysis.channel)
    ).all()

    return SummaryStatsResponse(
        period_days=period,
        total=total,
        by_threat_type={row.threat_type: row.n for row in by_threat},
        by_channel={row.channel: row.n for row in by_channel},
    )
