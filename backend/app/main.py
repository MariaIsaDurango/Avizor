import pathlib

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.web.router import web_router

app = FastAPI(
    title="Avizor API",
    version=settings.CONTRACT_VERSION,
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
)

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
async def add_contract_version_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Contract-Version"] = settings.CONTRACT_VERSION
    return response


@app.get("/api/v1/health", tags=["system"])
async def health():
    return {"status": "ok", "contract_version": settings.CONTRACT_VERSION}
