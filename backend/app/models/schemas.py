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


class ExtractionResponse(BaseModel):
    columns: list[ColumnDefinition]
    rows: list[dict[str, Any]]
    source: str
    note_count: int


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
