"""The headers every response carries, and the one place they must relax."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_api_responses_carry_the_strictest_policy(client: AsyncClient):
    """The API returns JSON and files, never markup — nothing may load."""
    resp = await client.get("/api/v1/runs/stats")
    assert resp.headers["content-security-policy"] == "default-src 'none'"
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"


@pytest.mark.anyio
async def test_the_interactive_docs_are_allowed_to_load(client: AsyncClient):
    """A blanket policy left the page the README tells people to open blank.

    FastAPI renders Swagger UI from a CDN, so the docs paths — and only those —
    name it explicitly.
    """
    resp = await client.get("/docs")
    assert resp.status_code == 200
    csp = resp.headers["content-security-policy"]
    assert "cdn.jsdelivr.net" in csp
    assert "default-src 'self'" in csp
