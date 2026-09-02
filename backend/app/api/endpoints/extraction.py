"""Extraction endpoints — run AI extraction on notes or uploaded text."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import Settings, get_settings
from app.core.security import Role, require_role
from app.models.schemas import (
    ColumnDataType,
    ColumnDefinition,
    ExtractionRequest,
    ExtractionResponse,
    FileExtractionRequest,
    UserClaims,
)
from app.services.database_service import DatabaseService
from app.services.extraction_service import ExtractionService

router = APIRouter()
logger = logging.getLogger("mediextract.api.extraction")

# Preferred display names for the provenance columns. They are resolved against
# the user's schema before use — see _resolve_names.
NOTE_COLUMN = "Source Note"
PATIENT_COLUMN = "Patient ID"
DOCUMENT_COLUMN = "Source Document"


def _resolve_names(desired: list[str], taken: set[str]) -> list[str]:
    """Pick provenance column names that do not collide with the user's schema.

    A user is free to define a column called "Patient ID" themselves. If we
    wrote our provenance under the same key we would silently overwrite what
    the model extracted, so we suffix ours instead. Losing extracted data to a
    name clash would be far worse than an unusual column heading.
    """
    resolved: list[str] = []
    used = set(taken)
    for name in desired:
        candidate = name
        suffix = 2
        while candidate in used:
            candidate = f"{name} ({suffix})"
            suffix += 1
        resolved.append(candidate)
        used.add(candidate)
    return resolved


def _provenance_column(name: str, description: str) -> ColumnDefinition:
    return ColumnDefinition(
        name=name,
        data_type=ColumnDataType.TEXT,
        description=description,
        required=False,
    )


@router.post("/from-database", response_model=ExtractionResponse)
async def extract_from_database(
    body: ExtractionRequest,
    user: UserClaims = Depends(require_role(Role.ADMIN, Role.CLINICIAN)),
    settings: Settings = Depends(get_settings),
):
    """Extract structured data from medical notes stored in the SQL database.

    The user supplies note IDs and an output schema (column definitions). Every
    returned row carries the note and patient it came from, because one note can
    produce several rows and the caller cannot otherwise tell them apart.
    """
    logger.info(
        "User %s extracting from %d notes, %d columns",
        user.sub,
        len(body.note_ids),
        len(body.columns),
    )

    db = DatabaseService(settings)
    notes = await db.get_notes_for_extraction(body.note_ids)

    if not notes:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "None of the requested notes were found in the source database",
        )

    note_col, patient_col = _resolve_names(
        [NOTE_COLUMN, PATIENT_COLUMN],
        {c.name for c in body.columns},
    )
    provenance = [
        {note_col: n.note_id, patient_col: n.patient_id} for n in notes
    ]

    extractor = ExtractionService.instance()
    try:
        rows = await extractor.extract(
            texts=[n.note_text for n in notes],
            columns=body.columns,
            provenance=provenance,
        )
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    return ExtractionResponse(
        columns=[
            _provenance_column(
                note_col, "Identifier of the source note this row came from"
            ),
            _provenance_column(
                patient_col, "Patient identifier on the source note"
            ),
            *body.columns,
        ],
        rows=rows,
        source="database",
        note_count=len(notes),
        provenance_columns=[note_col, patient_col],
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

    (document_col,) = _resolve_names(
        [DOCUMENT_COLUMN],
        {c.name for c in body.columns},
    )

    extractor = ExtractionService.instance()
    try:
        rows = await extractor.extract(
            texts=[body.text],
            columns=body.columns,
            provenance=[{document_col: body.source_name}],
        )
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    return ExtractionResponse(
        columns=[
            _provenance_column(
                document_col, "Document this row was extracted from"
            ),
            *body.columns,
        ],
        rows=rows,
        source="text",
        note_count=1,
        provenance_columns=[document_col],
    )
