"""Extraction endpoints — run AI extraction on notes or uploaded text."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import Role, require_role
from app.dependencies import DbSession, SettingsDep, build_repository
from app.models.schemas import (
    ColumnDataType,
    ColumnDefinition,
    ExtractionRequest,
    ExtractionResponse,
    FileExtractionRequest,
    ModelStatus,
    UserClaims,
)
from app.services import run_service
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


@router.get("/models", response_model=list[ModelStatus])
async def model_chain(
    user: UserClaims = Depends(require_role(Role.ADMIN, Role.CLINICIAN)),
):
    """The AI models extraction will try, in order, and which are usable now.

    When a free-tier model hits its daily quota the extractor moves to the next
    one on its own; this is how anyone can see that it happened, and when the
    exhausted model is expected back.
    """
    return ExtractionService.instance().model_status()


@router.post("/from-database", response_model=ExtractionResponse)
async def extract_from_database(
    body: ExtractionRequest,
    session: DbSession,
    settings: SettingsDep,
    user: UserClaims = Depends(require_role(Role.ADMIN, Role.CLINICIAN)),
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

    repo = await build_repository(session, settings, body.source_id)
    notes = await repo.get_notes_for_extraction(body.note_ids)

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
    models_used: set[str] = set()
    try:
        rows = await extractor.extract(
            texts=[n.note_text for n in notes],
            columns=body.columns,
            provenance=provenance,
            models_used=models_used,
        )
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    columns = [
        _provenance_column(note_col, "Identifier of the source note this row came from"),
        _provenance_column(patient_col, "Patient identifier on the source note"),
        *body.columns,
    ]

    # Persisted before it is returned. The result is a draft either way, but a
    # draft that only exists in a browser tab is one refresh from gone — and
    # with it every correction anyone had started making.
    run = await run_service.create_run(
        session,
        user,
        source_kind="database",
        source_id=repo.source.id,
        source_label=repo.source.name,
        columns=columns,
        provenance_columns=[note_col, patient_col],
        rows=rows,
        note_count=len(notes),
        models_used=models_used,
        note_key=note_col,
        patient_key=patient_col,
    )

    return ExtractionResponse(
        columns=columns,
        rows=rows,
        source="database",
        note_count=len(notes),
        provenance_columns=[note_col, patient_col],
        run_id=run.id,
    )


@router.post("/from-text", response_model=ExtractionResponse)
async def extract_from_text(
    body: FileExtractionRequest,
    session: DbSession,
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
    models_used: set[str] = set()
    try:
        rows = await extractor.extract(
            texts=[body.text],
            columns=body.columns,
            provenance=[{document_col: body.source_name}],
            models_used=models_used,
        )
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    columns = [
        _provenance_column(document_col, "Document this row was extracted from"),
        *body.columns,
    ]

    # Recorded as source_kind="upload", and that distinction is load-bearing:
    # a row from here points at a file on someone's machine, not at a note in a
    # system anyone can read back. The review UI says so, because provenance
    # that cannot be re-checked should not be presented as if it could.
    run = await run_service.create_run(
        session,
        user,
        source_kind="upload",
        source_id="",
        source_label=body.source_name,
        columns=columns,
        provenance_columns=[document_col],
        rows=rows,
        note_count=1,
        models_used=models_used,
        note_key=document_col,
    )

    return ExtractionResponse(
        columns=columns,
        rows=rows,
        source="text",
        note_count=1,
        provenance_columns=[document_col],
        run_id=run.id,
    )
