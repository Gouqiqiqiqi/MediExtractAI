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
    gemini_model: str = "gemini-2.5-flash"

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
    notes_database_url: str = ""

    # ── Derived ──
    @property
    def notes_db_url(self) -> str:
        """Connection string for the source notes database."""
        return self.notes_database_url or self.database_url

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
