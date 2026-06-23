from __future__ import annotations

import chess
import pytest

from app.bots.heuristic_bot import HeuristicBot
from app.bots.random_bot import RandomBot
from app.bots.search_bot import SearchBot
from app.schemas import Constraints

# White to move with a free, undefended black queen on e5 (Qe2xe5).
FREE_QUEEN = "4k3/8/8/4q3/8/8/4Q3/4K3 w - - 0 1"
# White to move, Ra1-a8 is mate (black king boxed by its own pawns).
MATE_IN_1 = "6k1/5ppp/8/8/8/8/8/R6K w - - 0 1"


async def test_random_returns_a_legal_move() -> None:
    board = chess.Board()
    chosen = await RandomBot().choose(board, Constraints(), None)
    assert chosen.move in board.legal_moves


async def test_heuristic_grabs_free_queen() -> None:
    board = chess.Board(FREE_QUEEN)
    chosen = await HeuristicBot().choose(board, Constraints(), None)
    assert chosen.move.uci() == "e2e5"


async def test_search_finds_mate_in_one() -> None:
    board = chess.Board(MATE_IN_1)
    chosen = await SearchBot(default_depth=3).choose(board, Constraints(), None)
    assert chosen.move.uci() == "a1a8"


async def test_search_grabs_free_queen() -> None:
    board = chess.Board(FREE_QUEEN)
    chosen = await SearchBot(default_depth=2).choose(board, Constraints(), None)
    assert chosen.move.uci() == "e2e5"


@pytest.mark.parametrize("depth", [1, 2, 3])
async def test_search_depth_respects_constraint(depth: int) -> None:
    board = chess.Board()
    chosen = await SearchBot().choose(board, Constraints(max_depth=depth), None)
    assert chosen.depth == depth
    assert chosen.move in board.legal_moves
