"""Medical notes endpoints — browse and search notes from the SQL database."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.config import Settings, get_settings
from app.core.security import Role, get_current_user, require_role
from app.models.schemas import NoteListResponse, NotePreview, UserClaims
from app.services.database_service import DatabaseService

router = APIRouter()
logger = logging.getLogger("mediextract.api.notes")


def _get_db_service(settings: Settings = Depends(get_settings)) -> DatabaseService:
    return DatabaseService(settings)


@router.get("/", response_model=NoteListResponse)
async def list_notes(
    user: UserClaims = Depends(require_role(Role.ADMIN, Role.CLINICIAN)),
    db: DatabaseService = Depends(_get_db_service),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str | None = None,
):
    """List medical notes with pagination and optional free-text search."""
    logger.info(
        "User %s listing notes page=%d search=%s",
        user.sub,
        page,
        bool(search),
    )
    notes, total = await db.list_notes(
        page=page, page_size=page_size, search=search
    )
    return NoteListResponse(
        items=notes,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{note_id}", response_model=NotePreview)
async def get_note(
    note_id: str,
    user: UserClaims = Depends(require_role(Role.ADMIN, Role.CLINICIAN)),
    db: DatabaseService = Depends(_get_db_service),
):
    """Retrieve a single note's metadata and text preview."""
    logger.info("User %s viewing note %s", user.sub, note_id)
    return await db.get_note(note_id)
