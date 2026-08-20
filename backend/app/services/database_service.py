"""Database service — read-only access to the source medical notes database."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings
from app.models.schemas import NotePreview

logger = logging.getLogger("mediextract.services.database")

# Module-level session factory (initialised lazily)
async_session_factory: async_sessionmaker[AsyncSession] | None = None


def _init_engine(database_url: str) -> async_sessionmaker[AsyncSession]:
    """Create an async engine + session factory from the connection string."""
    global async_session_factory

    # Convert sync URL to async if needed
    url = database_url
    if url.startswith("mssql+pyodbc://"):
        url = url.replace("mssql+pyodbc://", "mssql+aioodbc://", 1)

    engine = create_async_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=False,
    )
    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return async_session_factory


class DatabaseService:
    """Read-only access to the medical notes SQL database."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        global async_session_factory
        if async_session_factory is None and settings.database_url:
            _init_engine(settings.database_url)

    async def _session(self) -> AsyncSession:
        if async_session_factory is None:
            raise RuntimeError("Database not configured — set DATABASE_URL")
        return async_session_factory()

    async def list_notes(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> tuple[list[NotePreview], int]:
        """Return paginated note previews from the source database.

        NOTE: Adjust the SQL below to match your actual table schema.
        The default assumes a table `medical_notes` with columns:
          id, patient_id, note_date, author, note_text
        """
        async with await self._session() as session:
            # Count
            count_sql = "SELECT COUNT(*) FROM medical_notes"
            params: dict[str, Any] = {}

            if search:
                count_sql += " WHERE note_text LIKE :search"
                params["search"] = f"%{search}%"

            result = await session.execute(text(count_sql), params)
            total = result.scalar_one()

            # Fetch page
            query_sql = (
                "SELECT id, patient_id, note_date, author, "
                "LEFT(note_text, 500) AS text_preview, LEN(note_text) AS char_count "
                "FROM medical_notes"
            )
            if search:
                query_sql += " WHERE note_text LIKE :search"

            query_sql += " ORDER BY note_date DESC OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY"
            params["offset"] = (page - 1) * page_size
            params["limit"] = page_size

            result = await session.execute(text(query_sql), params)
            rows = result.mappings().all()

            notes = [
                NotePreview(
                    id=str(row["id"]),
                    patient_id=str(row.get("patient_id", "")),
                    date=str(row.get("note_date", "")),
                    author=str(row.get("author", "")),
                    text_preview=str(row.get("text_preview", "")),
                    char_count=int(row.get("char_count", 0)),
                )
                for row in rows
            ]

        return notes, total

    async def get_note(self, note_id: str) -> NotePreview:
        """Retrieve a single note by ID."""
        async with await self._session() as session:
            result = await session.execute(
                text(
                    "SELECT id, patient_id, note_date, author, "
                    "LEFT(note_text, 500) AS text_preview, LEN(note_text) AS char_count "
                    "FROM medical_notes WHERE id = :id"
                ),
                {"id": note_id},
            )
            row = result.mappings().first()
            if row is None:
                from fastapi import HTTPException, status
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found")

            return NotePreview(
                id=str(row["id"]),
                patient_id=str(row.get("patient_id", "")),
                date=str(row.get("note_date", "")),
                author=str(row.get("author", "")),
                text_preview=str(row.get("text_preview", "")),
                char_count=int(row.get("char_count", 0)),
            )

    async def get_notes_text(self, note_ids: list[str]) -> list[str]:
        """Retrieve full note text for the given IDs."""
        async with await self._session() as session:
            # Use parameterised IN clause
            placeholders = ", ".join(f":id_{i}" for i in range(len(note_ids)))
            params = {f"id_{i}": nid for i, nid in enumerate(note_ids)}

            result = await session.execute(
                text(f"SELECT note_text FROM medical_notes WHERE id IN ({placeholders})"),
                params,
            )
            rows = result.scalars().all()
            return [str(r) for r in rows]
