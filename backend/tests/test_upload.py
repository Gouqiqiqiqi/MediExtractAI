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


@pytest.mark.anyio
async def test_upload_of_a_scan_returns_page_images(client: AsyncClient):
    """A PDF with no text layer comes back as pages, not as an empty string.

    This is the upload half of the bug: the response used to be a 200 with
    zero characters, which the UI showed as a successfully uploaded document.
    """
    import fitz

    doc = fitz.open()
    doc.new_page(width=300, height=400)
    scan = doc.tobytes()
    doc.close()

    resp = await client.post(
        "/api/v1/upload/",
        files={"file": ("scan.pdf", scan, "application/pdf")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["char_count"] == 0
    assert len(data["page_images"]) == 1
    assert data["page_images"][0]["data"]
    assert data["warning"], "the client has to be able to say why this looks empty"


@pytest.mark.anyio
async def test_upload_of_an_unreadable_file_is_an_error_not_an_empty_success(
    client: AsyncClient,
):
    resp = await client.post(
        "/api/v1/upload/",
        files={"file": ("empty.txt", b"   \n  ", "text/plain")},
    )
    assert resp.status_code == 422
    assert "No text could be extracted" in resp.json()["detail"]


@pytest.mark.anyio
async def test_extraction_refuses_a_request_with_nothing_in_it(client: AsyncClient):
    """The other half of the bug, from the client's side.

    Two empty documents joined by the uploader's "\\n\\n---\\n\\n" separator
    made a seven-character request that looked like content and cost a model
    call. Whitespace and separators are not a document.
    """
    resp = await client.post(
        "/api/v1/extraction/from-text",
        json={
            "text": "\n\n---\n\n",
            "images": [],
            "columns": [{"name": "Diagnosis", "data_type": "text"}],
        },
    )
    assert resp.status_code == 422
