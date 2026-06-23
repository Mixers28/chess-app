from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings, populated from env vars (prefix ``AI_``)."""

    model_config = SettingsConfigDict(
        env_prefix="AI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "local"
    log_level: str = "INFO"

    # Path to a Stockfish (or any UCI) binary. When unset/missing, the "stockfish"
    # difficulty is unavailable but baseline bots still work and /ready stays green.
    stockfish_path: str | None = None

    # Default per-move limits for engine/search bots; overridable per request.
    default_movetime_ms: int = 100
    default_search_depth: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
