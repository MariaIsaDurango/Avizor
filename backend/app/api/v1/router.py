"""Router principal de la API v1: todas las rutas cuelgan de /api/v1.
Main API v1 router: every route hangs from /api/v1.
"""

from fastapi import APIRouter

from app.api.v1 import auth

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
