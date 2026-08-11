"""Profile routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DbSession, require_csrf
from app.schemas import CandidateProfileOut, CandidateProfileUpdate
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/profile", tags=["profile"], dependencies=[Depends(require_csrf)])


@router.get("", response_model=CandidateProfileOut)
async def get_profile(user: CurrentUser, db: DbSession) -> CandidateProfileOut:
    profile = await ProfileService(db).get(user.id)
    return CandidateProfileOut.model_validate(profile)


@router.patch("", response_model=CandidateProfileOut)
@router.put("", response_model=CandidateProfileOut)
async def update_profile(
    data: CandidateProfileUpdate, user: CurrentUser, db: DbSession
) -> CandidateProfileOut:
    profile = await ProfileService(db).update(user, data)
    return CandidateProfileOut.model_validate(profile)
