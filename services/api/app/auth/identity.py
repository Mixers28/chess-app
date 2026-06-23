from __future__ import annotations

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models import User
from app.db.session import get_session


async def get_current_user(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    x_dev_user: str | None = Header(default=None),
) -> User:
    """Development identity seam.

    Phase 1 has no real authentication. The caller is identified by the optional
    ``X-Dev-User`` header, falling back to ``CHESS_DEV_USER_ID``. The user row is
    created on first sight so the domain never hard-codes auth assumptions. This is
    the single function Phase 4 (Sign in with Apple) replaces — nothing downstream
    knows how identity was established.
    """
    user_id = x_dev_user or settings.dev_user_id
    user = await session.get(User, user_id)
    if user is None:
        user = User(id=user_id, username=f"dev-{user_id[:8]}")
        session.add(user)
        await session.flush()
    return user


async def ensure_user(session: AsyncSession, user_id: str) -> User:
    user = await session.get(User, user_id)
    if user is None:
        user = User(id=user_id, username=f"dev-{user_id[:8]}")
        session.add(user)
        await session.flush()
    return user
