from __future__ import annotations


async def _create_game(client, mode: str = "local") -> dict:
    resp = await client.post("/v1/games", json={"mode": mode})
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _move(client, game_id: str, command_id: str, expected_sequence: int, uci: str, **kw):
    return await client.post(
        f"/v1/games/{game_id}/moves",
        json={"command_id": command_id, "expected_sequence": expected_sequence, "move": uci},
        **kw,
    )


async def test_create_game_returns_initial_state(client) -> None:
    game = await _create_game(client)
    assert game["sequence"] == 0
    assert game["turn"] == "white"
    assert game["status"] == "active"
    assert game["result"] is None
    assert game["fen"].startswith("rnbqkbnr")


async def test_get_game_404(client) -> None:
    resp = await client.get("/v1/games/does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["error"] == "game_not_found"


async def test_full_game_to_checkmate(client) -> None:
    """Play Fool's mate end to end through the API and verify persisted records."""
    game = await _create_game(client)
    gid = game["game_id"]

    moves = ["f2f3", "e7e5", "g2g4", "d8h4"]
    state = game
    for i, uci in enumerate(moves):
        resp = await _move(client, gid, f"cmd-{i}", expected_sequence=i, uci=uci)
        assert resp.status_code == 200, resp.text
        state = resp.json()
        assert state["sequence"] == i + 1

    assert state["status"] == "checkmate"
    assert state["result"] == "0-1"
    assert state["last_move"] == {"uci": "d8h4", "san": "Qh4#"}

    # Move list is complete and ordered.
    listed = await client.get(f"/v1/games/{gid}/moves")
    records = listed.json()
    assert [m["uci"] for m in records] == moves
    assert records[-1]["san"] == "Qh4#"


async def test_illegal_move_rejected(client) -> None:
    game = await _create_game(client)
    resp = await _move(client, game["game_id"], "cmd-x", 0, "e2e5")
    assert resp.status_code == 422
    assert resp.json()["error"] == "illegal_move"
    # State is unchanged.
    after = await client.get(f"/v1/games/{game['game_id']}")
    assert after.json()["sequence"] == 0


async def test_duplicate_command_is_idempotent(client) -> None:
    game = await _create_game(client)
    gid = game["game_id"]
    first = await _move(client, gid, "same-cmd", 0, "e2e4")
    assert first.status_code == 200
    assert first.json()["sequence"] == 1

    # Replaying the same command id must not create a second move or advance sequence.
    replay = await _move(client, gid, "same-cmd", 0, "e2e4")
    assert replay.status_code == 200
    assert replay.json()["sequence"] == 1

    listed = await client.get(f"/v1/games/{gid}/moves")
    assert len(listed.json()) == 1


async def test_stale_sequence_returns_recovery_state(client) -> None:
    game = await _create_game(client)
    gid = game["game_id"]
    await _move(client, gid, "cmd-0", 0, "e2e4")

    # Client thinks it is still at sequence 0.
    resp = await _move(client, gid, "cmd-stale", 0, "e7e5")
    assert resp.status_code == 409
    body = resp.json()
    assert body["error"] == "stale_sequence"
    assert body["current_sequence"] == 1
    assert body["state"]["sequence"] == 1


async def test_non_participant_cannot_move(client) -> None:
    game = await _create_game(client)
    resp = await _move(
        client, game["game_id"], "cmd-0", 0, "e2e4", headers={"X-Dev-User": "intruder-1"}
    )
    assert resp.status_code == 403
    assert resp.json()["error"] == "not_a_participant"


async def test_resign_finalizes_game(client) -> None:
    game = await _create_game(client)
    gid = game["game_id"]
    resp = await client.post(
        f"/v1/games/{gid}/resign", json={"command_id": "r-0", "expected_sequence": 0}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "resigned"
    # White resigned (white moves first / creator), so black wins.
    assert body["result"] == "0-1"

    # No further commands accepted.
    blocked = await _move(client, gid, "cmd-after", body["sequence"], "e2e4")
    assert blocked.status_code == 409
    assert blocked.json()["error"] == "game_not_active"
