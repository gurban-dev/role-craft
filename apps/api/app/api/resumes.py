"""Resume routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession, require_csrf
from app.schemas import ResumeOut
from app.services.rate_limit import RateLimitService
from app.services.resume_service import ResumeService

router = APIRouter(prefix="/resumes", tags=["resumes"], dependencies=[Depends(require_csrf)])


class TailorRequest(BaseModel):
    job_id: UUID


@router.get("", response_model=list[ResumeOut])
async def list_resumes(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[ResumeOut]:
    resumes = await ResumeService(db).list_for_user(user.id, limit=limit)
    return [ResumeOut.model_validate(r) for r in resumes]


@router.post("/tailor", response_model=ResumeOut)
async def tailor_resume(
    data: TailorRequest, user: CurrentUser, db: DbSession
) -> ResumeOut:
    RateLimitService().check_llm(str(user.id))
    resume = await ResumeService(db).tailor_for_job(user, data.job_id)
    return ResumeOut.model_validate(resume)


@router.get("/{resume_id}", response_model=ResumeOut)
async def get_resume(resume_id: UUID, user: CurrentUser, db: DbSession) -> ResumeOut:
    resume = await ResumeService(db).get(resume_id, user.id)
    return ResumeOut.model_validate(resume)
