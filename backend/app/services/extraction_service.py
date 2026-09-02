"""AI extraction service — converts free-text notes into structured rows.

Supports two providers, selected via AI_PROVIDER:
  - "gemini"        Google Gemini API (free tier available) — default
  - "azure_openai"  Azure OpenAI (optional)
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config import Settings
from app.models.schemas import ColumnDefinition

logger = logging.getLogger("mediextract.services.extraction")

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _build_prompts(text: str, columns: list[ColumnDefinition]) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for a single note."""
    schema_description = "\n".join(
        f"- {col.name} ({col.data_type}): {col.description or 'No description'}"
        for col in columns
    )
    column_names = [col.name for col in columns]

    system_prompt = (
        "You are a clinical data extraction assistant. "
        "Your job is to read a medical note and extract structured data "
        "according to the user-defined schema.\n\n"
        "RULES:\n"
        "1. Return ONLY valid JSON — an array of objects.\n"
        "2. Each object must have exactly these keys: "
        f"{json.dumps(column_names)}\n"
        "3. If a value is not found in the text, use null.\n"
        "4. Respect data types: text→string, integer→int, float→float, "
        "boolean→true/false, date→YYYY-MM-DD, datetime→ISO 8601, "
        "text[]→array of strings.\n"
        "5. If the note contains multiple entries (e.g. multiple medications), "
        "return multiple objects.\n"
        "6. Do NOT invent data that isn't in the note.\n"
        "7. Do NOT include any explanation — only the JSON array.\n"
    )

    user_prompt = (
        f"## Output Schema\n{schema_description}\n\n"
        f"## Medical Note\n{text}\n\n"
        "Extract the data now. Return ONLY the JSON array."
    )
    return system_prompt, user_prompt


def _normalise(parsed: Any) -> list[dict[str, Any]]:
    """The model might return {"rows": [...]} or a bare object — normalise to a list."""
    if isinstance(parsed, dict):
        for key in ("rows", "data", "results", "items"):
            if key in parsed and isinstance(parsed[key], list):
                return parsed[key]
        return [parsed]
    if not isinstance(parsed, list):
        return [parsed]
    return parsed


class ExtractionService:
    """Singleton service wrapping the configured AI provider."""

    _instance: ExtractionService | None = None
    _settings: Settings | None = None
    _azure_client: Any = None  # AsyncAzureOpenAI, imported lazily

    # ── Lifecycle ──

    @classmethod
    def initialize(cls, settings: Settings) -> None:
        cls._settings = settings

        if settings.ai_provider == "gemini":
            if not settings.gemini_api_key:
                logger.warning("GEMINI_API_KEY not set — extraction will be unavailable")
            else:
                logger.info(
                    "ExtractionService initialised (provider=gemini, model=%s)",
                    settings.gemini_model,
                )
        elif settings.ai_provider == "azure_openai":
            if not settings.azure_openai_endpoint:
                logger.warning("Azure OpenAI not configured — extraction will be unavailable")
            else:
                from openai import AsyncAzureOpenAI  # lazy import — optional dependency

                cls._azure_client = AsyncAzureOpenAI(
                    azure_endpoint=settings.azure_openai_endpoint,
                    api_key=settings.azure_openai_api_key,
                    api_version=settings.azure_openai_api_version,
                )
                logger.info(
                    "ExtractionService initialised (provider=azure_openai, deployment=%s)",
                    settings.azure_openai_deployment,
                )

        cls._instance = cls()

    @classmethod
    def instance(cls) -> ExtractionService:
        if cls._instance is None:
            from app.config import get_settings
            cls.initialize(get_settings())
        return cls._instance

    @classmethod
    def shutdown(cls) -> None:
        cls._azure_client = None
        cls._instance = None
        cls._settings = None

    # ── Core extraction ──

    async def extract(
        self,
        texts: list[str],
        columns: list[ColumnDefinition],
        provenance: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Extract structured rows from one or more free-text notes.

        ``provenance``, when given, must be the same length as ``texts``. Its
        entry for a note is merged into every row that note produces, so the
        link back to the source survives however the rows are later reordered.

        Attaching it here rather than at the end is deliberate: a single note
        can yield several rows, so the caller cannot reconstruct the mapping
        from the returned list alone.
        """
        if provenance is not None and len(provenance) != len(texts):
            raise ValueError(
                f"provenance has {len(provenance)} entries for {len(texts)} texts"
            )

        all_rows: list[dict[str, Any]] = []
        for i, text in enumerate(texts):
            logger.info("Extracting note %d/%d (%d chars)", i + 1, len(texts), len(text))
            rows = await self._extract_single(text, columns)
            if provenance is not None:
                source = provenance[i]
                # Provenance first so a hallucinated key of the same name in the
                # model output cannot overwrite it.
                rows = [{**source, **row, **source} for row in rows]
            all_rows.extend(rows)
        return all_rows

    async def _extract_single(
        self,
        text: str,
        columns: list[ColumnDefinition],
    ) -> list[dict[str, Any]]:
        settings = self._settings
        if settings is None:
            raise RuntimeError("ExtractionService not initialised")

        system_prompt, user_prompt = _build_prompts(text, columns)

        if settings.ai_provider == "gemini":
            raw = await self._call_gemini(settings, system_prompt, user_prompt)
        else:
            raw = await self._call_azure_openai(settings, system_prompt, user_prompt)

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("LLM returned invalid JSON: %.200s", raw)
            return []

        return _normalise(parsed)

    # ── Providers ──

    async def _call_gemini(
        self, settings: Settings, system_prompt: str, user_prompt: str
    ) -> str:
        if not settings.gemini_api_key:
            raise RuntimeError("Gemini is not configured. Set GEMINI_API_KEY.")

        url = f"{GEMINI_BASE}/models/{settings.gemini_model}:generateContent"
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 4096,
                "responseMimeType": "application/json",
            },
        }
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                url,
                params={"key": settings.gemini_api_key},
                json=payload,
            )
        if resp.status_code != 200:
            logger.error("Gemini API error %s: %.300s", resp.status_code, resp.text)
            raise RuntimeError(f"Gemini API returned {resp.status_code}")

        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            logger.error("Unexpected Gemini response shape: %.300s", json.dumps(data))
            return "[]"

    async def _call_azure_openai(
        self, settings: Settings, system_prompt: str, user_prompt: str
    ) -> str:
        if self._azure_client is None:
            raise RuntimeError(
                "Azure OpenAI is not configured. "
                "Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY."
            )
        response = await self._azure_client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or "[]"
