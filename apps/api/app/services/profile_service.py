"""Candidate profile service."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models import CandidateProfile, User
from app.repositories.user_repository import UserRepository
from app.schemas import CandidateProfileUpdate
from app.services.audit_service import AuditService


class ProfileService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.audit = AuditService(db)

    async def get(self, user_id: UUID) -> CandidateProfile:
        profile = await self.users.get_profile(user_id)
        if not profile:
            raise NotFoundError("Profile not found")
        return profile

    async def update(self, user: User, data: CandidateProfileUpdate) -> CandidateProfile:
        profile = await self.get(user.id)
        payload = data.model_dump(exclude_unset=True)
        for key, value in payload.items():
            setattr(profile, key, value)
        await self.db.flush()
        await self.db.refresh(profile)
        await self.audit.log(
            actor=str(user.id),
            action="profile.update",
            entity_type="candidate_profile",
            entity_id=profile.id,
            details={"fields": list(payload.keys())},
        )
        return profile
