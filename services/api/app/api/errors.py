from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.games.errors import (
    GameNotActive,
    GameNotFound,
    IllegalMove,
    NotAParticipant,
    NotYourTurn,
    StaleSequence,
)


def _problem(status_code: int, code: str, detail: str, **extra: object) -> JSONResponse:
    body: dict[str, object] = {"error": code, "detail": detail}
    body.update(extra)
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    """Map domain errors to stable HTTP envelopes.

    The mapping is the public contract: 404 not found, 422 illegal move, 409
    conflict for stale/finished games, 403 for authorization. Stale commands return
    the canonical recovery snapshot so clients can resync in one round trip.
    """

    @app.exception_handler(GameNotFound)
    async def _not_found(_: Request, exc: GameNotFound) -> JSONResponse:
        return _problem(status.HTTP_404_NOT_FOUND, "game_not_found", str(exc))

    @app.exception_handler(IllegalMove)
    async def _illegal(_: Request, exc: IllegalMove) -> JSONResponse:
        return _problem(422, "illegal_move", str(exc))

    @app.exception_handler(GameNotActive)
    async def _finished(_: Request, exc: GameNotActive) -> JSONResponse:
        return _problem(status.HTTP_409_CONFLICT, "game_not_active", str(exc))

    @app.exception_handler(StaleSequence)
    async def _stale(_: Request, exc: StaleSequence) -> JSONResponse:
        state = exc.state.model_dump() if hasattr(exc.state, "model_dump") else None
        return _problem(
            status.HTTP_409_CONFLICT,
            "stale_sequence",
            str(exc),
            expected_sequence=exc.expected,
            current_sequence=exc.actual,
            state=state,
        )

    @app.exception_handler(NotAParticipant)
    async def _not_participant(_: Request, exc: NotAParticipant) -> JSONResponse:
        return _problem(status.HTTP_403_FORBIDDEN, "not_a_participant", str(exc))

    @app.exception_handler(NotYourTurn)
    async def _not_turn(_: Request, exc: NotYourTurn) -> JSONResponse:
        return _problem(status.HTTP_403_FORBIDDEN, "not_your_turn", str(exc))
