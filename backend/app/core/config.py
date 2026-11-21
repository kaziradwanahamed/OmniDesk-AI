"""Application configuration via environment variables (Pydantic Settings)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings.

    Values are loaded from environment variables (and an optional local
    ``.env`` file). Unknown variables are ignored (``extra="ignore"``).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Runtime ---
    app_env: str = "development"
    log_level: str = "INFO"

    # --- Database (async SQLAlchemy URL) ---
    database_url: str

    # --- CORS: comma-separated browser origins for the Next.js frontend ---
    cors_allowed_origins: str = "http://localhost:3000"

    # --- Auth / sessions ---
    jwt_secret_key: str
    access_token_expire_minutes: int = 60 * 24  # 1 day (dev-friendly)
    cookie_secure: bool = False  # set true in production (HTTPS)
    cookie_samesite: str = "lax"

    # --- Context assembly (Phase 6 ContextBuilder) ---
    # Conservative, configurable INPUT token budget for the 8-layer context
    # package. This is a safety budget, NOT an invented per-model context window
    # (blueprint example = 16000). Tune per deployment via the environment.
    context_input_token_budget: int = 16000

    # --- Provider key encryption ---
    # Fernet key (generate: python -c "from cryptography.fernet import Fernet;
    # print(Fernet.generate_key().decode())"). Encrypts stored provider API keys.
    omnidesk_master_key: str
    # Optional server-default provider keys (fallback when a user has none configured).
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    anthropic_api_key: str | None = None

    @property
    def cors_origins(self) -> list[str]:
        """CORS origins as a cleaned list."""
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""
    return Settings()
