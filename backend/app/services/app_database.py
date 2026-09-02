"""The application's own database — audit log, jobs, saved schemas, data sources.

Deliberately separate from the source notes database (see database_service).
This one we own and write to; that one belongs to the customer and we only ever
read from it. Sharing a connection between the two would put our audit trail
inside their estate, which is exactly what a governance review would object to.
"""

from __future__ import annotations

import logging

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


async def create_tables() -> None:
    """Create any application tables that do not exist yet."""
    if _engine is None:
        raise RuntimeError("Application database not initialised")
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Application tables ensured: %s", ", ".join(Base.metadata.tables))


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
