from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings, populated from env vars (prefix ``CHESS_``)."""

    model_config = SettingsConfigDict(
        env_prefix="CHESS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "local"
    log_level: str = "INFO"

    # Async SQLAlchemy URL. asyncpg in prod; aiosqlite in tests.
    database_url: str = "postgresql+asyncpg://chess:chess@localhost:5432/chess"

    # Optional in Phase 1. When unset, readiness skips the Redis probe.
    redis_url: str | None = None

    # Dev identity seam — replaced by Sign in with Apple in Phase 4.
    dev_user_id: str = "00000000-0000-0000-0000-000000000001"

    # AI service (services/ai). When unset, ai-mode games still work via the local
    # random fallback (if enabled); set it to use the real engine/bots.
    ai_base_url: str | None = None
    ai_request_timeout_ms: int = 2000
    ai_retries: int = 2
    ai_breaker_threshold: int = 5  # consecutive failures before the breaker opens
    ai_breaker_cooldown_s: float = 10.0
    ai_fallback_to_random: bool = True
    ai_default_difficulty: str = "heuristic"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"prod", "production"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
