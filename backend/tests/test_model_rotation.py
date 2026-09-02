"""Tests for rotating away from a rate-limited AI model.

The behaviour these protect is the one that only shows up on a spent quota,
which is exactly when nobody wants to be debugging it: a 429 must cost one
request, not one per note, and the chain must keep going.
"""

from __future__ import annotations

import httpx
import pytest

from app.config import Settings
from app.models.schemas import ColumnDefinition
from app.services import model_rotation as mr
from app.services.extraction_service import ExtractionService


def make_settings(**overrides) -> Settings:
    base = {
        "ai_provider": "gemini",
        "gemini_api_key": "test-key",
        "gemini_model": "model-a",
        "ai_fallback_models": "model-b,model-c",
        "groq_api_key": "",
        "mistral_api_key": "",
    }
    base.update(overrides)
    return Settings(**base)


# ── Building the chain ──────────────────────────────────────────────────────

def test_chain_is_primary_then_fallbacks_in_order():
    settings = make_settings()
    chain = mr.parse_chain(
        primary=mr.ModelCandidate("gemini", settings.ai_primary_model),
        fallbacks=settings.ai_fallback_models,
        default_provider="gemini",
        is_configured=lambda p: p == "gemini",
    )
    assert [c.label for c in chain] == [
        "gemini:model-a",
        "gemini:model-b",
        "gemini:model-c",
    ]


def test_chain_drops_duplicates_and_unconfigured_providers():
    chain = mr.parse_chain(
        primary=mr.ModelCandidate("gemini", "model-a"),
        fallbacks="model-a, azure_openai:gpt-4o, model-b, nonsense:x",
        default_provider="gemini",
        is_configured=lambda p: p == "gemini",
    )
    # model-a is already the primary; the Azure entry has no credentials, and
    # a deployment on Gemini should not have to blank the shipped defaults out.
    assert [c.label for c in chain] == ["gemini:model-a", "gemini:model-b"]


# ── Reading the provider's own answer ───────────────────────────────────────

def test_per_minute_limit_uses_the_delay_google_gives():
    cooldown, reason = mr.gemini_rate_limit(
        {
            "error": {
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                        "violations": [
                            {"quotaId": "GenerateRequestsPerMinutePerProjectPerModel"}
                        ],
                    },
                    {
                        "@type": "type.googleapis.com/google.rpc.RetryInfo",
                        "retryDelay": "27s",
                    },
                ]
            }
        }
    )
    assert reason == "per-minute rate limit"
    assert 27 <= cooldown <= 27 + mr.RETRY_DELAY_BUFFER_SECONDS


def test_daily_quota_outranks_the_retry_delay():
    """The delay sent with a spent daily quota is seconds, and it is a trap.

    Retrying then just spends another request on the same answer, so the daily
    violation has to win over the RetryInfo that travels beside it.
    """
    cooldown, reason = mr.gemini_rate_limit(
        {
            "error": {
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                        "violations": [
                            {
                                "quotaId": (
                                    "GenerateRequestsPerDayPerProjectPerModel-FreeTier"
                                )
                            }
                        ],
                    },
                    {"retryDelay": "31s"},
                ]
            }
        }
    )
    assert reason == "daily quota exhausted"
    assert cooldown > 3600


def test_unparseable_429_falls_back_to_a_plain_cooldown():
    cooldown, reason = mr.gemini_rate_limit({"error": {"message": "quota exceeded"}})
    assert reason == "rate limited"
    assert cooldown == mr.DEFAULT_COOLDOWN_SECONDS


def test_reset_durations_are_parsed_in_the_shapes_these_apis_use():
    assert mr.parse_reset_duration("7.66s") == pytest.approx(7.66)
    assert mr.parse_reset_duration("2m59.56s") == pytest.approx(179.56)
    assert mr.parse_reset_duration("1h30m") == pytest.approx(5400)
    assert mr.parse_reset_duration("60") == 60
    assert mr.parse_reset_duration("soon") is None
    assert mr.parse_reset_duration(None) is None


def test_openai_compatible_429_prefers_retry_after():
    cooldown, reason = mr.openai_compatible_rate_limit(
        httpx.Headers({"retry-after": "12"}), default_seconds=60
    )
    assert reason == "per-minute rate limit"
    assert cooldown == pytest.approx(12 + mr.RETRY_DELAY_BUFFER_SECONDS)


def test_openai_compatible_daily_bucket_is_named_as_such():
    """A reset hours away is a daily allowance, not a burst limit.

    The distinction is what decides whether the request waits or gives up, so
    it has to survive the trip from Groq's header to the rotation.
    """
    cooldown, reason = mr.openai_compatible_rate_limit(
        httpx.Headers({"x-ratelimit-reset-requests": "3h12m10s"}), default_seconds=60
    )
    assert reason == "daily quota exhausted"
    assert cooldown > 3600


def test_openai_compatible_429_without_headers_uses_the_configured_default():
    cooldown, reason = mr.openai_compatible_rate_limit(
        httpx.Headers({}), default_seconds=45
    )
    assert (cooldown, reason) == (45, "rate limited")


# ── The rotation ────────────────────────────────────────────────────────────

def test_blocked_candidate_is_skipped_until_its_cooldown_expires():
    a, b = mr.ModelCandidate("gemini", "a"), mr.ModelCandidate("gemini", "b")
    rotation = mr.ModelRotation([a, b])

    assert rotation.next_available() == a
    rotation.block(a, 60, "daily quota exhausted")
    assert rotation.next_available() == b

    # Expired cooldowns are not sticky.
    rotation.block(a, -1, "over")
    assert rotation.next_available() == a


def test_status_reports_why_and_for_how_long():
    a, b = mr.ModelCandidate("gemini", "a"), mr.ModelCandidate("gemini", "b")
    rotation = mr.ModelRotation([a, b])
    rotation.block(a, 120, "daily quota exhausted")

    status = {row["model"]: row for row in rotation.status()}
    assert status["a"]["available"] is False
    assert status["a"]["is_primary"] is True
    assert status["a"]["reason"] == "daily quota exhausted"
    assert 0 < status["a"]["available_in_seconds"] <= 120
    assert status["b"]["available"] is True
    assert status["b"]["available_in_seconds"] is None


# ── End to end through the service ──────────────────────────────────────────

def gemini_429(daily: bool) -> httpx.Response:
    quota_id = (
        "GenerateRequestsPerDayPerProjectPerModel-FreeTier"
        if daily
        else "GenerateRequestsPerMinutePerProjectPerModel"
    )
    return httpx.Response(
        429,
        json={
            "error": {
                "code": 429,
                "message": "You exceeded your current quota.",
                "details": [
                    {"violations": [{"quotaId": quota_id}]},
                    {"retryDelay": "5s"},
                ],
            }
        },
        request=httpx.Request("POST", "https://example.invalid"),
    )


ANSWER = '[{"Diagnosis": "heart failure"}]'


class FakeLLM:
    """Stands in for every HTTP provider: named models fail, the rest answer.

    One fake for both request shapes on purpose — Gemini names the model in the
    URL and answers with ``candidates``, the OpenAI-compatible providers put it
    in the body and answer with ``choices``, and the tests that matter here are
    the ones that cross from one to the other.

    ``once`` makes a failure transient — the model fails its first call and
    answers afterwards, which is what a per-minute limit looks like.
    """

    def __init__(self, failing: dict[str, httpx.Response], once: bool = False) -> None:
        self.failing = dict(failing)
        self.once = once
        self.calls: list[str] = []

    async def post(self, url, *, params=None, headers=None, json=None):  # noqa: A002
        gemini = "/models/" in url
        model = url.split("/models/")[1].split(":")[0] if gemini else json["model"]
        self.calls.append(model)

        if model in self.failing:
            response = self.failing[model]
            if self.once:
                del self.failing[model]
            return response

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


@pytest.fixture
def fake_gemini(monkeypatch):
    """Point the extraction service at a fake provider and a fresh rotation."""

    def install(
        failing: dict[str, httpx.Response], once: bool = False, **settings
    ) -> FakeLLM:
        fake = FakeLLM(failing, once=once)
        monkeypatch.setattr(
            "app.services.extraction_service.httpx.AsyncClient",
            lambda *a, **k: fake,
        )
        ExtractionService.initialize(make_settings(**settings))
        return fake

    yield install
    ExtractionService.shutdown()


COLUMNS = [ColumnDefinition(name="Diagnosis", description="Primary diagnosis")]


@pytest.mark.anyio
async def test_rate_limited_model_falls_through_to_the_next(fake_gemini):
    fake = fake_gemini({"model-a": gemini_429(daily=True)})

    rows = await ExtractionService.instance().extract(["note text"], COLUMNS)

    assert rows == [{"Diagnosis": "heart failure"}]
    assert fake.calls == ["model-a", "model-b"]


@pytest.mark.anyio
async def test_exhausted_model_is_not_retried_for_every_note(fake_gemini):
    """The point of the shared cooldown: one 429, not one per note."""
    fake = fake_gemini({"model-a": gemini_429(daily=True)})

    rows = await ExtractionService.instance().extract(["one", "two", "three"], COLUMNS)

    assert len(rows) == 3
    assert fake.calls.count("model-a") == 1
    assert fake.calls.count("model-b") == 3


@pytest.mark.anyio
async def test_a_retired_model_is_dropped_rather_than_retried(fake_gemini):
    """A 404 is how a demo goes quiet: the model name was retired."""
    gone = httpx.Response(
        404,
        json={"error": {"code": 404, "message": "models/model-a is not found"}},
        request=httpx.Request("POST", "https://example.invalid"),
    )
    fake = fake_gemini({"model-a": gone})

    rows = await ExtractionService.instance().extract(["one", "two"], COLUMNS)

    assert len(rows) == 2
    assert fake.calls.count("model-a") == 1
    status = {row["model"]: row for row in ExtractionService.instance().model_status()}
    assert status["model-a"]["reason"] == "rejected (404)"


@pytest.mark.anyio
async def test_everything_rate_limited_reports_which_and_for_how_long(fake_gemini):
    fake = fake_gemini(
        {
            "model-a": gemini_429(daily=True),
            "model-b": gemini_429(daily=True),
            "model-c": gemini_429(daily=True),
        }
    )

    with pytest.raises(RuntimeError) as excinfo:
        await ExtractionService.instance().extract(["note"], COLUMNS)

    message = str(excinfo.value)
    assert "daily quota exhausted" in message
    assert "model-c" in message
    # Every model tried exactly once, and no waiting around for a daily quota.
    assert sorted(fake.calls) == ["model-a", "model-b", "model-c"]


@pytest.mark.anyio
async def test_short_per_minute_limit_is_waited_out_when_nothing_else_is_free(
    fake_gemini, monkeypatch
):
    """One model and a per-minute limit: there is nowhere to rotate to.

    Failing straight away would be wrong — the limit expires in seconds — so
    the request waits it out once, and only once.
    """
    slept: list[float] = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr("app.services.extraction_service.asyncio.sleep", fake_sleep)

    fake = fake_gemini(
        {"model-a": gemini_429(daily=False)}, once=True, ai_fallback_models=""
    )

    rows = await ExtractionService.instance().extract(["note"], COLUMNS)

    assert rows == [{"Diagnosis": "heart failure"}]
    assert fake.calls == ["model-a", "model-a"]
    assert slept and slept[0] <= 5 + mr.RETRY_DELAY_BUFFER_SECONDS


@pytest.mark.anyio
async def test_a_daily_quota_is_not_waited_out(fake_gemini, monkeypatch):
    """The counterpart: hours of waiting is a 503, not a held-open request."""
    monkeypatch.setattr(
        "app.services.extraction_service.asyncio.sleep",
        lambda seconds: pytest.fail("should not wait out a daily quota"),
    )
    fake_gemini({"model-a": gemini_429(daily=True)}, ai_fallback_models="")

    with pytest.raises(RuntimeError, match="rate limited"):
        await ExtractionService.instance().extract(["note"], COLUMNS)


# ── Across providers ────────────────────────────────────────────────────────

def openai_429(headers: dict[str, str]) -> httpx.Response:
    return httpx.Response(
        429,
        json={"error": {"message": "Rate limit reached for model"}},
        headers=headers,
        request=httpx.Request("POST", "https://example.invalid"),
    )


@pytest.mark.anyio
async def test_gemini_falls_through_to_groq(fake_gemini):
    """The reason for a second provider: a spent Google quota is not the end."""
    fake = fake_gemini(
        {"model-a": gemini_429(daily=True)},
        ai_fallback_models="groq:openai/gpt-oss-120b",
        groq_api_key="groq-key",
    )

    rows = await ExtractionService.instance().extract(["note"], COLUMNS)

    assert rows == [{"Diagnosis": "heart failure"}]
    assert fake.calls == ["model-a", "openai/gpt-oss-120b"]


@pytest.mark.anyio
async def test_rotation_crosses_providers_in_both_directions(fake_gemini):
    fake = fake_gemini(
        {
            "model-a": gemini_429(daily=True),
            "openai/gpt-oss-120b": openai_429({"x-ratelimit-reset-requests": "4h"}),
        },
        ai_fallback_models=(
            "groq:openai/gpt-oss-120b,mistral:mistral-small-latest"
        ),
        groq_api_key="groq-key",
        mistral_api_key="mistral-key",
    )

    rows = await ExtractionService.instance().extract(["one", "two"], COLUMNS)

    assert len(rows) == 2
    # Each dead model costs one request in total, not one per note.
    assert fake.calls.count("model-a") == 1
    assert fake.calls.count("openai/gpt-oss-120b") == 1
    assert fake.calls.count("mistral-small-latest") == 2

    status = {row["model"]: row for row in ExtractionService.instance().model_status()}
    assert status["openai/gpt-oss-120b"]["reason"] == "daily quota exhausted"
    assert status["mistral-small-latest"]["available"] is True


@pytest.mark.anyio
async def test_a_provider_without_a_key_never_enters_the_chain(fake_gemini):
    """The shipped defaults name Groq and Mistral; an unset key must be inert."""
    fake_gemini({}, ai_fallback_models="groq:openai/gpt-oss-120b")

    chain = ExtractionService.instance().model_status()

    assert [m["model"] for m in chain] == ["model-a"]
    assert fake_gemini is not None
