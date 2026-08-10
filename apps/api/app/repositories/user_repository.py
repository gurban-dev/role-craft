"""User repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import CandidateProfile, User, UserSettings


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def get_with_profile(self, user_id: UUID) -> User | None:
        result = await self.db.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.profile), selectinload(User.settings))
        )
        return result.scalar_one_or_none()

    async def get_profile(self, user_id: UUID) -> CandidateProfile | None:
        result = await self.db.execute(
            select(CandidateProfile).where(CandidateProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_settings(self, user_id: UUID) -> UserSettings | None:
        result = await self.db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
        return result.scalar_one_or_none()
