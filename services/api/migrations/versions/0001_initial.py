"""initial schema: users, games, moves

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-13
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("apple_user_id", sa.String(length=255), unique=True, nullable=True),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False, server_default="1200"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "games",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("white_user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("black_user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("mode", sa.String(length=16), nullable=False, server_default="local"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("result", sa.String(length=8), nullable=True),
        sa.Column("current_fen", sa.String(length=120), nullable=False),
        sa.Column("pgn", sa.Text(), nullable=True),
        sa.Column("time_control", sa.String(length=32), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "moves",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("game_id", sa.String(length=36), sa.ForeignKey("games.id"), nullable=False),
        sa.Column("ply", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("color", sa.String(length=5), nullable=False),
        sa.Column("uci_move", sa.String(length=6), nullable=False),
        sa.Column("san_move", sa.String(length=12), nullable=False),
        sa.Column("fen_after", sa.String(length=120), nullable=False),
        sa.Column("command_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("game_id", "command_id", name="uq_moves_game_command"),
        sa.UniqueConstraint("game_id", "ply", name="uq_moves_game_ply"),
    )
    op.create_index("ix_moves_game_id", "moves", ["game_id"])


def downgrade() -> None:
    op.drop_index("ix_moves_game_id", table_name="moves")
    op.drop_table("moves")
    op.drop_table("games")
    op.drop_table("users")
