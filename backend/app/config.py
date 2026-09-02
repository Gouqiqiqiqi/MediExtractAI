"""Application configuration — loaded from environment variables / .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration sourced from .env / environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──
    app_env: Literal["development", "staging", "production"] = "development"
    app_secret_key: str = "change-me"
    cors_origins: str = "http://localhost:5173"
    max_upload_size_mb: int = 10
    log_level: str = "INFO"

    # ── Auth ──
    # demo_mode=True disables authentication entirely and serves a demo user.
    # Intended for portfolio / evaluation deployments with synthetic data only.
    demo_mode: bool = True

    # ── AI provider ──
    ai_provider: Literal["gemini", "azure_openai"] = "gemini"

    # Google Gemini (free tier available — https://aistudio.google.com/apikey)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"

    # Models to fall back to, in order, when the one above is rate limited.
    # "provider:model", or a bare model name meaning AI_PROVIDER's provider.
    # Free-tier request quotas are counted per model and per day, so a second
    # model is a second quota — which is the whole point of the chain. Entries
    # whose provider has no credentials configured are dropped at startup.
    ai_fallback_models: str = "gemini-3.1-flash-lite,gemini-2.5-flash"

    # How long a model is left alone after a 429 that carried no delay of its
    # own. Providers that do say (Google's RetryInfo, a Retry-After header) are
    # believed instead, and an exhausted per-day quota is held until it resets.
    ai_rate_limit_cooldown_seconds: int = 60

    # When every model in the chain is cooling down, wait this long for the
    # first one to free up before failing the request. Longer than this and the
    # honest answer is a 503 — an HTTP request should not sit open for minutes.
    ai_max_wait_seconds: int = 30

    # Azure OpenAI (optional alternative)
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-12-01-preview"

    # ── Azure AD / OIDC (only used when demo_mode=False) ──
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""
    azure_authority: str = ""

    # ── Database (application metadata) ──
    # Audit log, extraction jobs, saved schemas. Defaults to a local SQLite file
    # so the app runs with zero external services.
    database_url: str = "sqlite+aiosqlite:///./data/mediextract.db"

    # ── Source notes database (the customer's system) ──
    # In a real deployment the clinical notes live in a system we do not own —
    # a hospital SQL Server, a data-warehouse Postgres — and we get read-only
    # credentials to it. Keeping it separate from database_url means the app's
    # own metadata never has to live inside the customer's estate.
    # Falls back to database_url when unset (single-database dev setups).
    # On first start this is registered as the default data source; after that
    # data sources are managed through the API and this is only a bootstrap.
    notes_database_url: str = ""

    # Hosts a demo deployment may connect a data source to. Demo mode has no
    # authentication, so an unrestricted connection form would turn a public
    # page into an SSRF primitive. Ignored entirely when demo_mode is False.
    demo_allowed_db_hosts: str = "notes-db,localhost,127.0.0.1"

    # ── Derived ──
    @property
    def notes_db_url(self) -> str:
        """Bootstrap connection string for the source notes database."""
        return self.notes_database_url or self.database_url

    @property
    def demo_allowed_db_host_list(self) -> list[str]:
        return [
            h.strip().lower()
            for h in self.demo_allowed_db_hosts.split(",")
            if h.strip()
        ]

    @property
    def ai_provider_configured(self) -> dict[str, bool]:
        """Which providers have enough configuration to be called at all."""
        return {
            "gemini": bool(self.gemini_api_key),
            "azure_openai": bool(
                self.azure_openai_endpoint and self.azure_openai_api_key
            ),
        }

    @property
    def ai_primary_model(self) -> str:
        """The model name AI_PROVIDER's own setting points at."""
        if self.ai_provider == "azure_openai":
            return self.azure_openai_deployment
        return self.gemini_model

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @field_validator("app_secret_key")
    @classmethod
    def warn_default_secret(cls, v: str) -> str:
        if v == "change-me":
            import warnings
            warnings.warn(
                "APP_SECRET_KEY is set to default — change it in production!",
                stacklevel=2,
            )
        return v

    def ensure_data_dir(self) -> None:
        """Create the local data directory used by the SQLite default."""
        if self.database_url.startswith("sqlite"):
            Path("./data").mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Cached singleton settings instance."""
    return Settings()
