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


# ═══════════════════════════════════════════════════════════════════════════════
# Upload
# ═══════════════════════════════════════════════════════════════════════════════

class UploadResponse(BaseModel):
    filename: str
    size_bytes: int
    extracted_text: str
    char_count: int


# ═══════════════════════════════════════════════════════════════════════════════
# Export
# ═══════════════════════════════════════════════════════════════════════════════

class ExportRequest(BaseModel):
    columns: list[ColumnDefinition]
    rows: list[dict[str, Any]]
