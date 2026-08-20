"""FastAPI dependency injection factories."""

from __future__ import annotations

from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.security import get_current_user
from app.models.schemas import UserClaims
from app.services.database_service import DatabaseService


# ── Settings ──
SettingsDep = Annotated[Settings, Depends(get_settings)]


# ── Auth ──
CurrentUser = Annotated[UserClaims, Depends(get_current_user)]


# ── Database session ──
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional DB session, rolled back on error."""
    from app.services.database_service import async_session_factory

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DbSession = Annotated[AsyncSession, Depends(get_db_session)]


# ── Services ──
def get_database_service(
    settings: SettingsDep,
) -> DatabaseService:
    return DatabaseService(settings)
