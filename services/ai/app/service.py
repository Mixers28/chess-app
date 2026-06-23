from __future__ import annotations

import time

import chess

from app.errors import GameAlreadyOver, InvalidPosition
from app.registry import BotRegistry
from app.schemas import Constraints, MoveRequest, MoveResponse


class MoveService:
    """Turns a move request into a validated move, independent of transport."""

    def __init__(self, registry: BotRegistry) -> None:
        self._registry = registry

    async def choose_move(self, req: MoveRequest) -> MoveResponse:
        board = self._parse(req.fen)
        if board.is_game_over() or not any(board.legal_moves):
            raise GameAlreadyOver("position is terminal; no move to make")

        bot = self._registry.get(req.difficulty)
        constraints = req.constraints or Constraints()

        start = time.perf_counter()
        chosen = await bot.choose(board, constraints, req.level)
        think_ms = int((time.perf_counter() - start) * 1000)

        # Defense in depth: never return an illegal move even if a bot misbehaves.
        if chosen.move not in board.legal_moves:
            raise InvalidPosition(f"bot {bot.name} produced illegal move {chosen.move}")

        return MoveResponse(
            uci=chosen.move.uci(),
            san=board.san(chosen.move),
            difficulty=req.difficulty,
            engine=chosen.engine or bot.name,
            evaluation=chosen.evaluation,
            depth=chosen.depth,
            think_ms=think_ms,
            correlation_id=req.correlation_id,
        )

    @staticmethod
    def _parse(fen: str) -> chess.Board:
        try:
            return chess.Board(fen)
        except ValueError as exc:
            raise InvalidPosition(f"malformed FEN: {exc}") from exc
