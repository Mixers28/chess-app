from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.ai.orchestrator import AIOrchestrator, MoveProvider
from app.core.config import Settings
from app.db.base import Base
from app.db.session import get_session
from app.main import create_app


@pytest_asyncio.fixture
async def sessionmaker_() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    # In-memory SQLite shared across the test via StaticPool (single connection).
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    yield maker
    await engine.dispose()


@pytest_asyncio.fixture
async def session(sessionmaker_) -> AsyncIterator[AsyncSession]:
    async with sessionmaker_() as s:
        yield s


def _build_app(sessionmaker_, provider: MoveProvider | None, fallback: bool):
    app = create_app()

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with sessionmaker_() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    app.dependency_overrides[get_session] = override_get_session
    # The orchestrator shares the test's sessionmaker so it reads/writes the same DB.
    settings = Settings(ai_fallback_to_random=fallback)
    app.state.ai_orchestrator = AIOrchestrator(sessionmaker_, provider, settings)
    return app


@pytest_asyncio.fixture
async def client(sessionmaker_) -> AsyncIterator[AsyncClient]:
    app = _build_app(sessionmaker_, provider=None, fallback=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def make_ai_client(sessionmaker_):
    """Factory: build a client whose AI orchestrator uses ``provider`` and fallback."""

    @asynccontextmanager
    async def _factory(provider: MoveProvider | None = None, fallback: bool = True):
        app = _build_app(sessionmaker_, provider=provider, fallback=fallback)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    return _factory
