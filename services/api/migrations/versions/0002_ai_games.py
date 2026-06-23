"""ai games + move telemetry

Revision ID: 0002_ai_games
Revises: 0001_initial
Create Date: 2026-06-13
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_ai_games"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("moves", sa.Column("engine", sa.String(length=32), nullable=True))
    op.add_column("moves", sa.Column("think_ms", sa.Integer(), nullable=True))

    op.create_table(
        "ai_games",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "game_id",
            sa.String(length=36),
            sa.ForeignKey("games.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "human_user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("difficulty", sa.String(length=16), nullable=False),
        sa.Column("level", sa.Integer(), nullable=True),
        sa.Column("model_version", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("ai_games")
    op.drop_column("moves", "think_ms")
    op.drop_column("moves", "engine")
