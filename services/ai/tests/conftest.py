from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.engine.manager import EngineManager
from app.main import create_app
from app.registry import BotRegistry


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    # No Stockfish in tests: the engine is unavailable, baseline bots only.
    settings = Settings(stockfish_path=None)
    app = create_app()
    engine = EngineManager(None)
    await engine.start()  # no-op when path is None
    app.state.engine = engine
    app.state.registry = BotRegistry(settings, engine)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
