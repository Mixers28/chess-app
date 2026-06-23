from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.constants import AI_USER_ID, AI_USERNAME
from app.db.models import AiGame, Game, Move, User
from app.games import chess_engine
from app.games.errors import (
    GameNotActive,
    GameNotFound,
    NotAParticipant,
    NotYourTurn,
    StaleSequence,
)
from app.games.schemas import GameState, LastMove


class GameService:
    """Authoritative game command service.

    Clients submit commands (move, resign); this service validates against canonical
    state and emits a new sequence only after the transition commits. The caller's
    session transaction provides atomicity; ``_lock_game`` serializes concurrent
    commands per game on Postgres (FOR UPDATE) and unique constraints on
    (game_id, command_id) / (game_id, ply) are the final idempotency backstop.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_game(
        self,
        *,
        creator_id: str,
        mode: str = "local",
        time_control: str | None = None,
        difficulty: str | None = None,
        level: int | None = None,
        color: str = "white",
    ) -> GameState:
        if mode == "ai":
            white_id, black_id = await self._assign_ai_colors(creator_id, color)
        else:
            # Local (hotseat) mode: the creator controls both colors so a full game can
            # be played end-to-end before online multiplayer (Phase 4) exists.
            white_id, black_id = creator_id, creator_id

        game = Game(
            white_user_id=white_id,
            black_user_id=black_id,
            mode=mode,
            status="active",
            current_fen=chess_engine.INITIAL_FEN,
            sequence=0,
            time_control=time_control,
        )
        self.session.add(game)
        await self.session.flush()

        if mode == "ai":
            self.session.add(
                AiGame(
                    game_id=game.id,
                    human_user_id=creator_id,
                    difficulty=difficulty or "heuristic",
                    level=level,
                )
            )
            await self.session.flush()

        return self._state(game, last_move=None)

    async def _assign_ai_colors(self, creator_id: str, color: str) -> tuple[str, str]:
        """Return (white_user_id, black_user_id) for an ai-mode game."""
        await self._ensure_user(AI_USER_ID, AI_USERNAME)
        if color == "black":
            return AI_USER_ID, creator_id
        return creator_id, AI_USER_ID

    async def _ensure_user(self, user_id: str, username: str) -> None:
        if await self.session.get(User, user_id) is None:
            self.session.add(User(id=user_id, username=username))
            await self.session.flush()

    async def get_state(self, game_id: str) -> GameState:
        game = await self._get(game_id)
        last = await self._last_move(game_id)
        return self._state(game, last_move=_last_move_dto(last))

    async def list_moves(self, game_id: str) -> list[Move]:
        await self._get(game_id)  # 404 if missing
        result = await self.session.execute(
            select(Move).where(Move.game_id == game_id).order_by(Move.ply)
        )
        return list(result.scalars().all())

    async def submit_move(
        self,
        *,
        game_id: str,
        actor_id: str,
        command_id: str,
        expected_sequence: int,
        uci: str,
        engine: str | None = None,
        think_ms: int | None = None,
    ) -> GameState:
        game = await self._lock_game(game_id)

        # Idempotent replay: a previously accepted command returns current state.
        replay = await self._find_command(game_id, command_id)
        if replay is not None:
            return self._state(game, last_move=_last_move_dto(await self._last_move(game_id)))

        if game.status != "active":
            raise GameNotActive(f"game {game_id} is {game.status}")
        await self._require_sequence(game, expected_sequence)

        mover_color = chess_engine.side_to_move(game.current_fen)
        self._require_turn(game, actor_id, mover_color)

        outcome = chess_engine.apply_move(game.current_fen, uci)  # raises IllegalMove

        ply = game.sequence + 1
        self.session.add(
            Move(
                game_id=game.id,
                ply=ply,
                player_id=actor_id,
                color=mover_color,
                uci_move=uci,
                san_move=outcome.san,
                fen_after=outcome.fen_after,
                command_id=command_id,
                engine=engine,
                think_ms=think_ms,
            )
        )
        game.current_fen = outcome.fen_after
        game.sequence = ply
        game.status = outcome.status
        game.result = outcome.result
        await self.session.flush()

        if outcome.status != "active":
            game.pgn = await self._build_pgn(game)
            await self.session.flush()
        return self._state(game, last_move=LastMove(uci=uci, san=outcome.san))

    async def resign(
        self, *, game_id: str, actor_id: str, command_id: str, expected_sequence: int
    ) -> GameState:
        game = await self._lock_game(game_id)

        replay = await self._find_command(game_id, command_id)
        if replay is not None:
            return self._state(game, last_move=_last_move_dto(await self._last_move(game_id)))

        if game.status != "active":
            raise GameNotActive(f"game {game_id} is {game.status}")
        await self._require_sequence(game, expected_sequence)
        self._require_participant(game, actor_id)

        # The resigning side loses; the opponent's color wins.
        resigning_color = "white" if actor_id == game.white_user_id else "black"
        game.result = "0-1" if resigning_color == "white" else "1-0"
        game.status = "resigned"
        game.sequence += 1
        game.pgn = await self._build_pgn(game)
        await self.session.flush()
        return self._state(game, last_move=_last_move_dto(await self._last_move(game_id)))

    # --- internals -------------------------------------------------------------

    async def _get(self, game_id: str) -> Game:
        game = await self.session.get(Game, game_id)
        if game is None:
            raise GameNotFound(game_id)
        return game

    async def _lock_game(self, game_id: str) -> Game:
        # FOR UPDATE serializes per-game transitions on Postgres; SQLite ignores it
        # and relies on the unique constraints below for idempotency.
        result = await self.session.execute(
            select(Game).where(Game.id == game_id).with_for_update()
        )
        game = result.scalar_one_or_none()
        if game is None:
            raise GameNotFound(game_id)
        return game

    async def _find_command(self, game_id: str, command_id: str) -> Move | None:
        result = await self.session.execute(
            select(Move).where(Move.game_id == game_id, Move.command_id == command_id)
        )
        return result.scalar_one_or_none()

    async def _last_move(self, game_id: str) -> Move | None:
        result = await self.session.execute(
            select(Move).where(Move.game_id == game_id).order_by(Move.ply.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def _build_pgn(self, game: Game) -> str:
        result = await self.session.execute(
            select(Move.uci_move).where(Move.game_id == game.id).order_by(Move.ply)
        )
        ucis = [row[0] for row in result.all()]
        return chess_engine.build_pgn(ucis, game.result)

    async def _require_sequence(self, game: Game, expected: int) -> None:
        if expected != game.sequence:
            recovery = self._state(game, last_move=_last_move_dto(await self._last_move(game.id)))
            raise StaleSequence(expected=expected, actual=game.sequence, state=recovery)

    @staticmethod
    def _require_participant(game: Game, actor_id: str) -> None:
        if actor_id not in (game.white_user_id, game.black_user_id):
            raise NotAParticipant(actor_id)

    def _require_turn(self, game: Game, actor_id: str, mover_color: str) -> None:
        self._require_participant(game, actor_id)
        expected_id = game.white_user_id if mover_color == "white" else game.black_user_id
        if actor_id != expected_id:
            raise NotYourTurn(f"it is {mover_color}'s turn")

    @staticmethod
    def _state(game: Game, *, last_move: LastMove | None) -> GameState:
        return GameState(
            game_id=game.id,
            sequence=game.sequence,
            fen=game.current_fen,
            turn=chess_engine.side_to_move(game.current_fen),
            status=game.status,
            result=game.result,
            last_move=last_move,
            white_user_id=game.white_user_id,
            black_user_id=game.black_user_id,
            mode=game.mode,
        )


def _last_move_dto(move: Move | None) -> LastMove | None:
    if move is None:
        return None
    return LastMove(uci=move.uci_move, san=move.san_move)
