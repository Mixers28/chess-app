from __future__ import annotations

import random
from dataclasses import dataclass

import chess

from app.bots.base import Bot, ChosenMove
from app.bots.heuristic_bot import HeuristicBot
from app.bots.random_bot import RandomBot
from app.bots.search_bot import SearchBot
from app.bots.stockfish_bot import StockfishBot
from app.schemas import Constraints


@dataclass(frozen=True)
class LevelProfile:
    name: str
    bot: str
    depth: int | None = None
    top_n: int = 1
    blunder_rate: float = 0.0
    stockfish_skill: int | None = None
    movetime_ms: int | None = None


LEVELS: dict[int, LevelProfile] = {
    1: LevelProfile("Beginner", "random"),
    2: LevelProfile("Casual", "heuristic"),
    3: LevelProfile("Club", "search", depth=2, top_n=4, blunder_rate=0.10),
    4: LevelProfile("Advanced", "search", depth=3, top_n=3, blunder_rate=0.05),
    5: LevelProfile("Expert", "search", depth=4),
    6: LevelProfile("Stockfish 1", "stockfish", stockfish_skill=0, movetime_ms=50),
    7: LevelProfile("Stockfish 2", "stockfish", stockfish_skill=3, movetime_ms=100),
    8: LevelProfile("Stockfish 3", "stockfish", stockfish_skill=6, movetime_ms=250),
    9: LevelProfile("Stockfish 4", "stockfish", stockfish_skill=10, movetime_ms=500),
    10: LevelProfile("Stockfish 5", "stockfish", stockfish_skill=15, movetime_ms=800),
}


class LevelBot(Bot):
    """User-facing 1-10 strength ladder.

    Low levels use intentionally noisy built-in bots. Higher levels use Stockfish
    when configured and fall back to the strongest built-in search otherwise.
    """

    name = "level"

    def __init__(
        self,
        *,
        stockfish: StockfishBot | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._stockfish = stockfish
        self._rng = rng or random.Random()

    async def choose(
        self, board: chess.Board, constraints: Constraints, level: int | None = None
    ) -> ChosenMove:
        numeric_level = max(1, min(10, level or 3))
        profile = LEVELS[numeric_level]

        if profile.bot == "random":
            chosen = await RandomBot(self._rng).choose(board, constraints, None)
            return self._with_engine(chosen, "random")
        if profile.bot == "heuristic":
            chosen = await HeuristicBot(self._rng).choose(board, constraints, None)
            return self._with_engine(chosen, "heuristic")
        if profile.bot == "stockfish" and self._stockfish is not None:
            engine_constraints = Constraints(
                movetime_ms=constraints.movetime_ms or profile.movetime_ms,
                max_depth=constraints.max_depth,
            )
            chosen = await self._stockfish.choose(
                board, engine_constraints, profile.stockfish_skill
            )
            return self._with_engine(chosen, "stockfish")

        depth = profile.depth or 4
        search_constraints = Constraints(
            movetime_ms=constraints.movetime_ms,
            max_depth=constraints.max_depth or depth,
        )
        chosen = await SearchBot(
            default_depth=depth,
            rng=self._rng,
            blunder_rate=profile.blunder_rate,
            top_n=profile.top_n,
        ).choose(board, search_constraints, None)
        return self._with_engine(chosen, "search")

    @staticmethod
    def _with_engine(chosen: ChosenMove, engine: str) -> ChosenMove:
        return ChosenMove(
            move=chosen.move,
            evaluation=chosen.evaluation,
            depth=chosen.depth,
            engine=engine,
        )
