from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api.errors import register_exception_handlers
from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.engine.manager import EngineManager
from app.registry import BotRegistry

logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)

    engine = EngineManager(settings.stockfish_path)
    await engine.start()
    app.state.engine = engine
    app.state.registry = BotRegistry(settings, engine)
    logger.info(
        "startup",
        extra={"extra": {"environment": settings.environment, "stockfish": engine.available}},
    )
    try:
        yield
    finally:
        await engine.close()
        logger.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(title="Chess AI", version=__version__, lifespan=lifespan)
    register_exception_handlers(app)
    app.include_router(router)
    return app


app = create_app()
