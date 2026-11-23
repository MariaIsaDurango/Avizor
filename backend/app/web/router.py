import pathlib
from datetime import date

from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = pathlib.Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

web_router = APIRouter(include_in_schema=False)

# ES: Contexto común a todas las páginas (año para el footer).
# EN: Context shared by all pages (year for the footer).
_COMMON = {"year": date.today().year}


@web_router.get("/", response_class=HTMLResponse, name="dashboard")
async def dashboard(request: Request):
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"active_page": "dashboard", **_COMMON},
    )


@web_router.get("/analytics", response_class=HTMLResponse, name="analytics")
async def analytics(request: Request):
    return templates.TemplateResponse(
        request,
        "analytics.html",
        {"active_page": "analytics", **_COMMON},
    )


@web_router.get("/indicators", response_class=HTMLResponse, name="indicators")
async def indicators(request: Request):
    return templates.TemplateResponse(
        request,
        "indicators.html",
        {"active_page": "indicators", **_COMMON},
    )


@web_router.get("/support", response_class=HTMLResponse, name="support")
async def support(request: Request):
    return templates.TemplateResponse(
        request,
        "support.html",
        {"active_page": "support", **_COMMON},
    )


@web_router.get("/panel", response_class=HTMLResponse, name="panel")
async def panel(request: Request):
    return templates.TemplateResponse(
        request,
        "panel.html",
        {"active_page": "panel", **_COMMON},
    )


@web_router.get("/register", response_class=HTMLResponse, name="register")
async def register(request: Request):
    return templates.TemplateResponse(
        request,
        "register.html",
        {**_COMMON},
    )


@web_router.get("/login", response_class=HTMLResponse, name="login_page")
async def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {**_COMMON},
    )


@web_router.get("/download", response_class=HTMLResponse, name="download")
async def download(request: Request):
    return templates.TemplateResponse(
        request,
        "download.html",
        {**_COMMON},
    )


@web_router.get("/verify-email", response_class=HTMLResponse, name="verify_email")
async def verify_email_page(request: Request):
    return templates.TemplateResponse(
        request,
        "verify-email.html",
        {**_COMMON},
    )


@web_router.get("/forgot-password", response_class=HTMLResponse, name="forgot_password")
async def forgot_password_page(request: Request):
    return templates.TemplateResponse(
        request,
        "forgot-password.html",
        {**_COMMON},
    )


@web_router.get("/reset-password", response_class=HTMLResponse, name="reset_password")
async def reset_password_page(request: Request):
    return templates.TemplateResponse(
        request,
        "reset-password.html",
        {**_COMMON},
    )
