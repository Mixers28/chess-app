from __future__ import annotations

import chess

from app.ai.client import AIMoveResult, AIUnavailable
from app.ai.constants import AI_USER_ID, FALLBACK_ENGINE


class ScriptedProvider:
    """Fake AI service that plays the first legal move (sorted UCI), deterministically."""

    def __init__(self) -> None:
        self.calls = 0

    async def request_move(
        self, *, fen: str, difficulty: str, level: int | None, correlation_id: str | None
    ) -> AIMoveResult:
        self.calls += 1
        board = chess.Board(fen)
        uci = sorted(m.uci() for m in board.legal_moves)[0]
        return AIMoveResult(uci=uci, engine="fake", evaluation=0.1, think_ms=12)


class FailingProvider:
    async def request_move(self, **_: object) -> AIMoveResult:
        raise AIUnavailable("down")


async def _create_ai_game(client, **body) -> dict:
    payload = {"mode": "ai", "difficulty": "search", **body}
    resp = await client.post("/v1/games", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _move(client, gid, command_id, seq, uci):
    return await client.post(
        f"/v1/games/{gid}/moves",
        json={"command_id": command_id, "expected_sequence": seq, "move": uci},
    )


async def test_ai_replies_after_human_move(make_ai_client) -> None:
    provider = ScriptedProvider()
    async with make_ai_client(provider=provider) as client:
        game = await _create_ai_game(client)
        assert game["mode"] == "ai"
        assert game["white_user_id"] != AI_USER_ID  # human is white by default
        assert game["black_user_id"] == AI_USER_ID

        gid = game["game_id"]
        resp = await _move(client, gid, "h1", 0, "e2e4")
        assert resp.status_code == 200, resp.text
        state = resp.json()

        # Human move (seq 1) + AI reply (seq 2), back to the human's turn.
        assert state["sequence"] == 2
        assert state["turn"] == "white"
        assert state["status"] == "active"
        assert provider.calls == 1

        listed = (await client.get(f"/v1/games/{gid}/moves")).json()
        assert len(listed) == 2
        assert listed[0]["engine"] is None  # human move
        assert listed[1]["engine"] == "fake"  # AI move with telemetry
        assert listed[1]["think_ms"] == 12


async def test_human_as_black_makes_ai_move_first(make_ai_client) -> None:
    async with make_ai_client(provider=ScriptedProvider()) as client:
        game = await _create_ai_game(client, color="black")
        # The AI (white) has already moved during creation.
        assert game["white_user_id"] == AI_USER_ID
        assert game["sequence"] == 1
        assert game["turn"] == "black"
        assert game["last_move"] is not None


async def test_fallback_to_random_when_provider_fails(make_ai_client) -> None:
    async with make_ai_client(provider=FailingProvider(), fallback=True) as client:
        game = await _create_ai_game(client)
        gid = game["game_id"]
        resp = await _move(client, gid, "h1", 0, "e2e4")
        state = resp.json()

        # Provider failed, but the game advanced via the local fallback.
        assert state["sequence"] == 2
        listed = (await client.get(f"/v1/games/{gid}/moves")).json()
        assert listed[1]["engine"] == FALLBACK_ENGINE


async def test_no_fallback_keeps_human_move_and_leaves_ai_turn(make_ai_client) -> None:
    async with make_ai_client(provider=FailingProvider(), fallback=False) as client:
        game = await _create_ai_game(client)
        gid = game["game_id"]
        resp = await _move(client, gid, "h1", 0, "e2e4")
        state = resp.json()

        # Human move committed (seq 1); it is now the AI's turn; nothing corrupted.
        assert state["sequence"] == 1
        assert state["turn"] == "black"
        assert state["status"] == "active"
        listed = (await client.get(f"/v1/games/{gid}/moves")).json()
        assert len(listed) == 1

        # Retrying via /ai-move with the still-failing provider is safe (no move, no crash).
        retry = await client.post(f"/v1/games/{gid}/ai-move")
        assert retry.status_code == 200
        assert retry.json()["sequence"] == 1


async def test_ai_move_endpoint_is_idempotent_on_humans_turn(make_ai_client) -> None:
    async with make_ai_client(provider=ScriptedProvider()) as client:
        game = await _create_ai_game(client)
        gid = game["game_id"]
        await _move(client, gid, "h1", 0, "e2e4")  # advances to seq 2, human's turn

        # It is the human's turn now; driving the AI must be a no-op.
        resp = await client.post(f"/v1/games/{gid}/ai-move")
        assert resp.status_code == 200
        assert resp.json()["sequence"] == 2
        assert len((await client.get(f"/v1/games/{gid}/moves")).json()) == 2
