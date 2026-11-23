"""Estadísticas agregadas y anonimizadas para el portal web.
Aggregated and anonymised statistics for the web portal.

ES: Los datos son siempre contadores: nunca IDs ni contenido de mensajes.
    Solo se publican análisis amber y red (ataques); los green no cuentan.
EN: Data is always counters: never IDs or message content.
    Only amber and red analyses (attacks) are published; green ones don't count.
"""

from datetime import UTC, date, datetime, timedelta
from enum import IntEnum
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select, text

from app.api.deps import DbSession
from app.models.analysis import Analysis
from app.schemas.enums import RiskLevel
from app.schemas.stats import (
    DailyRow,
    DailyStatsResponse,
    IndicatorRankingResponse,
    IndicatorRow,
    SummaryStatsResponse,
)

router = APIRouter(prefix="/stats", tags=["stats"])


class Period(IntEnum):
    """ES: Períodos válidos en días. EN: Valid periods in days."""

    WEEK = 7
    MONTH = 30
    QUARTER = 90


def _since(period_days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=period_days)


def _date_range(period_days: int) -> list[str]:
    """ES: Genera todos los días del período para rellenar huecos con ceros.
    EN: Generates every day in the period to fill gaps with zeros.
    """
    today = date.today()
    return [str(today - timedelta(days=i)) for i in range(period_days - 1, -1, -1)]


@router.get("/daily", response_model=DailyStatsResponse)
def get_daily_stats(
    db: DbSession,
    period: Annotated[Period, Query()] = Period.WEEK,
) -> DailyStatsResponse:
    """ES: Ataques diarios (solo amber y red) agrupados por nivel de riesgo.
    EN: Daily attacks (amber and red only) grouped by risk level.
    """
    since = _since(period)
    rows = db.execute(
        select(
            func.date(Analysis.created_at).label("day"),
            Analysis.risk_level,
            func.count().label("n"),
        )
        .where(
            Analysis.created_at >= since,
            Analysis.risk_level != RiskLevel.GREEN,
        )
        .group_by(func.date(Analysis.created_at), Analysis.risk_level)
        .order_by(func.date(Analysis.created_at))
    ).all()

    # ES: Pivota (día, risk_level, n) → {día: {amber, red}}.
    # EN: Pivot (day, risk_level, n) → {day: {amber, red}}.
    pivoted: dict[str, dict[str, int]] = {}
    for day, risk_level, n in rows:
        key = str(day)
        if key not in pivoted:
            pivoted[key] = {"amber": 0, "red": 0}
        pivoted[key][risk_level] = n

    # ES: Rellena con ceros los días sin datos para evitar huecos en la gráfica.
    # EN: Fill days with no data with zeros to avoid gaps in the chart.
    return DailyStatsResponse(
        period_days=period,
        rows=[
            DailyRow(date=d, **pivoted.get(d, {"amber": 0, "red": 0}))
            for d in _date_range(period)
        ],
    )


@router.get("/summary", response_model=SummaryStatsResponse)
def get_summary_stats(
    db: DbSession,
    period: Annotated[Period, Query()] = Period.WEEK,
) -> SummaryStatsResponse:
    """ES: Totales por tipo de amenaza y canal (solo ataques amber y red).
    EN: Totals by threat type and channel (amber and red attacks only).
    """
    since = _since(period)
    attacks_filter = (
        Analysis.created_at >= since,
        Analysis.risk_level != RiskLevel.GREEN,
    )

    total = db.scalar(select(func.count(Analysis.id)).where(*attacks_filter)) or 0

    by_threat = db.execute(
        select(Analysis.threat_type, func.count().label("n"))
        .where(*attacks_filter)
        .group_by(Analysis.threat_type)
    ).all()

    by_channel = db.execute(
        select(Analysis.channel, func.count().label("n"))
        .where(*attacks_filter)
        .group_by(Analysis.channel)
    ).all()

    return SummaryStatsResponse(
        period_days=period,
        total=total,
        by_threat_type={row.threat_type: row.n for row in by_threat},
        by_channel={row.channel: row.n for row in by_channel},
    )


@router.get("/indicators")
def get_indicator_ranking(db: DbSession) -> IndicatorRankingResponse:
    """ES: Ranking público de indicadores con ≥5 reportes (teléfonos enmascarados).
    EN: Public ranking of indicators with ≥5 reports (phones are masked).
    """
    rows = (
        db.execute(
            text(
                "SELECT type, public_value, report_count, last_seen_at"
                " FROM v_indicator_ranking LIMIT 100"
            )
        )
        .mappings()
        .all()
    )
    return IndicatorRankingResponse(items=[IndicatorRow(**dict(row)) for row in rows])
