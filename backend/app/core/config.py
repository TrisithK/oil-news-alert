"""Application settings, loaded from environment / .env via pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Database ---
    database_url: str = "postgresql+psycopg://app:app@localhost:5432/oilalert"

    # --- LLM (Anthropic) — pin exact dated version strings ---
    anthropic_api_key: str | None = None
    triage_model: str = "claude-haiku-4-5-20251001"
    extract_model: str = "claude-sonnet-4-6"
    opus_model: str = "claude-opus-4-8"

    # --- External data feeds ---
    eia_api_key: str | None = None
    newsdata_api_key: str | None = None

    # --- Alert delivery ---
    telegram_bot_token: str | None = None
    telegram_default_chat_id: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_pass: str | None = None
    alert_from_email: str | None = None

    # --- API ---
    api_bearer_token: str = "devtoken"

    # --- Worker / scheduler ---
    ingest_interval_sec: int = 600
    max_items_per_cycle: int = 50

    # --- Alerting ---
    alert_cooldown_sec: int = 1800  # event-level dedup window (spec §7)

    # --- Logging ---
    log_level: str = "INFO"


settings = Settings()
