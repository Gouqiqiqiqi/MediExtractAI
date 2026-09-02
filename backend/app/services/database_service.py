"""Database service — read-only access to the source medical notes database.

Dialect portability
-------------------
The notes database belongs to the customer, so we cannot assume which engine it
runs on: a hospital SQL Server, a warehouse Postgres, a SQLite extract handed
over for a pilot. Every query here is therefore built with SQLAlchemy Core
rather than raw SQL, so the same code compiles to whatever dialect the
connection string points at.

Two rules keep it that way:
  * Pagination goes through ``.limit()/.offset()`` — SQLAlchemy emits
    ``LIMIT/OFFSET`` or ``OFFSET ... ROWS FETCH NEXT ... ROWS ONLY`` as required.
  * String truncation and length are done in Python, not in SQL. ``LEFT()`` and
    ``LEN()`` are T-SQL only; ``SUBSTR()``/``LENGTH()`` are not universal
    either. A page is 20 rows, so pulling the full text and slicing it here
    costs nothing and removes a whole class of dialect bugs.
"""

from __future__ import annotations

import logging
from typing import NamedTuple

from sqlalchemy import (
    Column,
    Date,
    MetaData,
    String,
    Table,
    Text,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings
from app.models.schemas import NotePreview

logger = logging.getLogger("mediextract.services.database")

# Length of the preview snippet shown in the notes browser.
PREVIEW_CHARS = 500

# ── Source table ────────────────────────────────────────────────────────────
# Reflects the customer's existing table; we never create or write to it.
# Point this at whatever the customer actually calls it — the column names are
# the only thing the rest of the app depends on.
metadata = MetaData()

medical_notes = Table(
    "medical_notes",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("patient_id", String(64)),
    Column("note_date", Date),
    Column("author", String(255)),
    Column("specialty", String(128)),
    Column("note_text", Text),
)


class NoteSource(NamedTuple):
    """A note plus the identifiers that let a result be traced back to it."""

    note_id: str
    patient_id: str
    note_text: str


# Module-level session factory (initialised lazily)
async_session_factory: async_sessionmaker[AsyncSession] | None = None


def _normalise_async_url(url: str) -> str:
    """Upgrade a sync driver URL to its async counterpart.

    Lets an operator paste the connection string their DBA gave them without
    having to know which async driver we use.
    """
    prefixes = {
        "mssql+pyodbc://": "mssql+aioodbc://",
        "postgresql://": "postgresql+asyncpg://",
        "postgres://": "postgresql+asyncpg://",
        "postgresql+psycopg2://": "postgresql+asyncpg://",
        "sqlite://": "sqlite+aiosqlite://",
    }
    for sync_prefix, async_prefix in prefixes.items():
        if url.startswith(sync_prefix):
            return url.replace(sync_prefix, async_prefix, 1)
    return url


def _init_engine(database_url: str) -> async_sessionmaker[AsyncSession]:
    """Create an async engine + session factory from the connection string."""
    global async_session_factory

    url = _normalise_async_url(database_url)

    # SQLite ignores pool sizing; passing it anyway raises on some driver
    # versions, so only send pool options to real server engines.
    kwargs: dict = {"pool_pre_ping": True, "echo": False}
    if not url.startswith("sqlite"):
        kwargs |= {"pool_size": 5, "max_overflow": 10}

    engine = create_async_engine(url, **kwargs)
    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    logger.info("Notes database engine initialised (dialect=%s)", engine.dialect.name)
    return async_session_factory


def _to_preview(row) -> NotePreview:  # noqa: ANN001 — SQLAlchemy Row
    """Build a NotePreview, truncating the note text in Python."""
    full_text = row.note_text or ""
    return NotePreview(
        id=str(row.id),
        patient_id=str(row.patient_id or ""),
        date=str(row.note_date or ""),
        author=str(row.author or ""),
        text_preview=full_text[:PREVIEW_CHARS],
        char_count=len(full_text),
    )


class DatabaseService:
    """Read-only access to the medical notes SQL database."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        global async_session_factory
        if async_session_factory is None and settings.notes_db_url:
            _init_engine(settings.notes_db_url)

    async def _session(self) -> AsyncSession:
        if async_session_factory is None:
            raise RuntimeError(
                "Notes database not configured — set NOTES_DATABASE_URL"
            )
        return async_session_factory()

    async def list_notes(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> tuple[list[NotePreview], int]:
        """Return paginated note previews from the source database."""
        async with await self._session() as session:
            count_stmt = select(func.count()).select_from(medical_notes)
            page_stmt = select(
                medical_notes.c.id,
                medical_notes.c.patient_id,
                medical_notes.c.note_date,
                medical_notes.c.author,
                medical_notes.c.note_text,
            )

            if search:
                # ilike compiles to LOWER(x) LIKE LOWER(y) on engines without a
                # native case-insensitive operator, so it works everywhere.
                pattern = f"%{search}%"
                condition = medical_notes.c.note_text.ilike(pattern)
                count_stmt = count_stmt.where(condition)
                page_stmt = page_stmt.where(condition)

            total = (await session.execute(count_stmt)).scalar_one()

            page_stmt = (
                page_stmt.order_by(medical_notes.c.note_date.desc())
                .limit(page_size)
                .offset((page - 1) * page_size)
            )
            rows = (await session.execute(page_stmt)).all()

        return [_to_preview(r) for r in rows], total

    async def get_note(self, note_id: str) -> NotePreview:
        """Retrieve a single note by ID."""
        async with await self._session() as session:
            stmt = select(
                medical_notes.c.id,
                medical_notes.c.patient_id,
                medical_notes.c.note_date,
                medical_notes.c.author,
                medical_notes.c.note_text,
            ).where(medical_notes.c.id == note_id)
            row = (await session.execute(stmt)).first()

        if row is None:
            from fastapi import HTTPException, status

            raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found")

        return _to_preview(row)

    async def get_notes_for_extraction(
        self, note_ids: list[str]
    ) -> list[NoteSource]:
        """Fetch full note text plus the identifiers needed to trace it back.

        Returns records in the same order as ``note_ids``. ``IN`` clauses give
        no ordering guarantee, so the caller must never assume the database
        returns rows in the order it asked for them — the rows are re-ordered
        here against the requested list.

        IDs that do not exist are skipped rather than raising: a note may have
        been deleted between the browser listing it and the user extracting it.
        """
        if not note_ids:
            return []

        async with await self._session() as session:
            stmt = select(
                medical_notes.c.id,
                medical_notes.c.patient_id,
                medical_notes.c.note_text,
            ).where(medical_notes.c.id.in_(note_ids))
            rows = (await session.execute(stmt)).all()

        by_id = {
            str(r.id): NoteSource(
                note_id=str(r.id),
                patient_id=str(r.patient_id or ""),
                note_text=str(r.note_text or ""),
            )
            for r in rows
        }

        missing = [nid for nid in note_ids if nid not in by_id]
        if missing:
            logger.warning(
                "%d requested note(s) not found in source database: %s",
                len(missing),
                ", ".join(missing[:5]),
            )

        return [by_id[nid] for nid in note_ids if nid in by_id]
