"""Managing the customer databases this deployment knows how to read."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.crypto import decrypt_secret, encrypt_secret
from app.models.database import DataSource
from app.models.schemas import (
    ColumnMapping,
    DataSourceCreate,
    DataSourceOut,
    DataSourceUpdate,
)
from app.services.database_service import (
    DataSourceError,
    SourceConfig,
    build_url,
    check_host_allowed,
)

logger = logging.getLogger("mediextract.services.data_source")

BOOTSTRAP_NAME = "Demo clinical notes (Postgres)"


def to_out(ds: DataSource) -> DataSourceOut:
    """Map to the response model. Never carries the password."""
    return DataSourceOut(
        id=ds.id,
        name=ds.name,
        description=ds.description,
        engine=ds.engine,
        host=ds.host,
        port=ds.port,
        database_name=ds.database_name,
        username=ds.username,
        table_name=ds.table_name,
        columns=ColumnMapping(
            id=ds.col_id,
            patient_id=ds.col_patient_id,
            date=ds.col_date,
            author=ds.col_author,
            note_text=ds.col_note_text,
            note_type=ds.col_note_type or "",
        ),
        is_default=ds.is_default,
        has_password=bool(ds.password_encrypted),
    )


def to_config(ds: DataSource, settings: Settings) -> SourceConfig:
    """Build the runtime connection config, decrypting the stored password."""
    password = decrypt_secret(ds.password_encrypted, settings.app_secret_key)
    check_host_allowed(ds.host, settings)
    return SourceConfig(
        id=ds.id,
        name=ds.name,
        url=build_url(
            engine=ds.engine,
            host=ds.host,
            port=ds.port,
            database=ds.database_name,
            username=ds.username,
            password=password,
        ),
        table_name=ds.table_name,
        col_id=ds.col_id,
        col_patient_id=ds.col_patient_id,
        col_date=ds.col_date,
        col_author=ds.col_author,
        col_note_text=ds.col_note_text,
        col_note_type=ds.col_note_type or "",
    )


async def list_sources(session: AsyncSession) -> list[DataSource]:
    result = await session.execute(
        select(DataSource).order_by(DataSource.is_default.desc(), DataSource.name)
    )
    return list(result.scalars().all())


async def get_source(session: AsyncSession, source_id: str) -> DataSource | None:
    return await session.get(DataSource, source_id)


async def resolve_source(
    session: AsyncSession, source_id: str | None
) -> DataSource | None:
    """Return the requested source, or the default when none was named.

    Clinicians work with one configured source most of the time, so the API
    stays usable without a source_id; naming one is how you work across
    several.
    """
    if source_id:
        return await get_source(session, source_id)
    result = await session.execute(
        select(DataSource).order_by(DataSource.is_default.desc(), DataSource.name)
    )
    return result.scalars().first()


async def create_source(
    session: AsyncSession,
    payload: DataSourceCreate,
    settings: Settings,
    created_by: str,
) -> DataSource:
    check_host_allowed(payload.host, settings)
    ds = DataSource(
        name=payload.name,
        description=payload.description,
        engine=payload.engine.value,
        host=payload.host,
        port=payload.port,
        database_name=payload.database_name,
        username=payload.username,
        password_encrypted=encrypt_secret(payload.password, settings.app_secret_key),
        table_name=payload.table_name,
        col_id=payload.columns.id,
        col_patient_id=payload.columns.patient_id,
        col_date=payload.columns.date,
        col_author=payload.columns.author,
        col_note_text=payload.columns.note_text,
        col_note_type=payload.columns.note_type,
        created_by=created_by,
    )
    session.add(ds)
    await session.commit()
    await session.refresh(ds)
    logger.info("Data source created: %s (%s)", ds.name, ds.id)
    return ds


async def update_source(
    session: AsyncSession,
    ds: DataSource,
    payload: DataSourceUpdate,
    settings: Settings,
) -> DataSource:
    data = payload.model_dump(exclude_unset=True)

    if "host" in data and data["host"] is not None:
        check_host_allowed(data["host"], settings)

    # An omitted password keeps the stored one; an explicit empty string clears
    # it. Treating "not sent" as "clear" would silently break a working source
    # every time someone edited its description.
    if "password" in data:
        password = data.pop("password")
        if password is not None:
            ds.password_encrypted = encrypt_secret(password, settings.app_secret_key)

    if "columns" in data and data["columns"] is not None:
        mapping = payload.columns
        ds.col_id = mapping.id
        ds.col_patient_id = mapping.patient_id
        ds.col_date = mapping.date
        ds.col_author = mapping.author
        ds.col_note_text = mapping.note_text
        ds.col_note_type = mapping.note_type
    data.pop("columns", None)

    for field, value in data.items():
        if value is not None:
            setattr(ds, field, value)

    await session.commit()
    await session.refresh(ds)
    return ds


async def delete_source(session: AsyncSession, ds: DataSource) -> None:
    await session.delete(ds)
    await session.commit()
    logger.info("Data source deleted: %s (%s)", ds.name, ds.id)


async def ensure_bootstrap_source(
    session: AsyncSession, settings: Settings
) -> None:
    """Register NOTES_DATABASE_URL as a data source on first start.

    Keeps a fresh deployment usable without anyone opening the settings page,
    while everything afterwards goes through the managed data sources.
    """
    existing = await session.execute(select(DataSource).limit(1))
    if existing.scalars().first() is not None:
        return

    raw_url = settings.notes_db_url
    if not raw_url:
        logger.info("No NOTES_DATABASE_URL set — starting with no data sources")
        return

    try:
        url = make_url(raw_url)
    except Exception:  # noqa: BLE001 — a bad URL must not stop startup
        logger.warning("NOTES_DATABASE_URL could not be parsed; skipping bootstrap")
        return

    backend = url.get_backend_name()
    engine = {"postgresql": "postgresql", "mssql": "mssql", "sqlite": "sqlite"}.get(
        backend
    )
    if engine is None:
        logger.warning("Unsupported bootstrap engine %r; skipping", backend)
        return

    ds = DataSource(
        name=BOOTSTRAP_NAME,
        description=(
            "Registered automatically from NOTES_DATABASE_URL on first start. "
            "Stands in for the customer's clinical system."
        ),
        engine=engine,
        host=url.host or "",
        port=url.port,
        database_name=url.database or "",
        username=url.username or "",
        password_encrypted=encrypt_secret(
            url.password or "", settings.app_secret_key
        ),
        table_name="medical_notes",
        # The seeded demo table carries the note's specialty; mapping it means
        # the type filter is available out of the box.
        col_note_type="specialty",
        is_default=True,
        created_by="system",
    )
    session.add(ds)
    try:
        await session.commit()
    except IntegrityError:
        # Every uvicorn worker runs startup, so two of them can both find the
        # registry empty and both insert. The unique name constraint catches the
        # loser, which is the right outcome — the source exists either way.
        await session.rollback()
        logger.debug("Default data source already created by another worker")
        return
    logger.info("Bootstrapped default data source from NOTES_DATABASE_URL")
