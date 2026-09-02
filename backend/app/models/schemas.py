"""Pydantic models (request / response schemas)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# Auth
# ═══════════════════════════════════════════════════════════════════════════════

class UserClaims(BaseModel):
    sub: str
    name: str
    email: str
    roles: list[str] = Field(default_factory=lambda: ["ReadOnly"])


# ═══════════════════════════════════════════════════════════════════════════════
# Column / Schema definitions
# ═══════════════════════════════════════════════════════════════════════════════

class ColumnDataType(StrEnum):
    TEXT = "text"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    TEXT_ARRAY = "text[]"


class ColumnDefinition(BaseModel):
    """A single output column the user wants extracted."""
    name: str = Field(..., min_length=1, max_length=100, examples=["Diagnosis"])
    data_type: ColumnDataType = ColumnDataType.TEXT
    description: str = Field(
        default="",
        max_length=500,
        examples=["Primary diagnosis mentioned in the note"],
    )
    required: bool = False


# ═══════════════════════════════════════════════════════════════════════════════
# Notes
# ═══════════════════════════════════════════════════════════════════════════════

class NotePreview(BaseModel):
    id: str
    patient_id: str | None = None
    date: str | None = None
    author: str | None = None
    note_type: str | None = None
    text_preview: str = Field(default="", max_length=500)
    char_count: int = 0


class NoteFilterOptions(BaseModel):
    """The values a user can actually filter by in this data source.

    Read from the data rather than hard-coded: what counts as a note type is
    whatever the customer's system puts in that column.
    """

    note_types: list[str] = Field(default_factory=list)
    authors: list[str] = Field(default_factory=list)
    has_note_type: bool = False


class NoteListResponse(BaseModel):
    items: list[NotePreview]
    total: int
    page: int
    page_size: int


# ═══════════════════════════════════════════════════════════════════════════════
# Data sources — the customer's clinical notes databases
# ═══════════════════════════════════════════════════════════════════════════════

# Identifiers are interpolated into SQLAlchemy Table/Column definitions. Those
# quote correctly, but validating the shape first keeps anything exotic out of
# the schema entirely rather than relying on the quoting alone.
IDENTIFIER_RE = r"^[A-Za-z_][A-Za-z0-9_$]{0,62}(\.[A-Za-z_][A-Za-z0-9_$]{0,62})?$"

# Same shape, but empty is also allowed. Written out rather than composed from
# the one above: pydantic v2 matches with search semantics, so an alternation
# built by stripping the leading "^" would leave the identifier branch
# unanchored and accept anything ending in something identifier-shaped.
OPTIONAL_IDENTIFIER_RE = (
    r"^(?:[A-Za-z_][A-Za-z0-9_$]{0,62}(?:\.[A-Za-z_][A-Za-z0-9_$]{0,62})?)?$"
)


class DbEngine(StrEnum):
    POSTGRESQL = "postgresql"
    MSSQL = "mssql"
    SQLITE = "sqlite"


class ColumnMapping(BaseModel):
    """Which column in the customer's table means what to us."""

    id: str = Field(default="id", pattern=IDENTIFIER_RE)
    patient_id: str = Field(default="patient_id", pattern=IDENTIFIER_RE)
    date: str = Field(default="note_date", pattern=IDENTIFIER_RE)
    author: str = Field(default="author", pattern=IDENTIFIER_RE)
    note_text: str = Field(default="note_text", pattern=IDENTIFIER_RE)
    # Optional: the column holding the kind of note (nursing, outpatient,
    # inpatient, a specialty). Empty when the source has no such column, in
    # which case the type filter is simply not offered.
    note_type: str = Field(default="", pattern=OPTIONAL_IDENTIFIER_RE)


class DataSourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=1000)
    engine: DbEngine = DbEngine.POSTGRESQL
    host: str = Field(default="", max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    database_name: str = Field(default="", max_length=255)
    username: str = Field(default="", max_length=255)
    table_name: str = Field(..., pattern=IDENTIFIER_RE)
    columns: ColumnMapping = Field(default_factory=ColumnMapping)


class DataSourceCreate(DataSourceBase):
    # Write-only. Never echoed back by any response model.
    password: str = Field(default="", max_length=512)


class DataSourceUpdate(BaseModel):
    """All fields optional — omit `password` to keep the stored one."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    host: str | None = Field(default=None, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    database_name: str | None = Field(default=None, max_length=255)
    username: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, max_length=512)
    table_name: str | None = Field(default=None, pattern=IDENTIFIER_RE)
    columns: ColumnMapping | None = None


class DataSourceOut(DataSourceBase):
    """A data source as returned to clients.

    Carries no password and no assembled connection string — a browser has no
    use for either, and the surest way not to leak a credential is never to put
    it in a response model.
    """

    id: str
    is_default: bool = False
    has_password: bool = False


class DataSourceTestResult(BaseModel):
    """Outcome of a connection test, shown during setup."""

    ok: bool
    message: str
    note_count: int | None = None
    sample: list[NotePreview] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# Extraction
# ═══════════════════════════════════════════════════════════════════════════════

class ExtractionRequest(BaseModel):
    """Request to extract structured data from database notes."""

    # Which configured data source to read the notes from. Omitted means the
    # default one, which is all a single-source deployment ever needs.
    source_id: str | None = None
    note_ids: list[str] = Field(..., min_length=1, max_length=100)
    columns: list[ColumnDefinition] = Field(..., min_length=1, max_length=50)


class FileExtractionRequest(BaseModel):
    """Request to extract structured data from free text."""
    text: str = Field(..., min_length=1, max_length=500_000)
    columns: list[ColumnDefinition] = Field(..., min_length=1, max_length=50)
    # Where the text came from — an uploaded filename, typically. Recorded
    # against every row so a result can always be traced back to its source.
    source_name: str = Field(default="Pasted text", max_length=255)


class ExtractionResponse(BaseModel):
    """Extraction results.

    ``columns`` leads with provenance columns (see ``provenance_columns``)
    followed by the user's requested schema. Provenance travels *inside* each
    row rather than alongside it, so the link between a row and the note it
    came from survives sorting, editing and export to CSV.

    This matters because one note can yield several rows: a row's position in
    the list says nothing about which note produced it.
    """
    columns: list[ColumnDefinition]
    rows: list[dict[str, Any]]
    source: str
    note_count: int
    # Names of the leading columns that carry provenance rather than extracted
    # data. The UI renders these read-only — they are a record of where the
    # data came from, not a value a reviewer should be able to correct.
    provenance_columns: list[str] = Field(default_factory=list)
    # The run this result was recorded as. Every extraction is persisted as a
    # draft before it is returned, so nothing depends on the browser keeping it.
    run_id: str = ""


class RunStatus(StrEnum):
    """Where a run sits between "the model answered" and "a clinician signed"."""

    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class RowStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RunRow(BaseModel):
    """One extracted row as a reviewer sees it."""

    id: str
    row_index: int
    note_id: str
    patient_id: str
    data: dict[str, Any]
    # The model's untouched answer. The UI shows it behind any value a person
    # changed, so a correction can always be inspected or undone.
    ai_data: dict[str, Any]
    # Columns where data differs from ai_data — a human correction.
    corrected_columns: list[str] = Field(default_factory=list)
    status: RowStatus = RowStatus.PENDING
    review_note: str = ""
    edited_by: str = ""
    edited_at: str | None = None
    decided_by: str = ""
    decided_at: str | None = None


class RunSummary(BaseModel):
    """A run in a list: enough to choose one, not enough to review it."""

    id: str
    created_at: str
    created_by: str
    source_kind: str
    source_label: str
    note_count: int
    row_count: int
    status: RunStatus
    models_used: str = ""
    approved_by: str = ""
    approved_at: str | None = None
    pending_rows: int = 0
    approved_rows: int = 0
    rejected_rows: int = 0
    corrected_rows: int = 0


class RunDetail(RunSummary):
    """A run with everything needed to review it."""

    columns: list[ColumnDefinition]
    provenance_columns: list[str] = Field(default_factory=list)
    rows: list[RunRow]
    sign_off_note: str = ""


class RunListResponse(BaseModel):
    items: list[RunSummary]
    total: int
    page: int
    page_size: int


class RunStats(BaseModel):
    """Outstanding review work, for the dashboard and the navigation badge."""

    total: int = 0
    draft: int = 0
    in_review: int = 0
    approved: int = 0
    rejected: int = 0
    awaiting_review: int = 0
    pending_rows: int = 0


class RowEditRequest(BaseModel):
    """Correct one or more values on a row.

    Partial by design: a reviewer fixes the field that is wrong, and sending
    the whole row back would make an unrelated stale value overwrite someone
    else's correction.
    """

    values: dict[str, Any] = Field(..., min_length=1)


class RowRevertRequest(BaseModel):
    """Put the model's original answer back. Omit the column to revert them all."""

    column: str | None = None


class RowDecisionRequest(BaseModel):
    """Approve, reject, or reopen a single row."""

    status: RowStatus
    note: str = Field(default="", max_length=1000)


class RunApprovalRequest(BaseModel):
    """Sign off a run.

    ``approve_pending`` is the batch case — "the rest are fine" — and it is
    recorded as exactly that, because a sign-off that claims each row was read
    individually when it was not is worse than no sign-off at all.
    """

    approve_pending: bool = True
    note: str = Field(default="", max_length=1000)


class ModelStatus(BaseModel):
    """One model in the extraction chain, and whether it can be used now.

    Free-tier quotas are spent per model per day, so "which model is actually
    answering right now" is operational information — without it, a fallback
    silently taking over looks identical to nothing having happened.
    """

    provider: str
    model: str
    is_primary: bool
    available: bool
    # Seconds until it can be tried again; null when it is available.
    available_in_seconds: float | None = None
    # Why it is being held back: "daily quota exhausted", "per-minute rate
    # limit", "rejected (404)" — the distinction that decides whether to wait
    # a minute or to change the configuration.
    reason: str | None = None
    blocked_since: str | None = None


# ═══════════════════════════════════════════════════════════════════════════════
# Upload
# ═══════════════════════════════════════════════════════════════════════════════

class UploadResponse(BaseModel):
    filename: str
    size_bytes: int
    extracted_text: str
    char_count: int


# Export takes no request body any more: a file is produced from a stored run,
# so what leaves is what was reviewed rather than what a client posted back.
