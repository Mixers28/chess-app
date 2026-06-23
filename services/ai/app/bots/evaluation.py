from __future__ import annotations

import chess

# Centipawn material values. King is 0 — its loss is handled as checkmate.
PIECE_VALUES: dict[chess.PieceType, int] = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

# Compact midgame piece-square tables (White's POV, a1=0 .. h8=63), centipawns.
# Black mirrors via chess.square_mirror. Encourages development and central control.
_PAWN_PST = [
    0, 0, 0, 0, 0, 0, 0, 0,
    5, 10, 10, -20, -20, 10, 10, 5,
    5, -5, -10, 0, 0, -10, -5, 5,
    0, 0, 0, 20, 20, 0, 0, 0,
    5, 5, 10, 25, 25, 10, 5, 5,
    10, 10, 20, 30, 30, 20, 10, 10,
    50, 50, 50, 50, 50, 50, 50, 50,
    0, 0, 0, 0, 0, 0, 0, 0,
]
_KNIGHT_PST = [
    -50, -40, -30, -30, -30, -30, -40, -50,
    -40, -20, 0, 5, 5, 0, -20, -40,
    -30, 5, 10, 15, 15, 10, 5, -30,
    -30, 0, 15, 20, 20, 15, 0, -30,
    -30, 5, 15, 20, 20, 15, 5, -30,
    -30, 0, 10, 15, 15, 10, 0, -30,
    -40, -20, 0, 0, 0, 0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50,
]
_BISHOP_PST = [
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10, 5, 0, 0, 0, 0, 5, -10,
    -10, 10, 10, 10, 10, 10, 10, -10,
    -10, 0, 10, 10, 10, 10, 0, -10,
    -10, 5, 5, 10, 10, 5, 5, -10,
    -10, 0, 5, 10, 10, 5, 0, -10,
    -10, 0, 0, 0, 0, 0, 0, -10,
    -20, -10, -10, -10, -10, -10, -10, -20,
]

_PST: dict[chess.PieceType, list[int]] = {
    chess.PAWN: _PAWN_PST,
    chess.KNIGHT: _KNIGHT_PST,
    chess.BISHOP: _BISHOP_PST,
}

MATE_SCORE = 1_000_000


def evaluate(board: chess.Board) -> int:
    """Static evaluation in centipawns from the side-to-move's perspective.

    Positive = good for the player to move. Used by the search bot; also exposed as a
    rough position read. Terminal nodes are scored by the search, not here.
    """
    score = 0
    for piece_type, value in PIECE_VALUES.items():
        pst = _PST.get(piece_type)
        for sq in board.pieces(piece_type, chess.WHITE):
            score += value + (pst[sq] if pst else 0)
        for sq in board.pieces(piece_type, chess.BLACK):
            score -= value + (pst[chess.square_mirror(sq)] if pst else 0)
    return score if board.turn == chess.WHITE else -score
