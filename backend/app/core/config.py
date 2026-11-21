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

    @property
    def cors_origins(self) -> list[str]:
        """CORS origins as a cleaned list."""
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""
    return Settings()
