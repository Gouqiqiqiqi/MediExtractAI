"""Medical notes endpoints — browse and search notes from a configured data source."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import Role, require_role
from app.dependencies import NotesRepo
from app.models.schemas import NoteListResponse, NotePreview, UserClaims

router = APIRouter()
logger = logging.getLogger("mediextract.api.notes")


@router.get("/", response_model=NoteListResponse)
async def list_notes(
    repo: NotesRepo,
    user: UserClaims = Depends(require_role(Role.ADMIN, Role.CLINICIAN)),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str | None = None,
):
    """List medical notes with pagination and optional free-text search."""
    logger.info("User %s listing notes page=%d search=%s", user.sub, page, bool(search))
    notes, total = await repo.list_notes(page=page, page_size=page_size, search=search)
    return NoteListResponse(items=notes, total=total, page=page, page_size=page_size)


@router.get("/{note_id}", response_model=NotePreview)
async def get_note(
    note_id: str,
    repo: NotesRepo,
    user: UserClaims = Depends(require_role(Role.ADMIN, Role.CLINICIAN)),
):
    """Retrieve a single note's metadata and text preview."""
    logger.info("User %s viewing note %s", user.sub, note_id)
    note = await repo.get_note(note_id)
    if note is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found")
    return note
