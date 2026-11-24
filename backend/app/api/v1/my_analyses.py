"""Historial de análisis del Sénior sin Tutor (#175).
Analysis history of the senior without a guardian (#175).
"""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbSession, SeniorSoloToken
from app.schemas.analysis import MyAnalysesPage
from app.services import my_analyses as service

router = APIRouter(prefix="/my-analyses", tags=["analyses"])


@router.get("")
def list_my_analyses(
    db: DbSession,
    token: SeniorSoloToken,
    limit: Annotated[int, Query(ge=1, le=service.MAX_LIMIT)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MyAnalysesPage:
    """ES: Sus análisis, más recientes primero (?limit=20&offset=0). Solo
    senior_solo: el Sénior vinculado no tiene historial propio (lo ve su Tutor).
    EN: Their analyses, newest first (?limit=20&offset=0). senior_solo only: a
    paired senior has no own history (their guardian sees it).
    """
    return service.list_my_analyses(db, token.sub, limit, offset)
