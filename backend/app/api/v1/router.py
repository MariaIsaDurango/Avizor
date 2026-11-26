"""Router principal de la API v1: todas las rutas cuelgan de /api/v1.
Main API v1 router: every route hangs from /api/v1.
"""

from fastapi import APIRouter

from app.api.v1 import (
    alerts,
    analyses,
    auth,
    consents,
    devices,
    indicators,
    my_analyses,
    pairings,
    senior,
    stats,
    unlocks,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(pairings.router)
api_router.include_router(consents.router)
api_router.include_router(analyses.router)
api_router.include_router(my_analyses.router)
api_router.include_router(indicators.router)
api_router.include_router(alerts.router)
api_router.include_router(unlocks.router)
api_router.include_router(devices.router)
api_router.include_router(senior.router)
api_router.include_router(stats.router)
