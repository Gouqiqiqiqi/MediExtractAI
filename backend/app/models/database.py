"""SQLAlchemy ORM models for the application's own database (not the source notes DB)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
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
