from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.constants import AI_USER_ID
from app.ai.orchestrator import AIOrchestrator
from app.auth.identity import get_current_user
from app.core.logging import request_id_var
from app.db.models import User
from app.db.session import get_session
from app.games.schemas import (
    CreateGameRequest,
    GameState,
    MoveRecord,
    ResignRequest,
    SubmitMoveRequest,
)
from app.games.service import GameService

router = APIRouter(prefix="/games", tags=["games"])


def _service(session: AsyncSession = Depends(get_session)) -> GameService:
    return GameService(session)


def get_orchestrator(request: Request) -> AIOrchestrator | None:
    return getattr(request.app.state, "ai_orchestrator", None)


def _is_ai_game(state: GameState) -> bool:
    return AI_USER_ID in (state.white_user_id, state.black_user_id)


@router.post("", response_model=GameState, status_code=status.HTTP_201_CREATED)
async def create_game(
    body: CreateGameRequest,
    session: AsyncSession = Depends(get_session),
    service: GameService = Depends(_service),
    user: User = Depends(get_current_user),
    orchestrator: AIOrchestrator | None = Depends(get_orchestrator),
) -> GameState:
    state = await service.create_game(
        creator_id=user.id,
        mode=body.mode,
        time_control=body.time_control,
        difficulty=body.difficulty,
        level=body.level,
        color=body.color,
    )
    # Persist the new game before the orchestrator (separate session) reads it.
    await session.commit()

    # If the human chose black, the AI (white) moves first.
    if body.mode == "ai" and orchestrator is not None:
        ai_state = await orchestrator.maybe_play(state.game_id, request_id_var.get())
        if ai_state is not None:
            return ai_state
    return state


@router.get("/{game_id}", response_model=GameState)
async def get_game(game_id: str, service: GameService = Depends(_service)) -> GameState:
    return await service.get_state(game_id)


@router.post("/{game_id}/moves", response_model=GameState)
async def submit_move(
    game_id: str,
    body: SubmitMoveRequest,
    session: AsyncSession = Depends(get_session),
    service: GameService = Depends(_service),
    user: User = Depends(get_current_user),
    orchestrator: AIOrchestrator | None = Depends(get_orchestrator),
) -> GameState:
    human_state = await service.submit_move(
        game_id=game_id,
        actor_id=user.id,
        command_id=body.command_id,
        expected_sequence=body.expected_sequence,
        uci=body.move,
    )
    # Commit the human transition independently so an AI failure can't undo it.
    await session.commit()

    if orchestrator is not None and _is_ai_game(human_state):
        ai_state = await orchestrator.maybe_play(game_id, request_id_var.get())
        if ai_state is not None:
            return ai_state
    return human_state


@router.post("/{game_id}/ai-move", response_model=GameState)
async def request_ai_move(
    game_id: str,
    service: GameService = Depends(_service),
    orchestrator: AIOrchestrator | None = Depends(get_orchestrator),
) -> GameState:
    """Manually drive the AI's turn — used to retry after a failed/skipped AI move."""
    if orchestrator is not None:
        state = await orchestrator.maybe_play(game_id, request_id_var.get())
        if state is not None:
            return state
    return await service.get_state(game_id)


@router.post("/{game_id}/resign", response_model=GameState)
async def resign(
    game_id: str,
    body: ResignRequest,
    service: GameService = Depends(_service),
    user: User = Depends(get_current_user),
) -> GameState:
    return await service.resign(
        game_id=game_id,
        actor_id=user.id,
        command_id=body.command_id,
        expected_sequence=body.expected_sequence,
    )


@router.get("/{game_id}/moves", response_model=list[MoveRecord])
async def list_moves(
    game_id: str, service: GameService = Depends(_service)
) -> list[MoveRecord]:
    moves = await service.list_moves(game_id)
    return [
        MoveRecord(
            ply=m.ply,
            color=m.color,
            uci=m.uci_move,
            san=m.san_move,
            fen_after=m.fen_after,
            engine=m.engine,
            think_ms=m.think_ms,
        )
        for m in moves
    ]
