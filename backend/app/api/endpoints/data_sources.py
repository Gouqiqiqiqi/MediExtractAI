"""Data source endpoints — register and map the customer's notes databases.

Administrator territory. A clinician picks a data source by name and never sees
a host or a credential; configuring one is a deployment activity done once,
by someone who has been given the connection details.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.crypto import SecretDecryptionError
from app.core.security import Role, require_role
from app.dependencies import DbSession, SettingsDep
from app.models.schemas import (
    DataSourceCreate,
    DataSourceOut,
    DataSourceTestResult,
    DataSourceUpdate,
    UserClaims,
)
from app.services import data_source_service
from app.services.database_service import DataSourceError, NotesRepository

router = APIRouter()
logger = logging.getLogger("mediextract.api.data_sources")


@router.get("/", response_model=list[DataSourceOut])
async def list_data_sources(
    session: DbSession,
    # Any signed-in role may *list* sources — a clinician has to choose one.
    # Only administrators can see or change the connection details below.
    user: UserClaims = Depends(
        require_role(Role.ADMIN, Role.CLINICIAN, Role.READONLY)
    ),
):
    """List the configured data sources."""
    sources = await data_source_service.list_sources(session)
    return [data_source_service.to_out(ds) for ds in sources]


@router.post("/", response_model=DataSourceOut, status_code=status.HTTP_201_CREATED)
async def create_data_source(
    payload: DataSourceCreate,
    session: DbSession,
    settings: SettingsDep,
    user: UserClaims = Depends(require_role(Role.ADMIN)),
):
    """Register a new customer database."""
    try:
        ds = await data_source_service.create_source(
            session, payload, settings, created_by=user.sub
        )
    except DataSourceError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    logger.info("User %s created data source %s", user.sub, ds.name)
    return data_source_service.to_out(ds)


@router.patch("/{source_id}", response_model=DataSourceOut)
async def update_data_source(
    source_id: str,
    payload: DataSourceUpdate,
    session: DbSession,
    settings: SettingsDep,
    user: UserClaims = Depends(require_role(Role.ADMIN)),
):
    """Update a data source. Omit `password` to keep the stored one."""
    ds = await data_source_service.get_source(session, source_id)
    if ds is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Data source not found")
    try:
        ds = await data_source_service.update_source(session, ds, payload, settings)
    except DataSourceError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    logger.info("User %s updated data source %s", user.sub, ds.name)
    return data_source_service.to_out(ds)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_data_source(
    source_id: str,
    session: DbSession,
    user: UserClaims = Depends(require_role(Role.ADMIN)),
):
    """Remove a data source. The customer's database is untouched."""
    ds = await data_source_service.get_source(session, source_id)
    if ds is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Data source not found")
    await data_source_service.delete_source(session, ds)
    logger.info("User %s deleted data source %s", user.sub, source_id)


@router.post("/{source_id}/test", response_model=DataSourceTestResult)
async def test_data_source(
    source_id: str,
    session: DbSession,
    settings: SettingsDep,
    user: UserClaims = Depends(require_role(Role.ADMIN)),
):
    """Connect, count the notes, and return a few rows.

    The sample is the point. A row count would pass even if the column picked
    as "note text" actually held a department code — seeing three real notes is
    what tells you the mapping is right.
    """
    ds = await data_source_service.get_source(session, source_id)
    if ds is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Data source not found")

    try:
        config = data_source_service.to_config(ds, settings)
        repo = NotesRepository(config)
        total, sample = await repo.test()
    except (DataSourceError, SecretDecryptionError) as exc:
        return DataSourceTestResult(ok=False, message=str(exc))
    except Exception as exc:  # noqa: BLE001 — surface the driver's own message
        logger.warning("Data source test failed for %s: %s", ds.name, exc)
        return DataSourceTestResult(ok=False, message=f"{type(exc).__name__}: {exc}")

    return DataSourceTestResult(
        ok=True,
        message=f"Connected to {ds.database_name or ds.host} — read {ds.table_name}",
        note_count=total,
        sample=sample,
    )
