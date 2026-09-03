"""AI extraction service — converts free-text notes into structured rows.

Providers, selected via AI_PROVIDER and used as fallbacks by name:
  - "gemini"        Google Gemini API (free tier available) — default
  - "groq"          Groq (free tier, OpenAI-compatible)
  - "mistral"       Mistral La Plateforme (free tier, OpenAI-compatible)
  - "azure_openai"  Azure OpenAI (optional)

Everything but Gemini and Azure goes through one OpenAI-compatible adapter, so
adding another provider of that kind is an endpoint URL and an API key rather
than a new integration.

AI_PROVIDER and its model are only the *first* choice. Extraction sends one
request per note against quotas counted per model and per day, so a demo can
exhaust a free-tier model mid-batch. AI_FALLBACK_MODELS names what to use when
that happens, and ``app.services.model_rotation`` decides when to move on and
for how long to leave the exhausted model alone.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import httpx

from app.config import Settings
from app.models.schemas import ColumnDefinition, DocumentImage, SourceDocument
from app.services.model_rotation import (
    CONFIG_ERROR_COOLDOWN_SECONDS,
    OPENAI_COMPATIBLE_ENDPOINTS,
    TRANSIENT_COOLDOWN_SECONDS,
    ModelCandidate,
    ModelRotation,
    ProviderError,
    gemini_rate_limit,
    openai_compatible_rate_limit,
    parse_chain,
    retry_after_seconds,
)

logger = logging.getLogger("mediextract.services.extraction")

# Notes are extracted concurrently, but not without a ceiling: provider rate
# limits are per-minute as well as per-day, and firing fifty requests at once is
# the fastest way to turn a working batch into a wall of 429s.
MAX_CONCURRENT_EXTRACTIONS = 4

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _build_prompts(
    document: SourceDocument, columns: list[ColumnDefinition]
) -> tuple[str, str]:
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

    if document.images:
        # Reading a scan is a different job from reading text, and the failure
        # mode is different too: a model asked to transcribe an illegible
        # handwritten word will offer a plausible one rather than admit it
        # cannot read it. In a clinical record a confident guess is worse than
        # a gap, because only the gap gets checked.
        system_prompt += (
            "\nTHIS NOTE IS SUPPLIED AS SCANNED PAGE IMAGES:\n"
            "8. Read the values off the page. Transcribe what is written, "
            "including handwriting, without normalising or correcting it.\n"
            "9. If a value is illegible, obscured or you are not certain of "
            "it, use null. Never guess at a word you cannot read — an omitted "
            "value gets checked by a human, an invented one does not.\n"
            "10. Ignore printed form furniture — headers, field labels, page "
            "numbers — unless a value is written against it.\n"
        )

    note_section = "## Medical Note\n"
    if document.text.strip():
        note_section += document.text
        if document.images:
            note_section += "\n\n(Further pages follow as images.)"
    else:
        pages = len(document.images)
        note_section += (
            f"The note is supplied as {pages} scanned page"
            f"{'' if pages == 1 else 's'}, attached as images."
        )

    user_prompt = (
        f"## Output Schema\n{schema_description}\n\n"
        f"{note_section}\n\n"
        "Extract the data now. Return ONLY the JSON array."
    )
    return system_prompt, user_prompt


def _as_document(item: SourceDocument | str) -> SourceDocument:
    """Accept a bare string where a document is expected.

    Most callers extract from plain text and should not have to wrap it.
    """
    return item if isinstance(item, SourceDocument) else SourceDocument(text=item)


def _describe(document: SourceDocument) -> str:
    """How a document is logged — chars, pages, or both."""
    parts = []
    if document.text:
        parts.append(f"{len(document.text)} chars")
    if document.images:
        parts.append(f"{len(document.images)} page images")
    return ", ".join(parts) or "empty"


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


def _openai_user_content(
    user_prompt: str, images: list[DocumentImage] | None
) -> Any:
    """Build the user message for an OpenAI-shaped API.

    Kept as a plain string when there are no images: the content-parts form is
    universally accepted by the vision models but not by every text-only one,
    and the text path here has to keep working on all of them.
    """
    if not images:
        return user_prompt
    content: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]
    for image in images:
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{image.mime_type};base64,{image.data}"
                },
            }
        )
    return content


class ExtractionService:
    """Singleton service wrapping the configured chain of AI models."""

    _instance: ExtractionService | None = None
    _settings: Settings | None = None
    _rotation: ModelRotation | None = None
    _azure_client: Any = None  # AsyncAzureOpenAI, imported lazily

    # ── Lifecycle ──

    @classmethod
    def initialize(cls, settings: Settings) -> None:
        cls._settings = settings
        cls._azure_client = None

        configured = settings.ai_provider_configured
        chain = parse_chain(
            primary=ModelCandidate(settings.ai_provider, settings.ai_primary_model),
            fallbacks=settings.ai_fallback_models,
            default_provider=settings.ai_provider,
            is_configured=lambda provider: configured.get(provider, False),
            vision_models=settings.ai_vision_models,
        )
        cls._rotation = ModelRotation(chain)

        if not chain:
            logger.warning(
                "No AI model is configured — extraction will be unavailable. "
                "Set GEMINI_API_KEY, or AZURE_OPENAI_ENDPOINT and "
                "AZURE_OPENAI_API_KEY."
            )
        else:
            logger.info(
                "ExtractionService initialised — model chain: %s",
                " → ".join(
                    f"{c.label}{' [vision]' if c.supports_vision else ''}"
                    for c in chain
                ),
            )
            if not any(c.supports_vision for c in chain):
                logger.warning(
                    "No model in the chain can read images — scanned documents "
                    "will be rejected. Add a vision-capable model, or name one "
                    "in AI_VISION_MODELS."
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
        cls._rotation = None

    # ── Status ──

    def model_status(self) -> list[dict[str, Any]]:
        """The chain and what each model is currently doing, for the API."""
        return self._rotation.status() if self._rotation else []

    # ── Core extraction ──

    async def extract(
        self,
        documents: list[SourceDocument | str],
        columns: list[ColumnDefinition],
        provenance: list[dict[str, Any]] | None = None,
        models_used: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Extract structured rows from one or more notes.

        A note is a ``SourceDocument`` — text, scanned page images, or both —
        and a bare string is accepted as shorthand for text. A note carrying
        images is only sent to a model that can read them; see ``_generate``.

        ``models_used``, when given, is filled with the label of every model
        that answered. The chain rotates on quota, so a run reviewed weeks
        later cannot otherwise say what produced it.

        ``provenance``, when given, must be the same length as ``texts``. Its
        entry for a note is merged into every row that note produces, so the
        link back to the source survives however the rows are later reordered.

        Attaching it here rather than at the end is deliberate: a single note
        can yield several rows, so the caller cannot reconstruct the mapping
        from the returned list alone.
        """
        if provenance is not None and len(provenance) != len(documents):
            raise ValueError(
                f"provenance has {len(provenance)} entries for "
                f"{len(documents)} documents"
            )

        notes = [_as_document(d) for d in documents]

        settings = self._settings
        if settings is None:
            raise RuntimeError("ExtractionService not initialised")

        total = len(notes)
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_EXTRACTIONS)

        # One budget for the whole batch, because the caller is one HTTP
        # request: twenty notes that each take their own generous timeout add
        # up to a request nginx has already given up on.
        deadline = time.monotonic() + settings.ai_deadline_seconds

        async def extract_one(
            index: int, document: SourceDocument
        ) -> list[dict[str, Any]]:
            async with semaphore:
                logger.info(
                    "Extracting note %d/%d (%s)",
                    index + 1,
                    total,
                    _describe(document),
                )
                return await self._extract_single(
                    document, columns, deadline, models_used
                )

        # Concurrent, but the results come back in request order, so the caller's
        # note order — and therefore the provenance pairing below — is preserved.
        per_note = await asyncio.gather(
            *(extract_one(i, note) for i, note in enumerate(notes))
        )

        all_rows: list[dict[str, Any]] = []
        for i, rows in enumerate(per_note):
            if provenance is not None:
                source = provenance[i]
                # Provenance first so a hallucinated key of the same name in the
                # model output cannot overwrite it.
                rows = [{**source, **row, **source} for row in rows]
            all_rows.extend(rows)
        return all_rows

    async def _extract_single(
        self,
        document: SourceDocument | str,
        columns: list[ColumnDefinition],
        deadline: float | None = None,
        models_used: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        settings = self._settings
        if settings is None:
            raise RuntimeError("ExtractionService not initialised")

        if deadline is None:
            deadline = time.monotonic() + settings.ai_deadline_seconds

        note = _as_document(document)
        system_prompt, user_prompt = _build_prompts(note, columns)
        raw = await self._generate(
            settings,
            system_prompt,
            user_prompt,
            deadline,
            models_used,
            images=note.images,
        )

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("LLM returned invalid JSON: %.200s", raw)
            return []

        return _normalise(parsed)

    # ── Rotation ──

    async def _generate(
        self,
        settings: Settings,
        system_prompt: str,
        user_prompt: str,
        deadline: float,
        models_used: set[str] | None = None,
        images: list[DocumentImage] | None = None,
    ) -> str:
        """Call the first usable model, moving down the chain as they fail.

        When the note carries page images the chain is narrowed to the models
        that can read them, before any of the availability logic below runs.
        A text-only model is not a failed candidate for a scan — it was never
        a candidate — so it is filtered out rather than tried and blocked.

        The cooldown a failure sets is shared, so the other notes in the batch
        skip the exhausted model instead of each discovering it for themselves.

        A model that has just answered 429 will not answer differently two
        seconds later, so a failed candidate is not tried again until either
        another one has been tried or its cooldown has actually been waited
        out — and each may be waited out once. Both sets shrink the options
        monotonically, which is what makes this loop terminate.
        """
        rotation = self._rotation
        if rotation is None or not rotation.candidates:
            raise RuntimeError(
                "No AI model is configured. Set GEMINI_API_KEY (or the "
                "AZURE_OPENAI_* settings) and restart."
            )

        images = images or []
        require_vision = bool(images)
        if require_vision and not rotation.eligible(require_vision=True):
            raise RuntimeError(
                "This document is a scan and has to be read as images, but no "
                "model in the chain can read images. Configure a "
                "vision-capable model (Gemini and GPT-4o-class deployments "
                "are), or name one in AI_VISION_MODELS. Chain: "
                + ", ".join(c.label for c in rotation.candidates)
            )

        tried: set[str] = set()
        waited: set[str] = set()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError(
                    "Extraction ran out of time before a model answered. "
                    f"Models tried: {rotation.describe_waits(require_vision)}. "
                    "Select fewer notes, or try again once a model is back."
                )

            candidate = rotation.next_available(tried, require_vision)

            if candidate is None:
                # Nothing is usable right now. Waiting beats failing only when
                # the wait is short — a per-minute limit on a single-model
                # deployment is seconds, but a spent daily quota is hours and
                # the caller deserves to be told rather than left hanging.
                candidate, wait = rotation.soonest(waited, require_vision)
                if candidate is None:
                    raise RuntimeError(
                        "Every AI model in the chain failed for this note: "
                        f"{rotation.describe_waits(require_vision)}"
                    )
                if wait > settings.ai_max_wait_seconds or wait >= remaining:
                    raise RuntimeError(
                        "All AI models are rate limited — "
                        f"{rotation.describe_waits(require_vision)}. Add "
                        "another model to AI_FALLBACK_MODELS, or try again "
                        "later."
                    )
                logger.info(
                    "Waiting %.1fs for %s to come off cooldown", wait, candidate.label
                )
                await asyncio.sleep(wait)
                # The cooldown has been served, so drop it rather than leaving
                # the candidate to be filtered out by a clock that a fraction
                # of a second of drift can still put on the wrong side.
                rotation.clear(candidate)
                waited.add(candidate.label)
                tried.discard(candidate.label)
                continue

            # Never wait longer on one model than the whole request has left.
            timeout = min(float(settings.ai_request_timeout_seconds), remaining)
            try:
                raw = await self._call(
                    candidate, settings, system_prompt, user_prompt, timeout, images
                )
            except ProviderError as exc:
                tried.add(candidate.label)
                rotation.block(candidate, exc.cooldown_seconds, exc.reason)
                logger.warning(
                    "%s unavailable (%s) — holding it for %.0fs and trying the "
                    "next model. %s",
                    candidate.label,
                    exc.reason,
                    exc.cooldown_seconds,
                    exc,
                )
                continue

            primary = rotation.primary
            if primary is not None and candidate.label != primary.label:
                if require_vision and not primary.supports_vision:
                    logger.info(
                        "Scanned note served by %s — the primary model %s "
                        "cannot read images",
                        candidate.label,
                        primary.label,
                    )
                else:
                    logger.info("Note served by fallback model %s", candidate.label)
            rotation.clear(candidate)
            if models_used is not None:
                models_used.add(candidate.label)
            return raw

    async def _call(
        self,
        candidate: ModelCandidate,
        settings: Settings,
        system_prompt: str,
        user_prompt: str,
        timeout: float,
        images: list[DocumentImage] | None = None,
    ) -> str:
        images = images or []
        if candidate.provider == "gemini":
            return await self._call_gemini(
                settings, candidate.model, system_prompt, user_prompt, timeout, images
            )
        if candidate.provider in OPENAI_COMPATIBLE_ENDPOINTS:
            return await self._call_openai_compatible(
                settings,
                candidate.provider,
                candidate.model,
                system_prompt,
                user_prompt,
                timeout,
                images,
            )
        return await self._call_azure_openai(
            settings, candidate.model, system_prompt, user_prompt, timeout, images
        )

    # ── Providers ──
    # Both translate their own failures into ProviderError so that the rotation
    # above does not have to know one provider's error shapes from another's.

    async def _call_gemini(
        self,
        settings: Settings,
        model: str,
        system_prompt: str,
        user_prompt: str,
        timeout: float,
        images: list[DocumentImage] | None = None,
    ) -> str:
        if not settings.gemini_api_key:
            raise ProviderError(
                "Gemini is not configured. Set GEMINI_API_KEY.",
                cooldown_seconds=CONFIG_ERROR_COOLDOWN_SECONDS,
                reason="not configured",
            )

        url = f"{GEMINI_BASE}/models/{model}:generateContent"
        # The prompt first, then the pages in order: the instructions are what
        # the pages are to be read against, and a model that meets the images
        # first tends to describe them instead of extracting from them.
        parts: list[dict[str, Any]] = [{"text": user_prompt}]
        for image in images or []:
            parts.append(
                {"inline_data": {"mime_type": image.mime_type, "data": image.data}}
            )
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 4096,
                "responseMimeType": "application/json",
            },
        }
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    url,
                    params={"key": settings.gemini_api_key},
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise ProviderError(
                f"Could not reach Gemini: {exc}",
                cooldown_seconds=TRANSIENT_COOLDOWN_SECONDS,
                reason="unreachable",
            ) from exc

        if resp.status_code != 200:
            raise self._gemini_error(settings, model, resp)

        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            # A response that parsed but holds no candidate is usually a safety
            # block on this note. Another model would very likely do the same,
            # so this is not a reason to rotate.
            logger.error("Unexpected Gemini response shape: %.300s", json.dumps(data))
            return "[]"

    def _gemini_error(
        self, settings: Settings, model: str, resp: httpx.Response
    ) -> ProviderError:
        """Classify a non-200 from Gemini into a cooldown."""
        try:
            payload = resp.json()
        except ValueError:
            payload = {}

        message = ""
        error = payload.get("error")
        if isinstance(error, dict):
            message = str(error.get("message", ""))[:200]

        if resp.status_code == 429:
            cooldown, reason = gemini_rate_limit(payload)
            # The configured default wins over our generic one; a deployment
            # that knows its own limits should be able to say so.
            if reason == "rate limited":
                cooldown = float(settings.ai_rate_limit_cooldown_seconds)
            return ProviderError(
                f"Gemini {model} rate limited: {message}",
                cooldown_seconds=cooldown,
                reason=reason,
            )

        if resp.status_code >= 500:
            return ProviderError(
                f"Gemini {model} returned {resp.status_code}: {message}",
                cooldown_seconds=TRANSIENT_COOLDOWN_SECONDS,
                reason=f"provider error {resp.status_code}",
            )

        # 400/401/403/404 — a retired model name, a key without access to it, a
        # malformed request. None of these fix themselves in a minute, and a
        # retired model is exactly how a working demo goes quiet, so say so
        # loudly and take the model out of the chain for the session.
        logger.error(
            "Gemini %s is misconfigured (HTTP %s): %s — removing it from the "
            "chain for this process",
            model,
            resp.status_code,
            message,
        )
        return ProviderError(
            f"Gemini {model} returned {resp.status_code}: {message}",
            cooldown_seconds=CONFIG_ERROR_COOLDOWN_SECONDS,
            reason=f"rejected ({resp.status_code})",
        )

    async def _call_openai_compatible(
        self,
        settings: Settings,
        provider: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        timeout: float,
        images: list[DocumentImage] | None = None,
    ) -> str:
        """Call any provider that speaks OpenAI's /chat/completions.

        Written against httpx rather than the openai package on purpose: the
        package is an optional dependency here, and this needs to work on a
        deployment that never installs it.
        """
        api_key = settings.openai_compatible_key(provider)
        if not api_key:
            raise ProviderError(
                f"{provider} is in the model chain but has no API key.",
                cooldown_seconds=CONFIG_ERROR_COOLDOWN_SECONDS,
                reason="not configured",
            )

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": _openai_user_content(user_prompt, images)},
            ],
            "temperature": 0.0,
            "max_tokens": 4096,
            # The system prompt says "JSON" in as many words, which is what
            # json_object mode requires of the prompt on several of these APIs.
            "response_format": {"type": "json_object"},
        }
        url = f"{OPENAI_COMPATIBLE_ENDPOINTS[provider]}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise ProviderError(
                f"Could not reach {provider}: {exc}",
                cooldown_seconds=TRANSIENT_COOLDOWN_SECONDS,
                reason="unreachable",
            ) from exc

        if resp.status_code != 200:
            raise self._openai_compatible_error(settings, provider, model, resp)

        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"] or "[]"
        except (KeyError, IndexError):
            logger.error(
                "Unexpected %s response shape: %.300s", provider, json.dumps(data)
            )
            return "[]"

    def _openai_compatible_error(
        self, settings: Settings, provider: str, model: str, resp: httpx.Response
    ) -> ProviderError:
        """Classify a non-200 from an OpenAI-compatible provider."""
        message = ""
        try:
            body = resp.json()
        except ValueError:
            body = {}
        error = body.get("error") if isinstance(body, dict) else None
        if isinstance(error, dict):
            message = str(error.get("message", ""))[:200]
        elif isinstance(error, str):
            message = error[:200]
        if not message:
            message = resp.text[:200]

        if resp.status_code == 429:
            cooldown, reason = openai_compatible_rate_limit(
                resp.headers, float(settings.ai_rate_limit_cooldown_seconds)
            )
            return ProviderError(
                f"{provider} {model} rate limited: {message}",
                cooldown_seconds=cooldown,
                reason=reason,
            )

        if resp.status_code >= 500:
            return ProviderError(
                f"{provider} {model} returned {resp.status_code}: {message}",
                cooldown_seconds=TRANSIENT_COOLDOWN_SECONDS,
                reason=f"provider error {resp.status_code}",
            )

        # A decommissioned model name, a key without access, or a model that
        # rejects json_object mode. Each needs a configuration change, so park
        # the candidate and say which one it was.
        logger.error(
            "%s %s is misconfigured (HTTP %s): %s — removing it from the chain "
            "for this process",
            provider,
            model,
            resp.status_code,
            message,
        )
        return ProviderError(
            f"{provider} {model} returned {resp.status_code}: {message}",
            cooldown_seconds=CONFIG_ERROR_COOLDOWN_SECONDS,
            reason=f"rejected ({resp.status_code})",
        )

    def _get_azure_client(self, settings: Settings) -> Any:
        """Create the Azure client on first use.

        Lazy because ``openai`` is an optional dependency: a Gemini-only
        deployment does not install it, and a chain that merely *mentions* a
        fallback should not make the import mandatory.
        """
        if self._azure_client is not None:
            return self._azure_client
        if not (settings.azure_openai_endpoint and settings.azure_openai_api_key):
            raise ProviderError(
                "Azure OpenAI is not configured. "
                "Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY.",
                cooldown_seconds=CONFIG_ERROR_COOLDOWN_SECONDS,
                reason="not configured",
            )
        try:
            from openai import AsyncAzureOpenAI
        except ImportError as exc:
            raise ProviderError(
                "Azure OpenAI is in the model chain but the openai package is "
                "not installed (uncomment it in requirements.txt).",
                cooldown_seconds=CONFIG_ERROR_COOLDOWN_SECONDS,
                reason="openai package missing",
            ) from exc

        ExtractionService._azure_client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        return ExtractionService._azure_client

    async def _call_azure_openai(
        self,
        settings: Settings,
        deployment: str,
        system_prompt: str,
        user_prompt: str,
        timeout: float,
        images: list[DocumentImage] | None = None,
    ) -> str:
        client = self._get_azure_client(settings)
        try:
            response = await client.chat.completions.create(
                model=deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": _openai_user_content(user_prompt, images),
                    },
                ],
                temperature=0.0,
                max_tokens=4096,
                response_format={"type": "json_object"},
                timeout=timeout,
            )
        except Exception as exc:  # noqa: BLE001 — classified below, then re-raised
            raise self._azure_error(settings, deployment, exc) from exc
        return response.choices[0].message.content or "[]"

    def _azure_error(
        self, settings: Settings, deployment: str, exc: Exception
    ) -> ProviderError:
        """Classify an openai SDK exception without importing the SDK.

        Duck-typed on purpose: the package is optional, so this code has to be
        importable — and testable — on a deployment that never installs it.
        """
        status_code = getattr(exc, "status_code", None)
        headers = getattr(getattr(exc, "response", None), "headers", None)

        if status_code == 429:
            cooldown = retry_after_seconds(headers)
            return ProviderError(
                f"Azure OpenAI {deployment} rate limited: {exc}",
                cooldown_seconds=(
                    cooldown
                    if cooldown is not None
                    else float(settings.ai_rate_limit_cooldown_seconds)
                ),
                reason="rate limited",
            )
        if status_code is not None and status_code >= 500:
            return ProviderError(
                f"Azure OpenAI {deployment} returned {status_code}: {exc}",
                cooldown_seconds=TRANSIENT_COOLDOWN_SECONDS,
                reason=f"provider error {status_code}",
            )
        if status_code is not None:
            return ProviderError(
                f"Azure OpenAI {deployment} returned {status_code}: {exc}",
                cooldown_seconds=CONFIG_ERROR_COOLDOWN_SECONDS,
                reason=f"rejected ({status_code})",
            )
        # A timeout or a dropped connection carries no status code.
        return ProviderError(
            f"Azure OpenAI {deployment} call failed: {exc}",
            cooldown_seconds=TRANSIENT_COOLDOWN_SECONDS,
            reason="unreachable",
        )
