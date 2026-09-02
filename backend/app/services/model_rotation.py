"""Rotation across AI models when one runs out of quota.

Extraction sends one request per note, so a batch of twenty notes costs twenty
requests against a free-tier quota that is counted *per model, per day*. The
first 429 therefore does not mean "slow down" — it usually means this model is
finished until the quota resets, and nineteen more requests to it will fail
exactly as fast.

So the service holds a chain of candidates rather than a single model, and this
module decides which one to use. A candidate that fails is put in a cooldown
that the next note sees too: one 429 costs one request, not one per note. The
cooldown length comes from the provider's own answer where it gives one —
Google returns both a RetryInfo delay and, in a QuotaFailure violation, whether
the quota that was hit is per-minute or per-day, and those want very different
responses (wait twenty seconds, versus don't come back until tomorrow).

State is per process and in memory. With two uvicorn workers each learns the
limits separately, which costs one wasted request per worker per model — not
worth a shared store, and a restart deliberately forgets everything.
"""

from __future__ import annotations

import datetime as dt
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable

logger = logging.getLogger("mediextract.services.rotation")

# Used when a provider says only "429" and offers no delay of its own.
DEFAULT_COOLDOWN_SECONDS = 60.0

# A 5xx or a dropped connection is not a quota problem: hold the candidate back
# long enough to get past a blip, not long enough to lose it for the session.
TRANSIENT_COOLDOWN_SECONDS = 20.0

# A model that does not exist, or a key that is refused, will not start working
# in the next few minutes. Park it for the session and carry on down the chain.
CONFIG_ERROR_COOLDOWN_SECONDS = 24 * 3600.0

# Added to a provider-supplied delay: coming back the same second it named is
# how you spend a second request to learn the same thing.
RETRY_DELAY_BUFFER_SECONDS = 2.0

# Google's free-tier daily quotas reset at midnight Pacific.
QUOTA_RESET_TZ = "America/Los_Angeles"
QUOTA_RESET_FALLBACK_SECONDS = 4 * 3600.0

# Providers that speak OpenAI's /chat/completions, which by now is most of
# them. One adapter covers the lot, so adding another is this line plus an API
# key setting — no new request-building or response-parsing code.
OPENAI_COMPATIBLE_ENDPOINTS = {
    "groq": "https://api.groq.com/openai/v1",
    "mistral": "https://api.mistral.ai/v1",
}

PROVIDERS = ("gemini", "azure_openai", *OPENAI_COMPATIBLE_ENDPOINTS)


@dataclass(frozen=True)
class ModelCandidate:
    """One provider/model pair the extractor may use."""

    provider: str
    model: str

    @property
    def label(self) -> str:
        return f"{self.provider}:{self.model}"


class ProviderError(RuntimeError):
    """A call failed in a way that should move the work to the next candidate.

    ``cooldown_seconds`` is how long this candidate should be left alone, and
    ``reason`` is what to tell a human looking at the status endpoint later.
    """

    def __init__(
        self,
        message: str,
        *,
        cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
        reason: str = "unavailable",
    ) -> None:
        super().__init__(message)
        self.cooldown_seconds = cooldown_seconds
        self.reason = reason


# ── Building the chain ──────────────────────────────────────────────────────

def parse_chain(
    primary: ModelCandidate,
    fallbacks: str,
    default_provider: str,
    is_configured: Callable[[str], bool],
) -> list[ModelCandidate]:
    """Turn the configured primary and fallback list into an ordered chain.

    Fallbacks are ``provider:model`` pairs, or a bare model name meaning the
    default provider. Candidates whose provider has no credentials are dropped
    rather than left in to fail: the shipped defaults name Gemini fallbacks, and
    a deployment running on Azure should not have to blank them out to avoid a
    chain full of models it cannot call.
    """
    chain: list[ModelCandidate] = []
    seen: set[str] = set()

    for candidate in [primary, *_parse_fallbacks(fallbacks, default_provider)]:
        if candidate.label in seen:
            continue
        if not candidate.model:
            continue
        if candidate.provider not in PROVIDERS:
            logger.warning("Ignoring fallback with unknown provider: %s", candidate.label)
            continue
        if not is_configured(candidate.provider):
            logger.info(
                "Skipping %s — no credentials configured for that provider",
                candidate.label,
            )
            continue
        seen.add(candidate.label)
        chain.append(candidate)

    return chain


def _parse_fallbacks(raw: str, default_provider: str) -> Iterable[ModelCandidate]:
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if ":" in entry:
            provider, _, model = entry.partition(":")
            yield ModelCandidate(provider.strip(), model.strip())
        else:
            yield ModelCandidate(default_provider, entry)


# ── Reading the provider's own answer ───────────────────────────────────────

def _seconds_until_quota_reset() -> float:
    """Seconds until midnight in the zone Google resets daily quotas in."""
    try:
        from zoneinfo import ZoneInfo

        now = dt.datetime.now(ZoneInfo(QUOTA_RESET_TZ))
        tomorrow = (now + dt.timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return max((tomorrow - now).total_seconds(), 60.0)
    except Exception:  # no tzdata in the image — a fixed hold is close enough
        return QUOTA_RESET_FALLBACK_SECONDS


def _parse_duration(value: Any) -> float | None:
    """Parse a protobuf duration string such as "27s" or "1.5s"."""
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)s\s*", value)
    return float(match.group(1)) if match else None


def gemini_rate_limit(payload: dict[str, Any]) -> tuple[float, str]:
    """Work out how long to hold a Gemini model back after a 429.

    The surface message ("you exceeded your current quota") is the same whether
    a per-minute or a per-day limit was hit, and the two need opposite
    responses. The ``violations`` carry the actual quota id, which names which
    one it was — that is the only reliable signal in the response.
    """
    details = []
    error = payload.get("error")
    if isinstance(error, dict) and isinstance(error.get("details"), list):
        details = error["details"]

    retry_delay: float | None = None
    daily = False

    for detail in details:
        if not isinstance(detail, dict):
            continue
        delay = _parse_duration(detail.get("retryDelay"))
        if delay is not None:
            retry_delay = delay
        for violation in detail.get("violations") or []:
            if not isinstance(violation, dict):
                continue
            quota_id = str(violation.get("quotaId", ""))
            if "PerDay" in quota_id:
                daily = True

    if daily:
        # A per-day quota is spent. The RetryInfo delay that comes back with it
        # is a handful of seconds and retrying then just burns another request.
        return _seconds_until_quota_reset(), "daily quota exhausted"
    if retry_delay is not None:
        return retry_delay + RETRY_DELAY_BUFFER_SECONDS, "per-minute rate limit"
    return DEFAULT_COOLDOWN_SECONDS, "rate limited"


def parse_reset_duration(value: Any) -> float | None:
    """Parse the durations these APIs put in their rate-limit headers.

    Groq answers in shapes like "2m59.56s" and "7.66s"; others send a plain
    number of seconds. Anything else is not worth guessing at.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        pass

    match = re.fullmatch(
        r"(?:(\d+(?:\.\d+)?)h)?(?:(\d+(?:\.\d+)?)m)?(?:(\d+(?:\.\d+)?)s)?",
        text,
    )
    if not match or not any(match.groups()):
        return None
    hours, minutes, seconds = (float(g) if g else 0.0 for g in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def openai_compatible_rate_limit(
    headers: Any, default_seconds: float
) -> tuple[float, str]:
    """How long to hold back an OpenAI-compatible provider after a 429.

    Retry-After is the standard answer; Groq also exposes when each bucket
    refills, and its daily bucket is the one that matters here — a reset an
    hour or more away is a daily allowance, not a burst limit, and calling it
    what it is keeps the "wait it out or give up" decision honest.
    """
    delay = retry_after_seconds(headers)
    if delay is None:
        try:
            delay = parse_reset_duration(headers.get("x-ratelimit-reset-requests"))
        except AttributeError:
            delay = None

    if delay is None:
        return default_seconds, "rate limited"
    delay += RETRY_DELAY_BUFFER_SECONDS
    if delay >= 3600:
        return delay, "daily quota exhausted"
    return delay, "per-minute rate limit"


def retry_after_seconds(headers: Any) -> float | None:
    """Read a Retry-After header, which OpenAI-compatible APIs send on a 429."""
    try:
        raw = headers.get("retry-after")
    except AttributeError:
        return None
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


# ── The rotation itself ─────────────────────────────────────────────────────

@dataclass
class _Cooldown:
    until: float  # time.monotonic()
    reason: str
    started_wall: dt.datetime


class ModelRotation:
    """Which candidate to try next, and which ones are still in the doghouse."""

    def __init__(self, candidates: list[ModelCandidate]) -> None:
        self._candidates = list(candidates)
        self._blocked: dict[str, _Cooldown] = {}

    @property
    def candidates(self) -> list[ModelCandidate]:
        return list(self._candidates)

    @property
    def primary(self) -> ModelCandidate | None:
        return self._candidates[0] if self._candidates else None

    def next_available(self, skip: set[str] | None = None) -> ModelCandidate | None:
        """The first candidate in preference order that is usable right now."""
        skip = skip or set()
        now = time.monotonic()
        for candidate in self._candidates:
            if candidate.label in skip:
                continue
            cooldown = self._blocked.get(candidate.label)
            if cooldown is not None and cooldown.until > now:
                continue
            return candidate
        return None

    def soonest(self, skip: set[str] | None = None) -> tuple[ModelCandidate | None, float]:
        """The candidate that frees up first, and how long that is."""
        skip = skip or set()
        now = time.monotonic()
        best: tuple[ModelCandidate | None, float] = (None, 0.0)
        for candidate in self._candidates:
            if candidate.label in skip:
                continue
            cooldown = self._blocked.get(candidate.label)
            wait = max(cooldown.until - now, 0.0) if cooldown else 0.0
            if best[0] is None or wait < best[1]:
                best = (candidate, wait)
        return best

    def block(self, candidate: ModelCandidate, seconds: float, reason: str) -> None:
        self._blocked[candidate.label] = _Cooldown(
            until=time.monotonic() + seconds,
            reason=reason,
            started_wall=dt.datetime.now(dt.timezone.utc),
        )

    def clear(self, candidate: ModelCandidate) -> None:
        """Forget a cooldown — a candidate that just answered is fine again."""
        self._blocked.pop(candidate.label, None)

    def status(self) -> list[dict[str, Any]]:
        """Per-candidate availability, for the status endpoint and the logs."""
        now = time.monotonic()
        rows: list[dict[str, Any]] = []
        for index, candidate in enumerate(self._candidates):
            cooldown = self._blocked.get(candidate.label)
            waiting = cooldown is not None and cooldown.until > now
            rows.append(
                {
                    "provider": candidate.provider,
                    "model": candidate.model,
                    "is_primary": index == 0,
                    "available": not waiting,
                    "available_in_seconds": (
                        round(cooldown.until - now, 1) if waiting else None
                    ),
                    "reason": cooldown.reason if waiting else None,
                    "blocked_since": (
                        cooldown.started_wall.isoformat(timespec="seconds")
                        if waiting
                        else None
                    ),
                }
            )
        return rows

    def describe_waits(self) -> str:
        """A one-line summary for the error raised when nothing is usable."""
        now = time.monotonic()
        parts = []
        for candidate in self._candidates:
            cooldown = self._blocked.get(candidate.label)
            wait = max(cooldown.until - now, 0.0) if cooldown else 0.0
            reason = cooldown.reason if cooldown else "failed"
            parts.append(f"{candidate.label} ({reason}, {int(wait)}s)")
        return "; ".join(parts) if parts else "no models configured"
