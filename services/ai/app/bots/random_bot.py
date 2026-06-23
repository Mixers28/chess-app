from __future__ import annotations

import random

import chess

from app.bots.base import Bot, ChosenMove
from app.schemas import Constraints


class RandomBot(Bot):
    """Picks a uniformly random legal move. The weakest, most deterministic baseline."""

    name = "random"

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()

    async def choose(
        self, board: chess.Board, constraints: Constraints, level: int | None = None
    ) -> ChosenMove:
        move = self._rng.choice(list(board.legal_moves))
        return ChosenMove(move=move)
