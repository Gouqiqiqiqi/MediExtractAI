"""Tests for file upload endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_upload_rejects_unauthenticated(anon_client: AsyncClient):
    resp = await anon_client.post("/api/v1/upload/")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_upload_rejects_unsupported_extension(client: AsyncClient):
    """Only .txt, .pdf, .doc, .docx are allowed."""
    resp = await client.post(
        "/api/v1/upload/",
        files={"file": ("test.exe", b"not a real file", "application/octet-stream")},
    )
    assert resp.status_code == 415


@pytest.mark.anyio
async def test_upload_txt_file(client: AsyncClient):
    """A plain text file should be parsed successfully."""
    content = b"Patient presented with headache and nausea."
    resp = await client.post(
        "/api/v1/upload/",
        files={"file": ("note.txt", content, "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "note.txt"
    assert "headache" in data["extracted_text"]
    assert data["char_count"] > 0
