"""FastAPI dependency injection factories."""

from __future__ import annotations

from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.security import get_current_user
from app.models.schemas import UserClaims
from app.services import app_database, data_source_service
from app.services.database_service import DataSourceError, NotesRepository

# ── Settings ──
SettingsDep = Annotated[Settings, Depends(get_settings)]


# ── Auth ──
CurrentUser = Annotated[UserClaims, Depends(get_current_user)]


# ── Application database session ──
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session against the *application's own* database.

    Not the notes database: the audit log and data source registry are ours,
    and the customer's system is read-only to us.
    """
    async with app_database.session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DbSession = Annotated[AsyncSession, Depends(get_db_session)]


# ── Notes repository for the selected data source ──
async def build_repository(
    session: AsyncSession,
    settings: Settings,
    source_id: str | None,
) -> NotesRepository:
    """Resolve the requested (or default) data source into a repository.

    A plain function as well as a dependency: the extraction endpoint takes its
    source_id from the request body, where a Depends-injected query parameter
    cannot reach it.
    """
    ds = await data_source_service.resolve_source(session, source_id)
    if ds is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No data source configured. An administrator must add one first.",
        )
    try:
        config = data_source_service.to_config(ds, settings)
    except DataSourceError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return NotesRepository(config)


async def get_notes_repository(
    session: DbSession,
    settings: SettingsDep,
    # Depending on the authenticated user rather than trusting the endpoint's
    # own role check to run first. FastAPI resolves a sub-dependency before the
    # dependency that needs it, so this is what puts authentication ahead of
    # the data source lookup — without it an anonymous request was answered
    # with 404 "no data source configured", which is both the wrong status and
    # a sliver of deployment state given away before anyone logged in.
    user: CurrentUser,
    source_id: Annotated[str | None, Query(description="Data source to read from")] = None,
) -> NotesRepository:
    return await build_repository(session, settings, source_id)


NotesRepo = Annotated[NotesRepository, Depends(get_notes_repository)]
