"""SQLAlchemy ORM models for the application's own database (not the source notes DB)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
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


class ExtractionJob(Base):
    """Record of each extraction run (metadata only)."""

    __tablename__ = "extraction_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_sub: Mapped[str] = mapped_column(String(255), index=True)
    source: Mapped[str] = mapped_column(String(50))  # "database" | "upload"
    note_count: Mapped[int] = mapped_column(default=0)
    column_count: Mapped[int] = mapped_column(default=0)
    row_count: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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
