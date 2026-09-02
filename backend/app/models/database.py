"""SQLAlchemy ORM models for the application's own database (not the source notes DB)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AuditLog(Base):
    """Immutable audit trail — who did what and when (never stores patient data)."""

    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_sub: Mapped[str] = mapped_column(String(255), index=True)
    user_email: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource: Mapped[str] = mapped_column(String(255), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class ExtractionRun(Base):
    """One extraction: what was asked for, what came back, and who signed it off.

    A run is an immutable *record* of an attempt, not a mutable table of
    results. Re-running the same notes against the same schema makes a second
    run so the two can be compared — which is the only way to tell whether a
    model change made things better or worse.

    The user's schema lives here as JSON rather than as columns on a table.
    Column names come from free text a clinician typed, and turning those into
    DDL would mean a CREATE TABLE per experiment, quoting user input into
    schema statements, and a migration every time someone adds a field. See
    ``ExtractionRow.data_json``.
    """

    __tablename__ = "extraction_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    created_by_sub: Mapped[str] = mapped_column(String(255), index=True)
    created_by_name: Mapped[str] = mapped_column(String(255), default="")

    # "database" — rows point at notes in a system we can read back.
    # "upload"   — rows came from a file on someone's laptop; the provenance is
    #              a filename and nothing more, which is why the two are not
    #              treated as equivalent downstream.
    source_kind: Mapped[str] = mapped_column(String(20), index=True)
    source_id: Mapped[str] = mapped_column(String(36), default="")
    source_label: Mapped[str] = mapped_column(String(500), default="")

    schema_json: Mapped[str] = mapped_column(Text)  # ColumnDefinition[]
    provenance_columns_json: Mapped[str] = mapped_column(Text, default="[]")
    # Which model(s) actually answered. Recorded because a run reviewed months
    # later is unexplainable without it — the chain rotates on quota.
    models_used: Mapped[str] = mapped_column(String(500), default="")

    note_count: Mapped[int] = mapped_column(default=0)
    row_count: Mapped[int] = mapped_column(default=0)

    # draft → in_review → approved, or rejected. Nothing leaves this system as
    # reviewed data without passing through approved.
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    approved_by_sub: Mapped[str] = mapped_column(String(255), default="")
    approved_by_name: Mapped[str] = mapped_column(String(255), default="")
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sign_off_note: Mapped[str] = mapped_column(Text, default="")


class ExtractionRow(Base):
    """One extracted row, its untouched model output, and its review state.

    ``ai_data_json`` is never written again after the run is created. Keeping
    the model's original answer beside the current value is what makes "this
    field was corrected by a human" a fact rather than an inference — and the
    pairs it produces are the evaluation set for the next prompt.

    ``data_json`` holds the user's own columns, keyed by column name. Stored as
    JSON text so the same code runs on the SQLite demo and on a customer's
    Postgres; on Postgres this should be JSONB with a GIN index, which is what
    makes ``data->>'Diagnosis'`` queryable without a table per schema.
    """

    __tablename__ = "extraction_rows"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("extraction_runs.id"), index=True
    )
    row_index: Mapped[int] = mapped_column(default=0)

    # Lifted out of the JSON because these are what anyone queries by, and
    # because they are the link back to the source system.
    note_id: Mapped[str] = mapped_column(String(255), default="", index=True)
    patient_id: Mapped[str] = mapped_column(String(255), default="", index=True)

    data_json: Mapped[str] = mapped_column(Text)
    ai_data_json: Mapped[str] = mapped_column(Text)

    # pending → approved | rejected. A rejected row is resolved, not deleted:
    # "the model got this one wrong" is a finding worth keeping.
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    review_note: Mapped[str] = mapped_column(Text, default="")

    edited_by_sub: Mapped[str] = mapped_column(String(255), default="")
    edited_by_name: Mapped[str] = mapped_column(String(255), default="")
    edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    decided_by_sub: Mapped[str] = mapped_column(String(255), default="")
    decided_by_name: Mapped[str] = mapped_column(String(255), default="")
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ExtractionRowRevision(Base):
    """Every change a person made to an extracted value.

    Clinical data is corrected, never quietly overwritten: the old value has to
    remain visible to whoever asks what this row said before. One record per
    column changed, so "who changed the follow-up date" is a query rather than
    a diff of two JSON blobs.
    """

    __tablename__ = "extraction_row_revisions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("extraction_runs.id"), index=True
    )
    row_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("extraction_rows.id"), index=True
    )
    column_name: Mapped[str] = mapped_column(String(255))
    old_value_json: Mapped[str] = mapped_column(Text, default="null")
    new_value_json: Mapped[str] = mapped_column(Text, default="null")
    # "edit" — a person typed a new value.
    # "revert" — a person put the model's original answer back.
    kind: Mapped[str] = mapped_column(String(20), default="edit")
    changed_by_sub: Mapped[str] = mapped_column(String(255), index=True)
    changed_by_name: Mapped[str] = mapped_column(String(255), default="")
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class DataSource(Base):
    """A configured connection to a customer's clinical notes database.

    Two halves, and the second is the one that matters in the field:

    * **Connection** — where the database is and how to authenticate. The
      password is stored encrypted and is never returned by the API.
    * **Schema mapping** — which table holds the notes, and which of its columns
      mean "note text", "patient identifier" and so on. No two customers name
      these the same way, so hard-coding them would mean a code change for every
      deployment. This is the difference between shipping a product and shipping
      a bespoke integration each time.
    """

    __tablename__ = "data_sources"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")

    # ── Connection ──
    engine: Mapped[str] = mapped_column(String(32))  # postgresql | mssql | sqlite
    host: Mapped[str] = mapped_column(String(255), default="")
    port: Mapped[int | None] = mapped_column(nullable=True)
    database_name: Mapped[str] = mapped_column(String(255), default="")
    username: Mapped[str] = mapped_column(String(255), default="")
    password_encrypted: Mapped[str] = mapped_column(Text, default="")

    # ── Schema mapping ──
    table_name: Mapped[str] = mapped_column(String(255))
    col_id: Mapped[str] = mapped_column(String(255), default="id")
    col_patient_id: Mapped[str] = mapped_column(String(255), default="patient_id")
    col_date: Mapped[str] = mapped_column(String(255), default="note_date")
    col_author: Mapped[str] = mapped_column(String(255), default="author")
    col_note_text: Mapped[str] = mapped_column(String(255), default="note_text")
    # Optional. Clinical systems keep every kind of note together — nursing,
    # outpatient, inpatient — and the useful first move is to narrow to a type
    # rather than search the lot. Blank means this source has no such column.
    col_note_type: Mapped[str] = mapped_column(String(255), default="")

    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SavedSchema(Base):
    """User-saved column schemas for reuse."""

    __tablename__ = "saved_schemas"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_sub: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(255))
    columns_json: Mapped[str] = mapped_column(Text)  # JSON-serialised ColumnDefinition[]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
