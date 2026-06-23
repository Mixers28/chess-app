from __future__ import annotations

from app.bots.base import Bot
from app.bots.heuristic_bot import HeuristicBot
from app.bots.random_bot import RandomBot
from app.bots.search_bot import SearchBot
from app.bots.stockfish_bot import StockfishBot
from app.core.config import Settings
from app.engine.manager import EngineManager
from app.errors import EngineUnavailable, UnknownDifficulty

# Difficulties that always exist (pure-Python, no external engine).
BASELINE_DIFFICULTIES = ("random", "heuristic", "search")


class BotRegistry:
    """Maps a difficulty name to a bot. Stockfish is only present when configured."""

    def __init__(self, settings: Settings, engine: EngineManager) -> None:
        self._engine = engine
        self._bots: dict[str, Bot] = {
            "random": RandomBot(),
            "heuristic": HeuristicBot(),
            "search": SearchBot(default_depth=settings.default_search_depth),
        }
        if engine.available:
            self._bots["stockfish"] = StockfishBot(
                engine, default_movetime_ms=settings.default_movetime_ms
            )

    def get(self, difficulty: str) -> Bot:
        bot = self._bots.get(difficulty)
        if bot is not None:
            return bot
        if difficulty == "stockfish":
            # Recognized but the engine binary isn't available in this deployment.
            raise EngineUnavailable("stockfish backend is not configured")
        raise UnknownDifficulty(difficulty)

    def names(self) -> list[str]:
        return list(self._bots.keys())

    @property
    def stockfish_available(self) -> bool:
        return "stockfish" in self._bots
