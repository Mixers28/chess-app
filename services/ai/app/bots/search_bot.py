from __future__ import annotations

import random

import chess

from app.bots.base import Bot, ChosenMove
from app.bots.evaluation import MATE_SCORE, PIECE_VALUES, evaluate
from app.schemas import Constraints


class SearchBot(Bot):
    """Negamax with alpha-beta pruning to a fixed depth.

    Finds short tactics (free captures, mate-in-N within the horizon) and avoids simple
    recaptures, which the heuristic bot cannot. Depth comes from the request constraints
    (``max_depth``), else the request ``level``, else the configured default.
    """

    name = "search"

    def __init__(self, default_depth: int = 3, rng: random.Random | None = None) -> None:
        self._default_depth = default_depth
        self._rng = rng or random.Random()

    async def choose(
        self, board: chess.Board, constraints: Constraints, level: int | None = None
    ) -> ChosenMove:
        depth = constraints.max_depth or level or self._default_depth
        alpha, beta = -MATE_SCORE * 2, MATE_SCORE * 2
        best_score = -MATE_SCORE * 2
        best_moves: list[chess.Move] = []

        for move in self._ordered(board):
            board.push(move)
            score = -self._negamax(board, depth - 1, -beta, -alpha, ply=1)
            board.pop()
            if score > best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)
            alpha = max(alpha, best_score)

        move = self._rng.choice(best_moves)
        return ChosenMove(move=move, evaluation=round(best_score / 100, 2), depth=depth)

    def _negamax(self, board: chess.Board, depth: int, alpha: int, beta: int, ply: int) -> int:
        if board.is_checkmate():
            return -(MATE_SCORE - ply)  # being mated; nearer mate is worse
        if depth == 0:
            return evaluate(board)
        if not any(board.legal_moves):  # stalemate
            return 0
        if board.is_insufficient_material() or board.can_claim_draw():
            return 0

        best = -MATE_SCORE * 2
        for move in self._ordered(board):
            board.push(move)
            score = -self._negamax(board, depth - 1, -beta, -alpha, ply + 1)
            board.pop()
            if score > best:
                best = score
            if best > alpha:
                alpha = best
            if alpha >= beta:
                break  # opponent won't allow this line
        return best

    @staticmethod
    def _ordered(board: chess.Board) -> list[chess.Move]:
        """Captures and promotions first (MVV-LVA-ish) to maximize pruning."""

        def key(move: chess.Move) -> int:
            score = 0
            if board.is_capture(move):
                victim = board.piece_at(move.to_square)
                attacker = board.piece_at(move.from_square)
                victim_val = PIECE_VALUES[victim.piece_type] if victim else 100  # en passant
                attacker_val = PIECE_VALUES[attacker.piece_type] if attacker else 0
                score += 1000 + victim_val - attacker_val
            if move.promotion:
                score += PIECE_VALUES.get(move.promotion, 0)
            return score

        return sorted(board.legal_moves, key=key, reverse=True)
