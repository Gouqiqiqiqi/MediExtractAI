#!/usr/bin/env python3
"""Seed the source notes database with synthetic clinical notes.

This stands in for the customer's existing clinical system. In a real
deployment we would be handed read-only credentials to a database that already
exists; for the demo we create and populate an equivalent table ourselves.

Usage (from the backend/ directory or inside the container's /app):

    python scripts/seed_notes.py            # create table, insert if empty
    python scripts/seed_notes.py --force    # drop existing rows and re-insert

The connection string comes from NOTES_DATABASE_URL, falling back to
DATABASE_URL — the same resolution the application uses.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Allow running as a plain script from either backend/ or /app.
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))
sys.path.insert(0, str(SCRIPT_DIR))

from sqlalchemy import delete, func, insert, select  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.services.database_service import (  # noqa: E402
    _normalise_async_url,
    medical_notes,
    metadata,
)
from synthetic_notes import NOTES  # noqa: E402


async def seed(force: bool = False) -> int:
    settings = get_settings()
    url = _normalise_async_url(settings.notes_db_url)
    print(f"→ notes database: {url.split('@')[-1]}")  # never print credentials

    engine = create_async_engine(url, echo=False)

    async with engine.begin() as conn:
        # The customer's table would already exist; we create it because we are
        # standing in for that system.
        await conn.run_sync(metadata.create_all)

        existing = await conn.scalar(
            select(func.count()).select_from(medical_notes)
        )

        if existing and not force:
            print(f"→ {existing} notes already present — nothing to do")
            print("  (use --force to wipe and re-seed)")
            await engine.dispose()
            return existing

        if existing:
            print(f"→ --force: deleting {existing} existing rows")
            await conn.execute(delete(medical_notes))

        rows = [
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
        await conn.execute(insert(medical_notes), rows)
        print(f"→ inserted {len(rows)} synthetic notes")

        total = await conn.scalar(select(func.count()).select_from(medical_notes))

    await engine.dispose()
    print(f"✓ done — {total} notes in medical_notes")
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="delete existing rows before inserting",
    )
    args = parser.parse_args()
    asyncio.run(seed(force=args.force))


if __name__ == "__main__":
    main()
