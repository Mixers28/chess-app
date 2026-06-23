from __future__ import annotations

import pytest

from app.auth.identity import ensure_user
from app.db.models import Game
from app.games.errors import NotYourTurn
from app.games.service import GameService


async def test_turn_ownership_enforced_for_two_players(session) -> None:
    await ensure_user(session, "white-u")
    await ensure_user(session, "black-u")
    svc = GameService(session)

    state = await svc.create_game(creator_id="white-u", mode="local")
    # Reassign black to a distinct participant (join is Phase 4; we set it directly).
    game = await session.get(Game, state.game_id)
    game.black_user_id = "black-u"
    await session.flush()

    # It is white's turn; black attempting to move is rejected.
    with pytest.raises(NotYourTurn):
        await svc.submit_move(
            game_id=state.game_id,
            actor_id="black-u",
            command_id="c1",
            expected_sequence=0,
            uci="e2e4",
        )

    # White moves, then it is black's turn and black may move.
    await svc.submit_move(
        game_id=state.game_id, actor_id="white-u", command_id="c2", expected_sequence=0, uci="e2e4"
    )
    result = await svc.submit_move(
        game_id=state.game_id, actor_id="black-u", command_id="c3", expected_sequence=1, uci="e7e5"
    )
    assert result.sequence == 2
    assert result.turn == "white"
