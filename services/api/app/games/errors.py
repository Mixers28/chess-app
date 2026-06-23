from __future__ import annotations


class GameError(Exception):
    """Base class for domain errors raised by the game command service."""


class GameNotFound(GameError):
    pass


class GameNotActive(GameError):
    """The game has already finished; no further commands are accepted."""


class IllegalMove(GameError):
    """The move is not legal in the current position."""


class StaleSequence(GameError):
    """The client's expected_sequence does not match canonical state.

    Carries the canonical recovery snapshot so the API can return current state and
    let the client resync without a separate round trip.
    """

    def __init__(self, expected: int, actual: int, state: object | None = None) -> None:
        super().__init__(f"expected sequence {expected}, server is at {actual}")
        self.expected = expected
        self.actual = actual
        self.state = state


class NotAParticipant(GameError):
    """The actor is not a player in this game."""


class NotYourTurn(GameError):
    """The actor is a participant but it is not their turn to move."""
