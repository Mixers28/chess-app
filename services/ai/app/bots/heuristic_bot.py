from __future__ import annotations

import random

import chess

from app.bots.base import Bot, ChosenMove
from app.bots.evaluation import evaluate
from app.schemas import Constraints


class HeuristicBot(Bot):
    """Greedy 1-ply bot: plays the move with the best static eval after it.

    Stronger than random — it grabs hanging material and is biased toward checks — but
    has no lookahead, so it walks into recaptures. A good "beginner" opponent.
    """

    name = "heuristic"

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()

    async def choose(
        self, board: chess.Board, constraints: Constraints, level: int | None = None
    ) -> ChosenMove:
        scored: list[tuple[int, chess.Move]] = []
        for move in board.legal_moves:
            gives_check = board.gives_check(move)
            board.push(move)
            # evaluate() is from the side-to-move POV; after our push it's the
            # opponent's turn, so negate to get our perspective.
            score = -evaluate(board)
            if gives_check:
                score += 30
            board.pop()
            scored.append((score, move))

        best = max(s for s, _ in scored)
        # Random tiebreak among equally good moves keeps play varied.
        top = [m for s, m in scored if s == best]
        move = self._rng.choice(top)
        return ChosenMove(move=move, evaluation=round(best / 100, 2), depth=1)
