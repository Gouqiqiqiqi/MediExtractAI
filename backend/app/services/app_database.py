"""The application's own database — audit log, jobs, saved schemas, data sources.

Deliberately separate from the source notes database (see database_service).
This one we own and write to; that one belongs to the customer and we only ever
read from it. Sharing a connection between the two would put our audit trail
inside their estate, which is exactly what a governance review would object to.
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings
from app.models.database import Base

logger = logging.getLogger("mediextract.services.app_database")

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(settings: Settings) -> None:
    """Create the engine and session factory. Idempotent."""
    global _engine, _session_factory
    if _session_factory is not None:
        return

    url = settings.database_url
    kwargs: dict = {"echo": False}
    if not url.startswith("sqlite"):
        kwargs |= {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 10}

    _engine = create_async_engine(url, **kwargs)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    logger.info("Application database initialised (dialect=%s)", _engine.dialect.name)


def _is_already_exists(exc: Exception) -> bool:
    """Whether a DDL error means another process got there first."""
    message = str(exc).lower()
    return "already exists" in message or "duplicate column" in message


async def create_tables() -> None:
    """Create any application tables that do not exist yet.

    Every uvicorn worker runs startup, and ``create_all`` is check-then-act:
    two workers can both see a table missing and both issue CREATE TABLE. The
    loser's error means the table now exists, which is what we wanted, so it is
    retried once — by then the winner has finished and ``checkfirst`` skips
    what it made.

    Running schema setup from each worker at all is a compromise: a dedicated
    pre-start step would avoid the race entirely, but it would also mean the
    documented native dev path (``uvicorn --reload``) silently started against
    an empty database. One tolerant code path is worth more here than a second
    path that only production takes.
    """
    if _engine is None:
        raise RuntimeError("Application database not initialised")

    for attempt in (1, 2):
        try:
            async with _engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            break
        except SQLAlchemyError as exc:
            if attempt == 1 and _is_already_exists(exc):
                logger.debug("Tables being created by another worker; retrying")
                await asyncio.sleep(0.5)
                continue
            if _is_already_exists(exc):
                logger.debug("Tables already created by another worker")
                break
            raise

    logger.info("Application tables ensured: %s", ", ".join(Base.metadata.tables))


async def ensure_columns() -> None:
    """Add columns introduced after a deployment's tables were created.

    We own this database, and ``create_all`` only creates tables that are
    missing entirely — it will not add a column to a table that already exists.
    Without this, upgrading a running deployment would mean telling the operator
    to delete their data source registry, which is not an acceptable upgrade
    path for something holding encrypted credentials.

    Runs under every uvicorn worker at once, so it has to be idempotent against
    *concurrent* execution and not merely re-runnable: two workers will both see
    a column missing and both try to add it. Each statement therefore gets its
    own transaction — a failure inside a shared one would abort the rest on
    PostgreSQL — and an "already exists" race is treated as success, because
    the other worker achieved exactly what this one wanted.

    Deliberately narrow: additive columns only, matched against the models.
    Anything structural belongs in a real migration.
    """
    if _engine is None:
        raise RuntimeError("Application database not initialised")

    def _missing(conn) -> list[tuple[str, str, str, str | None]]:  # noqa: ANN001
        from sqlalchemy import inspect as sa_inspect

        inspector = sa_inspect(conn)
        pending: list[tuple[str, str, str, str | None]] = []
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue
            existing = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing:
                    continue
                default = column.default.arg if column.default is not None else None
                pending.append(
                    (
                        table.name,
                        column.name,
                        column.type.compile(conn.dialect),
                        default if isinstance(default, str) else None,
                    )
                )
        return pending

    async with _engine.connect() as conn:
        pending = await conn.run_sync(_missing)

    added: list[str] = []
    for table_name, column_name, ddl_type, default in pending:
        clause = f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {ddl_type}'
        if default is not None:
            clause += f" DEFAULT '{default}'"
        try:
            async with _engine.begin() as conn:
                await conn.exec_driver_sql(clause)
            added.append(f"{table_name}.{column_name}")
        except SQLAlchemyError as exc:
            if _is_already_exists(exc):
                logger.debug(
                    "%s.%s added by another worker", table_name, column_name
                )
                continue
            raise

    if added:
        logger.info("Added missing columns: %s", ", ".join(added))


def session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Application database not initialised")
    return _session_factory


async def dispose() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
