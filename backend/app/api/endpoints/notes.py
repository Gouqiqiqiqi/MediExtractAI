"""Medical notes endpoints — browse and search notes from a configured data source."""

from __future__ import annotations

import datetime as dt
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import Role, require_role
from app.dependencies import NotesRepo
from app.models.schemas import (
    NoteFilterOptions,
    NoteListResponse,
    NotePreview,
    UserClaims,
)

router = APIRouter()
logger = logging.getLogger("mediextract.api.notes")


# Declared before "/{note_id}" — otherwise FastAPI matches this path as a note
# whose id happens to be "filters".
@router.get("/filters", response_model=NoteFilterOptions)
async def note_filters(
    repo: NotesRepo,
    user: UserClaims = Depends(require_role(Role.ADMIN, Role.CLINICIAN)),
):
    """Values available to filter by in the selected data source."""
    return await repo.filter_options()


@router.get("/", response_model=NoteListResponse)
async def list_notes(
    repo: NotesRepo,
    user: UserClaims = Depends(require_role(Role.ADMIN, Role.CLINICIAN)),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str | None = None,
    note_type: Annotated[str | None, Query(description="Kind of note")] = None,
    author: Annotated[str | None, Query(description="Clinician who wrote it")] = None,
    date_from: Annotated[dt.date | None, Query(description="Earliest note date")] = None,
    date_to: Annotated[dt.date | None, Query(description="Latest note date")] = None,
):
    """List notes, narrowed by any combination of type, clinician, date and keyword."""
    logger.info(
        "User %s listing notes page=%d type=%s author=%s dates=%s..%s search=%s",
        user.sub,
        page,
        note_type,
        bool(author),
        date_from,
        date_to,
        bool(search),
    )
    notes, total = await repo.list_notes(
        page=page,
        page_size=page_size,
        search=search,
        note_type=note_type,
        author=author,
        date_from=date_from,
        date_to=date_to,
    )
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
