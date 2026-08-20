"""Aggregate API router — all versioned endpoints mount here."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.endpoints import auth, export, extraction, notes, upload

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(notes.router, prefix="/notes", tags=["notes"])
api_router.include_router(extraction.router, prefix="/extraction", tags=["extraction"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(export.router, prefix="/export", tags=["export"])
