from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app import __version__
from app.ai.client import AIClient, CircuitBreaker
from app.ai.orchestrator import AIOrchestrator
from app.api import health
from app.api.errors import register_exception_handlers
from app.api.v1 import games
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestIDMiddleware
from app.db.session import dispose_engine, get_sessionmaker

logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)

    http_client: httpx.AsyncClient | None = None
    provider: AIClient | None = None
    if settings.ai_base_url:
        http_client = httpx.AsyncClient(
            base_url=settings.ai_base_url,
            timeout=settings.ai_request_timeout_ms / 1000,
        )
        provider = AIClient(
            http_client,
            retries=settings.ai_retries,
            breaker=CircuitBreaker(
                threshold=settings.ai_breaker_threshold,
                cooldown_s=settings.ai_breaker_cooldown_s,
            ),
        )
    # The orchestrator always exists: without a provider it uses the local fallback,
    # so ai-mode games are still playable in dev with no AI service running.
    app.state.ai_orchestrator = AIOrchestrator(get_sessionmaker(), provider, settings)

    logger.info(
        "startup",
        extra={"extra": {"environment": settings.environment, "ai": bool(provider)}},
    )
    try:
        yield
    finally:
        if http_client is not None:
            await http_client.aclose()
        await dispose_engine()
        logger.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(title="Chess API", version=__version__, lifespan=lifespan)
    app.add_middleware(RequestIDMiddleware)
    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(games.router, prefix="/v1")
    return app


app = create_app()
