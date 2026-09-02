"""Read-only access to a customer's clinical notes database.

Nothing about the customer's schema is hard-coded. A DataSource supplies the
connection *and* the mapping — which table holds the notes, and which of its
columns mean id, patient, date, author and note text. Two customers never name
these the same way, and needing a code change per site is the difference
between shipping a product and shipping a bespoke integration each time.

Dialect portability
-------------------
Queries are built with SQLAlchemy Core, never raw SQL, so the same code
compiles for Postgres, SQL Server or a SQLite extract handed over for a pilot.
Two rules keep it that way:

  * Pagination goes through ``.limit()/.offset()``.
  * String truncation and length are done in Python. ``LEFT()``/``LEN()`` are
    T-SQL; ``SUBSTR()``/``LENGTH()`` are not universal either. A page is 20
    rows, so slicing here costs nothing and removes a class of dialect bugs.

Safety
------
Identifiers come from operator input, so they are validated against
``IDENTIFIER_RE`` at the schema layer before they ever reach a Table
definition, and SQLAlchemy quotes them on the way out. In demo mode the set of
hosts that may be connected to is restricted — a publicly reachable demo with
authentication disabled must not double as an open database proxy.
"""

from __future__ import annotations

import logging
import urllib.parse
from dataclasses import dataclass
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
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.config import Settings
from app.models.schemas import NotePreview

logger = logging.getLogger("mediextract.services.database")

# Length of the preview snippet shown in the notes browser.
PREVIEW_CHARS = 500


class NoteSource(NamedTuple):
    """A note plus the identifiers that let a result be traced back to it."""

    note_id: str
    patient_id: str
    note_text: str


class DataSourceError(RuntimeError):
    """Configuration or connectivity problem with a data source."""


@dataclass(frozen=True)
class SourceConfig:
    """Everything needed to read notes from one customer database."""

    id: str
    name: str
    url: str
    table_name: str
    col_id: str
    col_patient_id: str
    col_date: str
    col_author: str
    col_note_text: str

    @property
    def table_key(self) -> tuple:
        return (
            self.url,
            self.table_name,
            self.col_id,
            self.col_patient_id,
            self.col_date,
            self.col_author,
            self.col_note_text,
        )


# ── Connection strings ──────────────────────────────────────────────────────

def build_url(
    engine: str,
    host: str,
    port: int | None,
    database: str,
    username: str,
    password: str,
) -> str:
    """Assemble an async SQLAlchemy URL. Credentials are percent-encoded."""
    if engine == "sqlite":
        # `database` is a filesystem path for SQLite.
        return f"sqlite+aiosqlite:///{database}"

    user = urllib.parse.quote_plus(username or "")
    pwd = urllib.parse.quote_plus(password or "")
    credentials = f"{user}:{pwd}@" if user else ""
    netloc = f"{host}:{port}" if port else host

    if engine == "postgresql":
        return f"postgresql+asyncpg://{credentials}{netloc}/{database}"
    if engine == "mssql":
        return (
            f"mssql+aioodbc://{credentials}{netloc}/{database}"
            "?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"
        )
    raise DataSourceError(f"Unsupported database engine: {engine!r}")


def check_host_allowed(host: str, settings: Settings) -> None:
    """Reject hosts that a demo deployment must not reach.

    With DEMO_MODE on there is no authentication, so an unrestricted connection
    form would let any visitor point the server at any host it can route to —
    an SSRF primitive and a credential-harvesting page in one. The allowlist is
    the price of showing the real flow on a public demo.
    """
    if not settings.demo_mode:
        return
    allowed = settings.demo_allowed_db_host_list
    if host and host.lower() not in allowed:
        raise DataSourceError(
            f"Demo mode only permits connections to: {', '.join(allowed)}. "
            f"Host {host!r} was refused. A real deployment has authentication "
            "and no such restriction."
        )


# ── Engine / table caches ───────────────────────────────────────────────────
# Engines are pooled per connection string; tables per mapping. Both are cheap
# to hold and expensive to rebuild on every request.
_engines: dict[str, AsyncEngine] = {}
_tables: dict[tuple, Table] = {}


def _get_engine(url: str) -> AsyncEngine:
    engine = _engines.get(url)
    if engine is None:
        kwargs: dict = {"echo": False}
        if not url.startswith("sqlite"):
            kwargs |= {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 10}
        engine = create_async_engine(url, **kwargs)
        _engines[url] = engine
        logger.info("Opened engine for %s", url.split("@")[-1])
    return engine


def _get_table(cfg: SourceConfig) -> Table:
    table = _tables.get(cfg.table_key)
    if table is None:
        schema = None
        name = cfg.table_name
        if "." in name:  # e.g. dbo.ClinicalDocument
            schema, name = name.split(".", 1)
        table = Table(
            name,
            MetaData(schema=schema),
            Column(cfg.col_id, String(255), primary_key=True),
            Column(cfg.col_patient_id, String(255)),
            Column(cfg.col_date, Date),
            Column(cfg.col_author, String(255)),
            Column(cfg.col_note_text, Text),
        )
        _tables[cfg.table_key] = table
    return table


async def dispose_engines() -> None:
    for engine in _engines.values():
        await engine.dispose()
    _engines.clear()
    _tables.clear()


# ── Repository ──────────────────────────────────────────────────────────────

class NotesRepository:
    """Read-only queries against one configured notes database."""

    def __init__(self, config: SourceConfig) -> None:
        self._cfg = config
        self._table = _get_table(config)
        self._engine = _get_engine(config.url)

    @property
    def _c(self):
        return self._table.c

    def _preview(self, row) -> NotePreview:  # noqa: ANN001 — SQLAlchemy Row
        cfg = self._cfg
        full_text = getattr(row, cfg.col_note_text, "") or ""
        return NotePreview(
            id=str(getattr(row, cfg.col_id, "")),
            patient_id=str(getattr(row, cfg.col_patient_id, "") or ""),
            date=str(getattr(row, cfg.col_date, "") or ""),
            author=str(getattr(row, cfg.col_author, "") or ""),
            text_preview=full_text[:PREVIEW_CHARS],
            char_count=len(full_text),
        )

    def _preview_select(self):
        c = self._c
        cfg = self._cfg
        return select(
            c[cfg.col_id],
            c[cfg.col_patient_id],
            c[cfg.col_date],
            c[cfg.col_author],
            c[cfg.col_note_text],
        )

    async def list_notes(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> tuple[list[NotePreview], int]:
        """Return paginated note previews."""
        cfg = self._cfg
        count_stmt = select(func.count()).select_from(self._table)
        page_stmt = self._preview_select()

        if search:
            # ilike compiles to LOWER(x) LIKE LOWER(y) where there is no native
            # case-insensitive operator, so it behaves the same everywhere.
            condition = self._c[cfg.col_note_text].ilike(f"%{search}%")
            count_stmt = count_stmt.where(condition)
            page_stmt = page_stmt.where(condition)

        page_stmt = (
            page_stmt.order_by(self._c[cfg.col_date].desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )

        async with self._engine.connect() as conn:
            total = (await conn.execute(count_stmt)).scalar_one()
            rows = (await conn.execute(page_stmt)).all()

        return [self._preview(r) for r in rows], total

    async def get_note(self, note_id: str) -> NotePreview | None:
        stmt = self._preview_select().where(self._c[self._cfg.col_id] == note_id)
        async with self._engine.connect() as conn:
            row = (await conn.execute(stmt)).first()
        return self._preview(row) if row is not None else None

    async def get_notes_for_extraction(
        self, note_ids: list[str]
    ) -> list[NoteSource]:
        """Fetch note text plus the identifiers needed to trace it back.

        Returns records in the order requested. ``IN`` gives no ordering
        guarantee, so the rows are re-ordered here against the requested list
        rather than trusting whatever the database returns.

        Unknown IDs are skipped with a warning rather than raising: a note can
        be deleted between the browser listing it and the user extracting it.
        """
        if not note_ids:
            return []

        cfg = self._cfg
        c = self._c
        stmt = select(
            c[cfg.col_id], c[cfg.col_patient_id], c[cfg.col_note_text]
        ).where(c[cfg.col_id].in_(note_ids))

        async with self._engine.connect() as conn:
            rows = (await conn.execute(stmt)).all()

        by_id = {
            str(getattr(r, cfg.col_id)): NoteSource(
                note_id=str(getattr(r, cfg.col_id)),
                patient_id=str(getattr(r, cfg.col_patient_id, "") or ""),
                note_text=str(getattr(r, cfg.col_note_text, "") or ""),
            )
            for r in rows
        }

        missing = [nid for nid in note_ids if nid not in by_id]
        if missing:
            logger.warning(
                "%d requested note(s) not found in %s: %s",
                len(missing),
                cfg.name,
                ", ".join(missing[:5]),
            )

        return [by_id[nid] for nid in note_ids if nid in by_id]

    async def test(self, sample_size: int = 3) -> tuple[int, list[NotePreview]]:
        """Count rows and read a few, to prove the mapping is right.

        Counting alone would pass against a table whose columns we have
        misnamed; returning rows lets whoever is configuring it *see* that the
        column they picked as "note text" really holds notes.
        """
        count_stmt = select(func.count()).select_from(self._table)
        sample_stmt = self._preview_select().limit(sample_size)
        async with self._engine.connect() as conn:
            total = (await conn.execute(count_stmt)).scalar_one()
            rows = (await conn.execute(sample_stmt)).all()
        return total, [self._preview(r) for r in rows]
