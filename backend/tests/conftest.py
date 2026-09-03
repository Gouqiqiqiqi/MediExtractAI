"""Shared test fixtures."""

from __future__ import annotations

import os

# Auth tests exercise the non-demo path; set env BEFORE the app imports settings.
os.environ["DEMO_MODE"] = "false"

import tempfile
from pathlib import Path

# The app reads its settings at import time, so the test database has to be
# chosen before anything under app/ is imported. Hence the noqa on the imports
# below — same reason as scripts/seed_notes.py.
TEST_DB = Path(tempfile.gettempdir()) / "mediextract_test.db"
# SQLite by default so the suite needs no services. Production runs on Postgres,
# so TEST_DATABASE_URL points the same tests at a real one when it matters —
# what breaks between the two is DDL and column types, which only a Postgres
# run exercises.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", f"sqlite+aiosqlite:///{TEST_DB}"
)

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services import app_database  # noqa: E402


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
async def app_db():
    """Give the app the database its dependencies expect.

    ASGITransport drives the app directly and never runs its lifespan, so
    nothing had created the engine and every request failed inside the session
    dependency — before reaching whatever the test was actually asserting. A
    throwaway SQLite file is enough: these tests do not care what is in it,
    only that asking for a session works.
    """
    app_database.init_engine(get_settings())
    await app_database.create_tables()
    yield
    await app_database.dispose()
    TEST_DB.unlink(missing_ok=True)


@pytest.fixture
async def client():
    """Authenticated async test client — uses dev-bypass token."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"Authorization": "Bearer dev-bypass"},
    ) as ac:
        yield ac


@pytest.fixture
async def anon_client():
    """Unauthenticated async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as ac:
        yield ac
