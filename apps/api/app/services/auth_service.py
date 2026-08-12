"""Auth service."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError, ConflictError
from app.core.security import (
    create_access_token,
    generate_csrf_token,
    hash_password,
    verify_password,
)
from app.models import CandidateProfile, User, UserSettings
from app.schemas import LoginRequest, RegisterRequest


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(self, data: RegisterRequest) -> tuple[User, str, str]:
        existing = await self.db.execute(select(User).where(User.email == data.email.lower()))
        if existing.scalar_one_or_none():
            raise ConflictError("Email already registered")
        user = User(
            email=data.email.lower(),
            name=data.name,
            hashed_password=hash_password(data.password),
            auth_providers=["password"],
        )
        self.db.add(user)
        await self.db.flush()
        self.db.add(CandidateProfile(user_id=user.id))
        self.db.add(UserSettings(user_id=user.id, auto_submit_enabled=False))
        await self.db.flush()
        token = create_access_token(str(user.id))
        csrf = generate_csrf_token()
        return user, token, csrf

    async def login(self, data: LoginRequest) -> tuple[User, str, str]:
        result = await self.db.execute(select(User).where(User.email == data.email.lower()))
        user = result.scalar_one_or_none()
        if not user:
            raise AuthError("Invalid email or password")
        if not user.hashed_password:
            raise AuthError("This account uses Google sign-in. Continue with Google instead.")
        if not verify_password(data.password, user.hashed_password):
            raise AuthError("Invalid email or password")
        token = create_access_token(str(user.id))
        csrf = generate_csrf_token()
        return user, token, csrf
