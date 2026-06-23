from __future__ import annotations


class AIServiceError(Exception):
    """Base class for AI service domain errors."""


class InvalidPosition(AIServiceError):
    """The supplied FEN is malformed."""


class GameAlreadyOver(AIServiceError):
    """No move can be produced because the position is terminal."""


class UnknownDifficulty(AIServiceError):
    """The requested difficulty is not registered."""


class EngineUnavailable(AIServiceError):
    """A stronger backend (e.g. Stockfish) was requested but is not configured."""
