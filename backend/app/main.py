from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings

app = FastAPI(
    title="Avizor API",
    version="1.0.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.APP_ENV == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_contract_version_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Contract-Version"] = settings.CONTRACT_VERSION
    return response


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "type": "https://avizor.app/errors/not-found",
            "title": "Recurso no encontrado",
            "status": 404,
            "code": "NOT_FOUND",
            "detail": f"La ruta {request.url.path} no existe.",
        },
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "type": "https://avizor.app/errors/internal-error",
            "title": "Error interno del servidor",
            "status": 500,
            "code": "INTERNAL_ERROR",
            "detail": "Ha ocurrido un error inesperado.",
        },
    )


@app.get("/api/v1/health", tags=["system"])
async def health():
    return {"status": "ok", "contract_version": settings.CONTRACT_VERSION}
