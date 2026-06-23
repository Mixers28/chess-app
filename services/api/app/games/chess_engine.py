from __future__ import annotations

from dataclasses import dataclass

import chess
import chess.pgn

from app.games.errors import IllegalMove

INITIAL_FEN = chess.STARTING_FEN

# Map python-chess outcome to our persisted (status, result) pair.
_TERMINATION_STATUS = {
    chess.Termination.CHECKMATE: "checkmate",
    chess.Termination.STALEMATE: "stalemate",
    chess.Termination.INSUFFICIENT_MATERIAL: "draw",
    chess.Termination.SEVENTYFIVE_MOVES: "draw",
    chess.Termination.FIVEFOLD_REPETITION: "draw",
    chess.Termination.FIFTY_MOVES: "draw",
    chess.Termination.THREEFOLD_REPETITION: "draw",
}


@dataclass(frozen=True)
class MoveOutcome:
    san: str
    fen_after: str
    turn: str  # side to move after this move: "white" | "black"
    status: str  # active | checkmate | stalemate | draw
    result: str | None  # 1-0 | 0-1 | 1/2-1/2 | None while active


def side_to_move(fen: str) -> str:
    return "white" if chess.Board(fen).turn == chess.WHITE else "black"


def apply_move(fen: str, uci: str) -> MoveOutcome:
    """Validate ``uci`` against ``fen`` and return the resulting canonical outcome.

    Raises :class:`IllegalMove` for malformed or illegal moves. This is the single
    authority for legality — every human and AI move passes through here.
    """
    board = chess.Board(fen)
    try:
        move = chess.Move.from_uci(uci)
    except ValueError as exc:
        raise IllegalMove(f"malformed UCI '{uci}'") from exc
    if move not in board.legal_moves:
        raise IllegalMove(f"illegal move '{uci}' in position {fen}")

    san = board.san(move)
    board.push(move)

    status, result = _status_for(board)
    turn = "white" if board.turn == chess.WHITE else "black"
    return MoveOutcome(san=san, fen_after=board.fen(), turn=turn, status=status, result=result)


def _status_for(board: chess.Board) -> tuple[str, str | None]:
    # claim_draw=True so threefold/fifty-move are treated as terminal when claimable.
    outcome = board.outcome(claim_draw=True)
    if outcome is None:
        return "active", None
    status = _TERMINATION_STATUS.get(outcome.termination, "draw")
    return status, outcome.result()


def build_pgn(uci_moves: list[str], result: str | None) -> str:
    """Reconstruct a PGN from the ordered UCI move list (source of truth = DB)."""
    game = chess.pgn.Game()
    if result:
        game.headers["Result"] = result
    node: chess.pgn.GameNode = game
    board = chess.Board()
    for uci in uci_moves:
        move = chess.Move.from_uci(uci)
        node = node.add_variation(move)
        board.push(move)
    exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
    return game.accept(exporter)
