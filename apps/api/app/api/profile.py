"""Profile routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DbSession, require_csrf
from app.schemas import CandidateProfileOut, CandidateProfileUpdate, ResumeExtractRequest
from app.services.candidate_profile_extractor import CandidateProfileExtractor
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


@router.post("/extract-from-resume", response_model=CandidateProfileOut)
async def extract_from_resume(
    data: ResumeExtractRequest, user: CurrentUser, db: DbSession
) -> CandidateProfileOut:
    """Parse resume text into structured profile fields (authoritative skills source)."""
    profile = await ProfileService(db).get(user.id)
    extractor = CandidateProfileExtractor(db)
    structured = await extractor.extract_from_resume_text(
        data.resume_text, user_id=str(user.id)
    )
    await extractor.persist(profile, structured)
    return CandidateProfileOut.model_validate(profile)
