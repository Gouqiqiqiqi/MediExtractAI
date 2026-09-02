"""MediExtractAI — FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.config import get_settings
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown hooks."""
    settings = get_settings()
    setup_logging(settings.log_level)
    settings.ensure_data_dir()

    # The application's own database — audit log, jobs, saved schemas and the
    # registry of customer databases we know how to read.
    from app.services import app_database, data_source_service, database_service

    app_database.init_engine(settings)
    await app_database.create_tables()
    await app_database.ensure_columns()
    async with app_database.session_factory()() as session:
        await data_source_service.ensure_bootstrap_source(session, settings)

    # Pre-warm Azure OpenAI client, DB pool, etc.
    from app.services.extraction_service import ExtractionService
    ExtractionService.initialize(settings)

    yield  # ── app is running ──

    # Cleanup
    ExtractionService.shutdown()
    await database_service.dispose_engines()
    await app_database.dispose()


# FastAPI serves Swagger UI and ReDoc from jsdelivr, and the favicon from its
# own site. Named here so the exception is visible rather than buried in a
# header string.
DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")
DOCS_CSP = (
    "default-src 'self'; "
    "script-src 'self' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "worker-src 'self' blob:"
)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="MediExtractAI",
        description="Clinical Note Extraction & Tabulation API",
        version="0.1.0",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
        lifespan=lifespan,
    )

    # ── CORS ──
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=600,
    )

    # ── Security headers middleware ──
    @app.middleware("http")
    async def security_headers(request: Request, call_next):  # noqa: ANN001
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )
        # The API returns JSON and files, never markup, so the strictest policy
        # is the right one — the SPA's own policy is set by nginx, which serves
        # it. The exception is the interactive docs: FastAPI renders those from
        # a CDN, so a blanket 'self' left the page the README tells people to
        # open in development silently blank.
        response.headers["Content-Security-Policy"] = (
            DOCS_CSP if request.url.path.startswith(DOCS_PATHS) else "default-src 'none'"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        return response

    # ── Global exception handler ──
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        # Never leak internal details in production
        import logging
        logger = logging.getLogger("mediextract")
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal error occurred."},
        )

    # ── Routes ──
    app.include_router(api_router, prefix="/api/v1")

    # ── Health check ──
    @app.get("/health", tags=["system"])
    async def health():
        return {"status": "healthy", "version": app.version}

    return app


app = create_app()
