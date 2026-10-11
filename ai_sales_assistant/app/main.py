from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_v1_router
from app.config import get_settings
from app.core.error_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import register_middleware
from app.routers import system, web

STATIC_DIR = Path(__file__).resolve().parent / "static"

DESCRIPTION = (
    "AI-powered assistant that generates commercial emails, sales proposals, "
    "follow-ups, WhatsApp messages and customer summaries."
)

OPENAPI_TAGS = [
    {"name": "System", "description": "Application information and health check."},
    {"name": "Authentication", "description": "Accounts, login sessions (HttpOnly cookie) and password recovery."},
    {"name": "Generations", "description": "AI generation of commercial content and its history (per user)."},
    {"name": "Pricing", "description": "Discount calculation (Decimal, done by the backend, never by the AI)."},
]


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=DESCRIPTION,
        openapi_tags=OPENAPI_TAGS,
    )
    register_exception_handlers(app)
    register_middleware(app)
    app.include_router(system.router)
    app.include_router(api_v1_router)
    app.include_router(web.router)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
