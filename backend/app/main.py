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

    # Pre-warm Azure OpenAI client, DB pool, etc.
    from app.services.extraction_service import ExtractionService
    ExtractionService.initialize(settings)

    yield  # ── app is running ──

    # Cleanup
    ExtractionService.shutdown()


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
        response.headers["Content-Security-Policy"] = "default-src 'self'"
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
