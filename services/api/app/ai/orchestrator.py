from __future__ import annotations

import random
from typing import Protocol

import chess
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.client import AIError, AIMoveResult
from app.ai.constants import AI_USER_ID, FALLBACK_ENGINE
from app.core.config import Settings
from app.core.logging import get_logger
from app.db.models import AiGame, Game
from app.games import chess_engine
from app.games.errors import IllegalMove
from app.games.schemas import GameState
from app.games.service import GameService

logger = get_logger("app.ai.orchestrator")


class MoveProvider(Protocol):
    async def request_move(
        self, *, fen: str, difficulty: str, level: int | None, correlation_id: str | None
    ) -> AIMoveResult: ...


class AIOrchestrator:
    """Plays the AI side of an ai-mode game.

    Invoked *after* a human transition has been committed. It runs in its own session
    and transaction, so an AI failure can never roll back the human's move. The AI move
    is applied through :meth:`GameService.submit_move` with a deterministic command id
    (``ai:<game>:<sequence>``), so retries are idempotent and a duplicate invocation
    cannot double-move. If the service is unreachable/invalid, it optionally falls back
    to a locally-chosen legal move so the game never stalls.
    """

    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        provider: MoveProvider | None,
        settings: Settings,
    ) -> None:
        self._sessionmaker = sessionmaker
        self._provider = provider
        self._settings = settings

    async def maybe_play(self, game_id: str, correlation_id: str | None = None) -> GameState | None:
        """Play one AI move if it is the AI's turn. Returns the new state, else None."""
        async with self._sessionmaker() as session:
            service = GameService(session)
            game = await session.get(Game, game_id)
            if game is None or game.status != "active":
                return None
            if self._side_to_move_user(game) != AI_USER_ID:
                return None  # not the AI's turn (or not an ai-mode game)

            difficulty, level = await self._opponent(session, game_id)
            fen, sequence = game.current_fen, game.sequence
            command_id = f"ai:{game_id}:{sequence}"

            uci, engine, think_ms = await self._decide(fen, difficulty, level, correlation_id)
            if uci is None:
                # Provider failed and fallback is disabled: leave the game at the AI's
                # turn with the human move intact. The client can retry via /ai-move.
                return None

            state = await self._apply(
                service, game_id, command_id, sequence, uci, engine, think_ms, fen
            )
            await session.commit()
            applied = state.last_move.uci if state.last_move else None
            logger.info(
                "ai_move_applied",
                extra={"extra": {"game_id": game_id, "engine": engine, "uci": applied}},
            )
            return state

    async def _decide(
        self, fen: str, difficulty: str, level: int | None, correlation_id: str | None
    ) -> tuple[str | None, str, int | None]:
        """Return (uci, engine, think_ms). uci is None only when no move can be made."""
        if self._provider is not None:
            try:
                result = await self._provider.request_move(
                    fen=fen, difficulty=difficulty, level=level, correlation_id=correlation_id
                )
                return result.uci, result.engine, result.think_ms
            except AIError:
                logger.warning("ai_provider_failed", extra={"extra": {"difficulty": difficulty}})

        if not self._settings.ai_fallback_to_random:
            return None, "", None
        return self._random_uci(fen), FALLBACK_ENGINE, None

    async def _apply(
        self,
        service: GameService,
        game_id: str,
        command_id: str,
        sequence: int,
        uci: str,
        engine: str,
        think_ms: int | None,
        fen: str,
    ) -> GameState:
        try:
            return await service.submit_move(
                game_id=game_id,
                actor_id=AI_USER_ID,
                command_id=command_id,
                expected_sequence=sequence,
                uci=uci,
                engine=engine,
                think_ms=think_ms,
            )
        except IllegalMove:
            # The provider returned a move the service accepted but our authority
            # rejected (should not happen). Fall back rather than corrupt the game.
            if not self._settings.ai_fallback_to_random:
                raise
            logger.warning("ai_move_illegal_fallback", extra={"extra": {"game_id": game_id}})
            return await service.submit_move(
                game_id=game_id,
                actor_id=AI_USER_ID,
                command_id=command_id,
                expected_sequence=sequence,
                uci=self._random_uci(fen),
                engine=FALLBACK_ENGINE,
                think_ms=None,
            )

    @staticmethod
    def _side_to_move_user(game: Game) -> str | None:
        color = chess_engine.side_to_move(game.current_fen)
        return game.white_user_id if color == "white" else game.black_user_id

    @staticmethod
    async def _opponent(session: AsyncSession, game_id: str) -> tuple[str, int | None]:
        ai_game = (
            await session.execute(select(AiGame).where(AiGame.game_id == game_id))
        ).scalar_one_or_none()
        if ai_game is None:  # pragma: no cover - ai-mode games always have a row
            return "heuristic", None
        return ai_game.difficulty, ai_game.level

    @staticmethod
    def _random_uci(fen: str) -> str:
        board = chess.Board(fen)
        return random.choice(list(board.legal_moves)).uci()
