"""Tests for the extraction endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_extract_from_text_requires_auth(anon_client: AsyncClient):
    """Unauthenticated requests should be rejected."""
    resp = await anon_client.post("/api/v1/extraction/from-text", json={})
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_extract_from_text_validation(client: AsyncClient):
    """Missing required fields should return 422."""
    resp = await client.post("/api/v1/extraction/from-text", json={})
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_extract_from_text_valid_payload(client: AsyncClient):
    """A valid payload should be accepted (extraction may fail without OpenAI)."""
    payload = {
        "text": "Patient presents with chest pain. BP 140/90. Prescribed aspirin 75mg.",
        "columns": [
            {"name": "Symptom", "data_type": "text", "description": "Main symptom"},
            {"name": "BP_Systolic", "data_type": "integer", "description": "Systolic BP"},
            {"name": "Medication", "data_type": "text", "description": "Prescribed medication"},
        ],
    }
    resp = await client.post("/api/v1/extraction/from-text", json=payload)
    # 200 if an AI provider is configured, 503 if not
    assert resp.status_code in (200, 503)


@pytest.mark.anyio
async def test_model_chain_is_reportable(client: AsyncClient):
    """The chain has to be inspectable — a silent fallback is unexplainable."""
    resp = await client.get("/api/v1/extraction/models")
    assert resp.status_code == 200
    for model in resp.json():
        assert {"provider", "model", "is_primary", "available"} <= set(model)


@pytest.mark.anyio
async def test_model_chain_requires_auth(anon_client: AsyncClient):
    resp = await anon_client.get("/api/v1/extraction/models")
    assert resp.status_code == 401
