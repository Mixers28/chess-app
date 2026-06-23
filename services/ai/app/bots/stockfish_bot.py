from __future__ import annotations

import chess
import chess.engine

from app.bots.base import Bot, ChosenMove
from app.engine.manager import EngineManager
from app.schemas import Constraints


class StockfishBot(Bot):
    """Adapter over a UCI engine via :class:`EngineManager`.

    Strength is set with the request ``level`` mapped to UCI "Skill Level" (0-20).
    A custom model (e.g. chess-sim) could later implement this same ``Bot`` interface
    and register under its own difficulty, with no change to the service or callers.
    """

    name = "stockfish"

    def __init__(
        self,
        manager: EngineManager,
        *,
        default_movetime_ms: int,
        default_skill: int = 8,
    ) -> None:
        self._manager = manager
        self._default_movetime_ms = default_movetime_ms
        self._default_skill = default_skill

    async def choose(
        self, board: chess.Board, constraints: Constraints, level: int | None = None
    ) -> ChosenMove:
        skill = self._default_skill if level is None else max(0, min(20, level))
        limit = chess.engine.Limit(
            time=(constraints.movetime_ms or self._default_movetime_ms) / 1000,
            depth=constraints.max_depth,
        )
        result = await self._manager.play(board, limit, skill_level=skill)
        if result.move is None:  # pragma: no cover - engine should always return a move
            raise RuntimeError("engine returned no move")

        evaluation = self._eval_pawns(result, board)
        return ChosenMove(move=result.move, evaluation=evaluation)

    @staticmethod
    def _eval_pawns(result: chess.engine.PlayResult, board: chess.Board) -> float | None:
        score = result.info.get("score") if result.info else None
        if score is None:
            return None
        cp = score.pov(board.turn).score(mate_score=100_000)
        return None if cp is None else round(cp / 100, 2)
