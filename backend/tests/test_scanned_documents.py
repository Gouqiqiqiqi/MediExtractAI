"""Tests for documents that arrive as scans rather than as text.

The bug these exist for: a PDF with no text layer parsed to an empty string,
which travelled all the way to the model as an empty note. Two of them joined
by the client's separator even looked like content — seven characters of
"---" — so the run button lit up and the extraction returned nothing.

Two things had to be true to fix it. A scan has to be turned into something a
model can read, and it must only be sent to a model that can read it: the
default chain's second entry is text-only, and a request it cannot serve is
not a request it should be blocked for having refused.
"""

from __future__ import annotations

import base64

import fitz
import httpx
import pytest

from app.config import Settings
from app.models.schemas import ColumnDefinition, DocumentImage, SourceDocument
from app.services import model_rotation as mr
from app.services.extraction_service import ExtractionService
from app.services.file_service import FileService

COLUMNS = [ColumnDefinition(name="Diagnosis", description="Primary diagnosis")]
ANSWER = '[{"Diagnosis": "generalised anxiety disorder"}]'


# ── Fixtures: the two kinds of PDF ──────────────────────────────────────────

def scanned_pdf() -> bytes:
    """A PDF that is one image and nothing else — what a scanner produces."""
    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 400, 500))
    pixmap.set_rect(pixmap.irect, (255, 255, 255))
    page.insert_image(fitz.Rect(0, 0, 400, 500), pixmap=pixmap)
    data = doc.tobytes()
    doc.close()
    return data


def text_pdf(text: str = "Diagnosis: generalised anxiety disorder. Sertraline 50mg.") -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


# ── Parsing ─────────────────────────────────────────────────────────────────

def test_a_scan_is_rendered_to_page_images():
    parsed = FileService().parse_document(scanned_pdf(), ".pdf")

    assert parsed.text == ""
    assert len(parsed.images) == 1
    assert parsed.images[0].mime_type in ("image/jpeg", "image/png")
    assert base64.b64decode(parsed.images[0].data)  # real bytes, not a marker
    assert parsed.has_content
    assert "no text layer" in parsed.warning.lower()


def test_a_text_pdf_is_still_read_as_text():
    """Rendering is the fallback, not the new default — it costs far more."""
    parsed = FileService().parse_document(text_pdf(), ".pdf")

    assert "generalised anxiety disorder" in parsed.text
    assert parsed.images == []
    assert parsed.warning == ""


def test_scanner_furniture_does_not_count_as_a_text_layer():
    """A page number stamped into the text layer is not the note."""
    parsed = FileService().parse_document(text_pdf("Page 1"), ".pdf")

    assert parsed.images, "a near-empty text layer should still be treated as a scan"


def test_the_page_cap_is_honoured():
    doc = fitz.open()
    for _ in range(5):
        doc.new_page()
    many_pages = doc.tobytes()
    doc.close()

    parsed = FileService(max_render_pages=2).parse_document(many_pages, ".pdf")

    assert len(parsed.images) == 2
    assert parsed.page_count == 5
    assert "first 2 of 5" in parsed.warning


# ── Which models may see a scan ─────────────────────────────────────────────

def test_text_only_models_are_recognised_as_such():
    # The shipped chain's first fallback. Sending it images earns a 400, which
    # would park it for the session — for text it is perfectly good.
    assert not mr.supports_vision("groq", "openai/gpt-oss-120b")
    assert mr.supports_vision("gemini", "gemini-3.5-flash")
    assert mr.supports_vision("azure_openai", "gpt-4o")
    assert not mr.supports_vision("gemini", "gemma-3-27b-it")


def test_a_deployment_can_name_a_vision_model_we_do_not_know():
    assert not mr.supports_vision("mistral", "mistral-small-latest")
    assert mr.supports_vision(
        "mistral", "mistral-small-latest", ["mistral:mistral-small-latest"]
    )


def test_the_shipped_chain_keeps_text_and_vision_apart():
    settings = Settings(gemini_api_key="k", groq_api_key="k", mistral_api_key="k")
    chain = mr.parse_chain(
        primary=mr.ModelCandidate(settings.ai_provider, settings.ai_primary_model),
        fallbacks=settings.ai_fallback_models,
        default_provider=settings.ai_provider,
        is_configured=lambda p: settings.ai_provider_configured.get(p, False),
        vision_models=settings.ai_vision_models,
    )
    rotation = mr.ModelRotation(chain)

    assert [c.label for c in rotation.eligible()] == [c.label for c in chain]
    assert all(c.provider == "gemini" for c in rotation.eligible(require_vision=True))


# ── Routing, end to end ─────────────────────────────────────────────────────

class RecordingLLM:
    """Fake provider that keeps the payloads it was sent."""

    def __init__(self) -> None:
        self.payloads: list[tuple[str, dict]] = []

    async def post(self, url, *, params=None, headers=None, json=None):  # noqa: A002
        gemini = "/models/" in url
        model = url.split("/models/")[1].split(":")[0] if gemini else json["model"]
        self.payloads.append((model, json))
        body = (
            {"candidates": [{"content": {"parts": [{"text": ANSWER}]}}]}
            if gemini
            else {"choices": [{"message": {"content": ANSWER}}]}
        )
        return httpx.Response(
            200, json=body, request=httpx.Request("POST", "https://example.invalid")
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    @property
    def models(self) -> list[str]:
        return [model for model, _ in self.payloads]


@pytest.fixture
def recording_llm(monkeypatch):
    def install(**settings) -> RecordingLLM:
        fake = RecordingLLM()
        monkeypatch.setattr(
            "app.services.extraction_service.httpx.AsyncClient",
            lambda *a, **k: fake,
        )
        base = {
            "ai_provider": "gemini",
            "gemini_api_key": "test-key",
            "gemini_model": "gemini-3.5-flash",
            "ai_fallback_models": "groq:openai/gpt-oss-120b,gemini-2.5-flash",
            "groq_api_key": "test-key",
            "mistral_api_key": "",
        }
        base.update(settings)
        ExtractionService.initialize(Settings(**base))
        return fake

    yield install
    ExtractionService.shutdown()


PAGE = DocumentImage(mime_type="image/jpeg", data="Zm9v", page=1)


@pytest.mark.anyio
async def test_a_scan_goes_to_a_vision_model_as_an_image(recording_llm):
    fake = recording_llm()

    rows = await ExtractionService.instance().extract(
        [SourceDocument(images=[PAGE])], COLUMNS
    )

    assert rows == [{"Diagnosis": "generalised anxiety disorder"}]
    model, payload = fake.payloads[0]
    assert model == "gemini-3.5-flash"
    parts = payload["contents"][0]["parts"]
    assert parts[0]["text"], "the instructions must come before the pages"
    assert parts[1]["inline_data"] == {"mime_type": "image/jpeg", "data": "Zm9v"}


@pytest.mark.anyio
async def test_a_scan_skips_a_text_only_model_without_blaming_it(recording_llm):
    """The whole point of the split.

    The text-only model is second in the chain. A scan must not be offered to
    it — and it must not be put in a cooldown for that, because it is still
    the right answer for the next note that *is* text.
    """
    fake = recording_llm(gemini_model="gemini-3.5-flash")
    service = ExtractionService.instance()
    # Take the vision-capable primary out of the running.
    rotation = service._rotation
    rotation.block(rotation.candidates[0], 600, "daily quota exhausted")

    await service.extract([SourceDocument(images=[PAGE])], COLUMNS)

    assert fake.models == ["gemini-2.5-flash"], "must skip groq, not call it"
    assert all(
        row["model"] != "openai/gpt-oss-120b" or row["available"]
        for row in service.model_status()
    ), "a model that was never eligible must not be left on a cooldown"


@pytest.mark.anyio
async def test_plain_text_still_uses_the_whole_chain(recording_llm):
    fake = recording_llm()
    service = ExtractionService.instance()
    rotation = service._rotation
    rotation.block(rotation.candidates[0], 600, "daily quota exhausted")

    await service.extract(["Diagnosis: anxiety"], COLUMNS)

    assert fake.models == ["openai/gpt-oss-120b"]
    _, payload = fake.payloads[0]
    # Text-only requests keep the plain-string content: the parts form is not
    # accepted everywhere, and this path has to work on every model.
    assert isinstance(payload["messages"][1]["content"], str)


@pytest.mark.anyio
async def test_an_openai_compatible_vision_model_gets_a_data_url(recording_llm):
    fake = recording_llm(
        ai_provider="groq",
        groq_model="meta-llama/llama-4-scout-17b",
        ai_fallback_models="",
        gemini_api_key="",
    )

    await ExtractionService.instance().extract([SourceDocument(images=[PAGE])], COLUMNS)

    _, payload = fake.payloads[0]
    content = payload["messages"][1]["content"]
    assert content[0]["type"] == "text"
    assert content[1]["image_url"]["url"] == "data:image/jpeg;base64,Zm9v"


@pytest.mark.anyio
async def test_a_chain_that_cannot_see_says_so(recording_llm):
    """Better than a 400 from the provider, which reads as a broken model."""
    recording_llm(
        ai_provider="groq",
        groq_model="openai/gpt-oss-120b",
        ai_fallback_models="",
        gemini_api_key="",
    )

    with pytest.raises(RuntimeError, match="no model in the chain can read images"):
        await ExtractionService.instance().extract(
            [SourceDocument(images=[PAGE])], COLUMNS
        )


@pytest.mark.anyio
async def test_the_scan_prompt_tells_the_model_not_to_guess(recording_llm):
    """Illegible handwriting must come back as null, not as a plausible word."""
    fake = recording_llm()

    await ExtractionService.instance().extract([SourceDocument(images=[PAGE])], COLUMNS)

    _, payload = fake.payloads[0]
    system = payload["system_instruction"]["parts"][0]["text"].lower()
    assert "illegible" in system
    assert "null" in system
