from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.db.session import get_session

router = APIRouter(tags=["health"])
logger = get_logger("app.health")


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness: the process is up. No external dependencies are checked."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(
    response: Response,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    """Readiness: verify the dependencies required to serve traffic.

    Postgres is always required. Redis is only probed once configured (Phase 4+).
    """
    checks: dict[str, str] = {}

    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # pragma: no cover - exercised via integration env
        logger.exception("readiness_db_failed")
        checks["database"] = f"error: {type(exc).__name__}"

    if settings.redis_url:
        checks["redis"] = await _check_redis(settings.redis_url)

    ready = all(v == "ok" for v in checks.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"ready": ready, "checks": checks}


async def _check_redis(url: str) -> str:
    try:
        import redis.asyncio as redis

        client = redis.from_url(url)
        try:
            await client.ping()
            return "ok"
        finally:
            await client.aclose()
    except Exception as exc:  # pragma: no cover - exercised via integration env
        logger.exception("readiness_redis_failed")
        return f"error: {type(exc).__name__}"
