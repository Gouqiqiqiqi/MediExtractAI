"""Shared test fixtures."""

from __future__ import annotations

import os

# Auth tests exercise the non-demo path; set env BEFORE the app imports settings.
os.environ["DEMO_MODE"] = "false"
os.environ["DATABASE_URL"] = ""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


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
