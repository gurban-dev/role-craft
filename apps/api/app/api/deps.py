"""Authentication dependencies."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AuthError, ForbiddenError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
    session_cookie: Annotated[str | None, Cookie(alias="jaa_session")] = None,
) -> User:
    settings = get_settings()
    token: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif session_cookie:
        token = session_cookie
    if not token:
        raise AuthError("Authentication required")
    try:
        payload = decode_access_token(token, settings=settings)
        user_id = UUID(payload["sub"])
    except Exception as exc:
        raise AuthError("Invalid or expired session") from exc

    result = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if not user:
        raise AuthError("User not found")
    return user


async def require_csrf(
    request: Request,
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
    csrf_cookie: Annotated[str | None, Cookie(alias="jaa_csrf")] = None,
) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    settings = get_settings()
    if settings.app_env == "test":
        return
    if not csrf_header or not csrf_cookie or csrf_header != csrf_cookie:
        raise ForbiddenError("CSRF validation failed")


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
