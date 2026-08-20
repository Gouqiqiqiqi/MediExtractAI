"""Tests for notes endpoints (require database — mostly smoke tests)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_list_notes_requires_auth(anon_client: AsyncClient):
    resp = await anon_client.get("/api/v1/notes/")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
