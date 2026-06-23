from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import chess

from app.schemas import Constraints


@dataclass(frozen=True)
class ChosenMove:
    """A bot's decision plus whatever metadata it can cheaply provide."""

    move: chess.Move
    evaluation: float | None = None  # pawns, from side-to-move POV
    depth: int | None = None
    engine: str | None = None


class Bot(ABC):
    """A move-selection strategy.

    Implementations must return a legal move for ``board`` (which is guaranteed to be
    non-terminal by the service). They never mutate the board passed in.
    """

    name: str

    @abstractmethod
    async def choose(
        self, board: chess.Board, constraints: Constraints, level: int | None
    ) -> ChosenMove:
        """Return a legal move. ``level`` is a generic strength knob (bot-specific)."""
        ...
