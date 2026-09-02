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
    text_preview: str = Field(default="", max_length=500)
    char_count: int = 0


class NoteListResponse(BaseModel):
    items: list[NotePreview]
    total: int
    page: int
    page_size: int


# ═══════════════════════════════════════════════════════════════════════════════
# Extraction
# ═══════════════════════════════════════════════════════════════════════════════

class ExtractionRequest(BaseModel):
    """Request to extract structured data from database notes."""
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
