from __future__ import annotations

import asyncio

import anyio
import chess
import chess.engine

from app.core.logging import get_logger

logger = get_logger("app.engine")


class EngineManager:
    """Owns a single long-lived UCI engine process (e.g. Stockfish).

    The python-chess engine is synchronous and single-process, so access is serialized
    behind a lock and the blocking calls run in a worker thread. The manager degrades
    gracefully: if no binary is configured or it fails to launch, ``available`` is False
    and the service simply doesn't offer the "stockfish" difficulty.
    """

    def __init__(self, path: str | None) -> None:
        self._path = path
        self._engine: chess.engine.SimpleEngine | None = None
        self._lock = asyncio.Lock()

    @property
    def available(self) -> bool:
        return self._engine is not None

    async def start(self) -> None:
        path = self._path
        if not path:
            logger.info("engine_disabled", extra={"extra": {"reason": "no AI_STOCKFISH_PATH"}})
            return
        try:
            self._engine = await anyio.to_thread.run_sync(
                lambda: chess.engine.SimpleEngine.popen_uci(path)
            )
            logger.info("engine_started", extra={"extra": {"path": path}})
        except Exception:
            self._engine = None
            logger.exception("engine_start_failed", extra={"extra": {"path": self._path}})

    async def close(self) -> None:
        if self._engine is not None:
            engine = self._engine
            self._engine = None
            await anyio.to_thread.run_sync(engine.quit)

    async def play(
        self, board: chess.Board, limit: chess.engine.Limit, skill_level: int | None
    ) -> chess.engine.PlayResult:
        if self._engine is None:
            raise RuntimeError("engine not available")
        engine = self._engine
        async with self._lock:
            if skill_level is not None:
                await anyio.to_thread.run_sync(
                    lambda: engine.configure({"Skill Level": skill_level})
                )
            return await anyio.to_thread.run_sync(
                lambda: engine.play(board, limit, info=chess.engine.INFO_SCORE)
            )
