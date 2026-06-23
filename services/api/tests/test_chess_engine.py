from __future__ import annotations

import pytest

from app.games import chess_engine
from app.games.errors import IllegalMove


def test_initial_side_to_move() -> None:
    assert chess_engine.side_to_move(chess_engine.INITIAL_FEN) == "white"


def test_legal_move_produces_san_and_advances_turn() -> None:
    outcome = chess_engine.apply_move(chess_engine.INITIAL_FEN, "e2e4")
    assert outcome.san == "e4"
    assert outcome.turn == "black"
    assert outcome.status == "active"
    assert outcome.result is None


def test_illegal_move_rejected() -> None:
    with pytest.raises(IllegalMove):
        chess_engine.apply_move(chess_engine.INITIAL_FEN, "e2e5")


def test_malformed_uci_rejected() -> None:
    with pytest.raises(IllegalMove):
        chess_engine.apply_move(chess_engine.INITIAL_FEN, "not-a-move")


def test_fools_mate_detected_as_checkmate() -> None:
    fen = chess_engine.INITIAL_FEN
    moves = ["f2f3", "e7e5", "g2g4", "d8h4"]
    outcome = None
    for uci in moves:
        outcome = chess_engine.apply_move(fen, uci)
        fen = outcome.fen_after
    assert outcome is not None
    assert outcome.status == "checkmate"
    assert outcome.result == "0-1"


def test_build_pgn_roundtrips_moves() -> None:
    pgn = chess_engine.build_pgn(["e2e4", "e7e5", "g1f3"], result=None)
    assert "1. e4 e5 2. Nf3" in pgn
