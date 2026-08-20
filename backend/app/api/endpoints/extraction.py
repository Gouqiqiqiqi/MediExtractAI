"""Extraction endpoints — run AI extraction on notes or uploaded text."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import Settings, get_settings
from app.core.security import Role, require_role
from app.models.schemas import (
    ExtractionRequest,
    ExtractionResponse,
    FileExtractionRequest,
    UserClaims,
)
from app.services.database_service import DatabaseService
from app.services.extraction_service import ExtractionService

router = APIRouter()
logger = logging.getLogger("mediextract.api.extraction")


@router.post("/from-database", response_model=ExtractionResponse)
async def extract_from_database(
    body: ExtractionRequest,
    user: UserClaims = Depends(require_role(Role.ADMIN, Role.CLINICIAN)),
    settings: Settings = Depends(get_settings),
):
    """Extract structured data from medical notes stored in the SQL database.

    The user supplies note IDs and an output schema (column definitions).
    """
    logger.info(
        "User %s extracting from %d notes, %d columns",
        user.sub,
        len(body.note_ids),
        len(body.columns),
    )

    db = DatabaseService(settings)
    notes_text = await db.get_notes_text(body.note_ids)

    extractor = ExtractionService.instance()
    try:
        rows = await extractor.extract(
            texts=notes_text,
            columns=body.columns,
        )
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    return ExtractionResponse(
        columns=body.columns,
        rows=rows,
        source="database",
        note_count=len(body.note_ids),
    )


@router.post("/from-text", response_model=ExtractionResponse)
async def extract_from_text(
    body: FileExtractionRequest,
    user: UserClaims = Depends(require_role(Role.ADMIN, Role.CLINICIAN)),
):
    """Extract structured data from raw text (e.g. pasted or from an uploaded file)."""
    logger.info(
        "User %s extracting from text (%d chars), %d columns",
        user.sub,
        len(body.text),
        len(body.columns),
    )

    extractor = ExtractionService.instance()
    try:
        rows = await extractor.extract(
            texts=[body.text],
            columns=body.columns,
        )
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    return ExtractionResponse(
        columns=body.columns,
        rows=rows,
        source="text",
        note_count=1,
    )
