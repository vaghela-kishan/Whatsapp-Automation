"""Application configuration.

All settings are loaded from environment variables (optionally via a ``.env``
file) and validated once at startup. Import the singleton ``settings`` object
anywhere in the app; never read ``os.environ`` directly.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Annotated, Any, Literal

from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings sourced from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Application -------------------------------------------------------
    PROJECT_NAME: str = "AI Support Platform"
    VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "staging", "production", "test"] = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- Business / branding ----------------------------------------------
    # Persona the AI assistant speaks as when replying to customers.
    BUSINESS_NAME: str = "WhatsApp Customer Service"
    BUSINESS_TAGLINE: str = "Premium lifestyle & electronics"
    SUPPORT_HOURS: str = "Mon–Sat, 9am–8pm IST"
    ASSISTANT_NAME: str = "Ava"

    # --- AI provider ------------------------------------------------------
    # AI_PROVIDER selects the reply engine: "gemini" (real) or "mock"
    # (rule-based, no API key needed — the app runs fully offline in demo).
    AI_PROVIDER: Literal["gemini", "mock"] = "mock"
    GEMINI_API_KEY: str = ""
    # A stable alias that always maps to the current Flash model (so it never
    # 404s when a specific version is retired). Each model has its own daily
    # free-tier quota (~20/day on this project — raise it by enabling billing).
    GEMINI_MODEL: str = "gemini-flash-latest"
    AI_MAX_OUTPUT_TOKENS: int = 500
    AI_TEMPERATURE: float = 0.4

    # --- WhatsApp provider ------------------------------------------------
    # WHATSAPP_PROVIDER selects the transport: "mock" (in-app simulator,
    # no credentials) or "meta" (WhatsApp Cloud API — fill the fields below).
    WHATSAPP_PROVIDER: Literal["mock", "meta"] = "mock"
    WHATSAPP_VERIFY_TOKEN: str = "dev-verify-token"
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_API_VERSION: str = "v21.0"
    # Meta App Secret — used to verify the X-Hub-Signature-256 header on inbound
    # webhooks. If set, unsigned/forged requests are rejected. Leave empty in
    # demo mode to skip verification.
    WHATSAPP_APP_SECRET: str = ""

    # --- Demo seeding -----------------------------------------------------
    # On startup, create tables and load sample customers/orders/FAQs if the
    # database is empty. Perfect for the demo; disable in production.
    SEED_ON_STARTUP: bool = True

    # --- Proactive automation --------------------------------------------
    # A background worker advances in-progress orders (confirmed → packed →
    # shipped → out for delivery → delivered) and proactively notifies the
    # customer on WhatsApp — no one has to ask. Demo of event-driven automation.
    AUTOMATION_ENABLED: bool = True
    AUTOMATION_INTERVAL_SECONDS: int = 30
    AUTOMATION_BATCH: int = 2

    # --- Security ---------------------------------------------------------
    SECRET_KEY: str = "CHANGE_ME_use_a_long_random_value_in_env"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # a working day
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    JWT_ALGORITHM: str = "HS256"

    # Single admin who can sign in to the dashboard. Override BOTH in .env for
    # any real deployment — the defaults are for local demo convenience only.
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"

    # --- Database ---------------------------------------------------------
    # SQLite for local dev today; swap to Postgres by changing this one value:
    #   postgresql+psycopg://user:pass@host:5432/dbname
    DATABASE_URL: str = "sqlite:///./dev.db"
    SQL_ECHO: bool = False

    # --- CORS -------------------------------------------------------------
    # Accepts a comma-separated string or a JSON array in the environment.
    BACKEND_CORS_ORIGINS: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # --- Logging ----------------------------------------------------------
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _assemble_cors_origins(cls, value: Any) -> list[str]:
        """Allow both ``a,b,c`` and ``["a","b"]`` forms from env vars."""
        if value is None or value == "":
            return []
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                return json.loads(stripped)
            return [item.strip() for item in stripped.split(",") if item.strip()]
        if isinstance(value, (list, tuple)):
            return list(value)
        raise ValueError("BACKEND_CORS_ORIGINS must be a list or a comma-separated string")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings singleton (instantiated on first call)."""
    return Settings()


settings: Settings = get_settings()
