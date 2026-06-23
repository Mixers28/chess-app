from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid

# --- Enumerated values (kept as strings for portability across SQLite/Postgres) ---
GAME_MODES = ("local", "ai")
GAME_STATUSES = ("active", "checkmate", "stalemate", "draw", "resigned")
COLORS = ("white", "black")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    apple_user_id: Mapped[str | None] = mapped_column(String(255), unique=True, default=None)
    username: Mapped[str | None] = mapped_column(String(64), default=None)
    rating: Mapped[int] = mapped_column(Integer, default=1200, nullable=False)


class Game(Base, TimestampMixin):
    __tablename__ = "games"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    white_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    black_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), default=None)

    mode: Mapped[str] = mapped_column(String(16), default="local", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    result: Mapped[str | None] = mapped_column(String(8), default=None)  # 1-0, 0-1, 1/2-1/2

    current_fen: Mapped[str] = mapped_column(String(120), nullable=False)
    pgn: Mapped[str | None] = mapped_column(Text, default=None)
    time_control: Mapped[str | None] = mapped_column(String(32), default=None)

    # Monotonic per-game sequence number. Increments on every committed transition;
    # clients submit the sequence they believe they are extending.
    sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    moves: Mapped[list[Move]] = relationship(
        back_populates="game", order_by="Move.ply", cascade="all, delete-orphan"
    )


class Move(Base):
    __tablename__ = "moves"
    __table_args__ = (
        # Idempotency: a command may be retried but applied at most once per game.
        UniqueConstraint("game_id", "command_id", name="uq_moves_game_command"),
        # Immutable ordering: one move per ply per game.
        UniqueConstraint("game_id", "ply", name="uq_moves_game_ply"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"), nullable=False, index=True)
    ply: Mapped[int] = mapped_column(Integer, nullable=False)
    player_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    color: Mapped[str] = mapped_column(String(5), nullable=False)

    uci_move: Mapped[str] = mapped_column(String(6), nullable=False)
    san_move: Mapped[str] = mapped_column(String(12), nullable=False)
    fen_after: Mapped[str] = mapped_column(String(120), nullable=False)
    command_id: Mapped[str] = mapped_column(String(64), nullable=False)

    # Telemetry for AI-produced moves; NULL for human moves.
    engine: Mapped[str | None] = mapped_column(String(32), default=None)
    think_ms: Mapped[int | None] = mapped_column(Integer, default=None)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    game: Mapped[Game] = relationship(back_populates="moves")


class AiGame(Base):
    """Per-AI-game record: which opponent the human faced. One row per ai-mode game."""

    __tablename__ = "ai_games"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"), nullable=False, unique=True)
    human_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(16), nullable=False)
    level: Mapped[int | None] = mapped_column(Integer, default=None)
    # Reserved for a future custom model id; bot name otherwise lives on each move.
    model_version: Mapped[str | None] = mapped_column(String(32), default=None)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
