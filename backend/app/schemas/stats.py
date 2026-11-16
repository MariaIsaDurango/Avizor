"""Schemas de estadísticas agregadas para el portal web.
Aggregated statistics schemas for the web portal.

ES: Solo contadores, nunca IDs ni contenido de mensajes.
EN: Counters only, never IDs or message content.
"""

from datetime import datetime

from app.schemas.common import ContractModel


class DailyRow(ContractModel):
    date: str  # YYYY-MM-DD
    amber: int = 0
    red: int = 0


class DailyStatsResponse(ContractModel):
    period_days: int
    rows: list[DailyRow]


class SummaryStatsResponse(ContractModel):
    period_days: int
    total: int
    by_threat_type: dict[str, int]
    by_channel: dict[str, int]


class IndicatorRow(ContractModel):
    type: str
    public_value: str
    report_count: int
    last_seen_at: datetime


class IndicatorRankingResponse(ContractModel):
    items: list[IndicatorRow]
