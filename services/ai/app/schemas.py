from __future__ import annotations

from pydantic import BaseModel, Field


class Constraints(BaseModel):
    """Optional per-move limits. Applied by search/engine bots; ignored by random."""

    movetime_ms: int | None = Field(default=None, ge=1, le=60_000)
    max_depth: int | None = Field(default=None, ge=1, le=30)


class MoveRequest(BaseModel):
    fen: str = Field(..., description="Position to move in, FEN")
    difficulty: str = Field(
        default="heuristic", description="random | heuristic | search | stockfish"
    )
    # Generic strength knob: depth for search, Skill Level (0-20) for stockfish.
    level: int | None = Field(default=None, ge=0, le=30)
    constraints: Constraints | None = None
    # Correlation id propagated from the game service for tracing.
    correlation_id: str | None = Field(default=None, max_length=64)


class MoveResponse(BaseModel):
    uci: str
    san: str
    difficulty: str
    engine: str
    evaluation: float | None = Field(default=None, description="Pawns, from side-to-move POV")
    depth: int | None = None
    think_ms: int
    correlation_id: str | None = None


class DifficultiesResponse(BaseModel):
    difficulties: list[str]
    stockfish_available: bool
