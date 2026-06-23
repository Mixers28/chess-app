from __future__ import annotations

from pydantic import BaseModel, Field


class CreateGameRequest(BaseModel):
    mode: str = Field(default="local", description="local (hotseat) or ai")
    time_control: str | None = None
    # ai-mode only:
    difficulty: str = Field(default="heuristic", description="AI opponent difficulty")
    level: int | None = Field(default=None, description="AI strength knob (engine-specific)")
    color: str = Field(default="white", description="Human's color in an ai game")


class LastMove(BaseModel):
    uci: str
    san: str


class GameState(BaseModel):
    """Canonical game state returned by every command and query."""

    game_id: str
    sequence: int
    fen: str
    turn: str
    status: str
    result: str | None
    last_move: LastMove | None = None
    white_user_id: str
    black_user_id: str | None
    mode: str


class SubmitMoveRequest(BaseModel):
    command_id: str = Field(..., max_length=64, description="Client-generated idempotency key")
    expected_sequence: int = Field(..., ge=0, description="Sequence the client is extending")
    move: str = Field(..., max_length=6, description="Move in UCI, e.g. e2e4 or e7e8q")


class ResignRequest(BaseModel):
    command_id: str = Field(..., max_length=64)
    expected_sequence: int = Field(..., ge=0)


class MoveRecord(BaseModel):
    ply: int
    color: str
    uci: str
    san: str
    fen_after: str
    engine: str | None = None  # set for AI moves
    think_ms: int | None = None

    model_config = {"from_attributes": True}
