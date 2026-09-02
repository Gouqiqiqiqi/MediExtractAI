#!/usr/bin/env python3
"""Seed the demo notes database with synthetic clinical notes.

This script plays the part of the customer's existing clinical system. In a
real deployment the table is already there and we are handed read-only
credentials to it; here we create and populate an equivalent one, which is why
the DDL lives in this script rather than in the application.

Usage (from backend/ or the container's /app):

    python scripts/seed_notes.py            # create table, insert if empty
    python scripts/seed_notes.py --force    # delete existing rows and re-insert

The connection string comes from NOTES_DATABASE_URL, falling back to
DATABASE_URL — the same bootstrap the application uses on first start.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))
sys.path.insert(0, str(SCRIPT_DIR))

from sqlalchemy import (  # noqa: E402
    Column,
    Date,
    MetaData,
    String,
    Table,
    Text,
    delete,
    func,
    insert,
    select,
)
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.config import get_settings  # noqa: E402
from synthetic_notes import NOTES  # noqa: E402

metadata = MetaData()

# Named and shaped the way a hospital table plausibly would be. The application
# does not depend on these names — a data source's column mapping tells it what
# each one means.
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


# A second system, deliberately shaped nothing like the first: different table
# name, different column names, a subset of the notes. Two customers never name
# things the same way, and a demo with only one schema cannot show that the
# column mapping is doing any work.
clinical_documents = Table(
    "clinical_documents",
    metadata,
    Column("doc_id", String(64), primary_key=True),
    Column("mrn", String(64)),
    Column("authored_on", Date),
    Column("clinician_name", String(255)),
    Column("service", String(128)),
    Column("doc_body", Text),
)

# Which of the synthetic notes belong to the "clinic letters" system.
CLINIC_SPECIALTIES = {"Cardiology", "Endocrinology", "Rheumatology", "Oncology"}


def _async_url(url: str) -> str:
    for sync_prefix, async_prefix in (
        ("postgresql://", "postgresql+asyncpg://"),
        ("postgres://", "postgresql+asyncpg://"),
        ("sqlite://", "sqlite+aiosqlite://"),
    ):
        if url.startswith(sync_prefix):
            return url.replace(sync_prefix, async_prefix, 1)
    return url


async def _seed_table(conn, table, rows, label: str, force: bool) -> int:
    """Insert rows into one table unless it already has some.

    Each table is decided independently — a second system added later must not
    be skipped just because the first one was already populated.
    """
    existing = await conn.scalar(select(func.count()).select_from(table))

    if existing and not force:
        print(f"→ {label}: {existing} rows already present — skipped")
        return existing

    if existing:
        print(f"→ {label}: --force, deleting {existing} rows")
        await conn.execute(delete(table))

    await conn.execute(insert(table), rows)
    print(f"→ {label}: inserted {len(rows)} rows")
    return await conn.scalar(select(func.count()).select_from(table))


async def seed(force: bool = False) -> None:
    settings = get_settings()
    url = _async_url(settings.notes_db_url)
    print(f"→ notes database: {url.split('@')[-1]}")  # never print credentials

    engine = create_async_engine(url, echo=False)

    note_rows = [
        {
            "id": f"NOTE-{i:04d}",
            "patient_id": note["patient_id"],
            "note_date": note["note_date"],
            "author": note["author"],
            "specialty": note["specialty"],
            "note_text": note["note_text"],
        }
        for i, note in enumerate(NOTES, start=1)
    ]

    doc_rows = [
        {
            "doc_id": f"DOC-{i:03d}",
            "mrn": note["patient_id"].replace("SYN-", "MRN"),
            "authored_on": note["note_date"],
            "clinician_name": note["author"],
            "service": note["specialty"],
            "doc_body": note["note_text"],
        }
        for i, note in enumerate(
            (n for n in NOTES if n["specialty"] in CLINIC_SPECIALTIES), start=1
        )
    ]

    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
        notes_total = await _seed_table(
            conn, medical_notes, note_rows, "medical_notes", force
        )
        docs_total = await _seed_table(
            conn, clinical_documents, doc_rows, "clinical_documents", force
        )

    await engine.dispose()
    print(f"✓ done — medical_notes={notes_total}, clinical_documents={docs_total}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true", help="delete existing rows before inserting"
    )
    args = parser.parse_args()
    asyncio.run(seed(force=args.force))


if __name__ == "__main__":
    main()
