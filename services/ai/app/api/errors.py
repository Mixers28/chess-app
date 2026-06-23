from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.errors import (
    EngineUnavailable,
    GameAlreadyOver,
    InvalidPosition,
    UnknownDifficulty,
)


def _problem(status_code: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": code, "detail": detail})


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidPosition)
    async def _invalid(_: Request, exc: InvalidPosition) -> JSONResponse:
        return _problem(422, "invalid_position", str(exc))

    @app.exception_handler(GameAlreadyOver)
    async def _over(_: Request, exc: GameAlreadyOver) -> JSONResponse:
        return _problem(409, "game_already_over", str(exc))

    @app.exception_handler(UnknownDifficulty)
    async def _unknown(_: Request, exc: UnknownDifficulty) -> JSONResponse:
        return _problem(400, "unknown_difficulty", str(exc))

    @app.exception_handler(EngineUnavailable)
    async def _unavailable(_: Request, exc: EngineUnavailable) -> JSONResponse:
        return _problem(503, "engine_unavailable", str(exc))
