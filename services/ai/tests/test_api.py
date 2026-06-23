from __future__ import annotations

import chess

START_FEN = chess.STARTING_FEN
# Fool's mate final position — white is checkmated, so no move can be produced.
CHECKMATED = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"


async def test_health(client) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_ready_reports_stockfish_absent(client) -> None:
    resp = await client.get("/ready")
    assert resp.status_code == 200
    assert resp.json() == {"ready": True, "stockfish_available": False}


async def test_difficulties_lists_baseline_only(client) -> None:
    resp = await client.get("/v1/difficulties")
    body = resp.json()
    assert body["stockfish_available"] is False
    assert set(body["difficulties"]) == {"random", "heuristic", "search"}


async def test_move_returns_legal_uci_and_san(client) -> None:
    resp = await client.post(
        "/v1/move",
        json={"fen": START_FEN, "difficulty": "search", "correlation_id": "trace-1"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["engine"] == "search"
    assert body["correlation_id"] == "trace-1"
    # Returned move must be legal in the supplied position.
    board = chess.Board(START_FEN)
    assert chess.Move.from_uci(body["uci"]) in board.legal_moves
    assert "think_ms" in body


async def test_stockfish_unavailable_returns_503(client) -> None:
    resp = await client.post("/v1/move", json={"fen": START_FEN, "difficulty": "stockfish"})
    assert resp.status_code == 503
    assert resp.json()["error"] == "engine_unavailable"


async def test_unknown_difficulty_returns_400(client) -> None:
    resp = await client.post("/v1/move", json={"fen": START_FEN, "difficulty": "wizard"})
    assert resp.status_code == 400
    assert resp.json()["error"] == "unknown_difficulty"


async def test_malformed_fen_returns_422(client) -> None:
    resp = await client.post("/v1/move", json={"fen": "not-a-fen", "difficulty": "random"})
    assert resp.status_code == 422
    assert resp.json()["error"] == "invalid_position"


async def test_terminal_position_returns_409(client) -> None:
    resp = await client.post("/v1/move", json={"fen": CHECKMATED, "difficulty": "random"})
    assert resp.status_code == 409
    assert resp.json()["error"] == "game_already_over"
