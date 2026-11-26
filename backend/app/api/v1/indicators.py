"""Reporte manual de indicadores (#170).
Manual indicator reports (#170).
"""

from fastapi import APIRouter, Response, status

from app.api.deps import DbSession, DeviceToken
from app.schemas.indicator import IndicatorReportCreate, IndicatorReportRead
from app.services import indicator_reports as service

router = APIRouter(prefix="/indicators", tags=["indicators"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={200: {"model": IndicatorReportRead}},
)
def report_indicator(
    body: IndicatorReportCreate,
    db: DbSession,
    token: DeviceToken,
    response: Response,
) -> IndicatorReportRead:
    """ES: 201 si el reporte cuenta; 200 si este dispositivo ya lo había hecho.
    EN: 201 if the report counts; 200 if this device had already reported it.
    """
    result = service.report_indicator(db, token, body)
    if not result.counted:
        response.status_code = status.HTTP_200_OK
    return result
