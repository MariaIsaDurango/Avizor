import asyncio
import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import problem_response, register_error_handlers
from app.core.limiter import limiter
from app.jobs.purge import purge_loop
from app.schemas.enums import ErrorCode
from app.services.agent import close_agent, initialize_agent
from app.services.detection.reputation import (
    create_runtime,
    install_private_request_filters,
    new_client,
)
from app.web.router import web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start periodic retention purge and the reputation runtime."""
    task = None
    if settings.RETENTION_PURGE_MINUTES > 0:
        task = asyncio.create_task(purge_loop(settings.RETENTION_PURGE_MINUTES))
    remove_filters = install_private_request_filters()
    try:
        # AI inference is CPU-intensive; do not block the event loop during startup.
        await asyncio.to_thread(initialize_agent, settings.AVIZOR_RAG_ENABLED)
        async with new_client() as client:
            app.state.reputation = await asyncio.to_thread(
                create_runtime, client, settings
            )
            yield
    finally:
        await asyncio.to_thread(close_agent)
        app.state.reputation = None
        remove_filters()
        if task:
            task.cancel()


_is_dev = settings.APP_ENV != "production"

app = FastAPI(
    title="Avizor API",
    version=settings.CONTRACT_VERSION,
    docs_url="/api/v1/docs" if _is_dev else None,
    redoc_url="/api/v1/redoc" if _is_dev else None,
    openapi_url="/api/v1/openapi.json" if _is_dev else None,
    lifespan=lifespan,
)
app.state.limiter = limiter


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return problem_response(
        429,
        ErrorCode.RATE_LIMITED,
        "Demasiados intentos de inicio de sesión. Espera un minuto e inténtalo de nuevo.",
    )


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

# ES: Usamos JWT Bearer (no cookies): sin credenciales y sin "*" con credenciales.
#     La app móvil no usa CORS; el portal se sirve desde el mismo dominio.
# EN: We use JWT Bearer (no cookies): no credentials and no "*" with credentials.
#     The mobile app does not use CORS; the portal is served from the same domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_STATIC_DIR = pathlib.Path(__file__).parent / "web" / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="web_static")

register_error_handlers(app)
app.include_router(api_router)
app.include_router(web_router)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Contract-Version"] = settings.CONTRACT_VERSION
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.APP_ENV == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


@app.get("/api/v1/health", tags=["system"])
async def health():
    return {"status": "ok", "contract_version": settings.CONTRACT_VERSION}
