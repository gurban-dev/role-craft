"""Resume routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.schemas import ResumeOut
from app.services.resume_service import ResumeService

router = APIRouter(prefix="/resumes", tags=["resumes"])


class TailorRequest(BaseModel):
    job_id: UUID


@router.post("/tailor", response_model=ResumeOut)
async def tailor_resume(
    data: TailorRequest, user: CurrentUser, db: DbSession
) -> ResumeOut:
    resume = await ResumeService(db).tailor_for_job(user, data.job_id)
    return ResumeOut.model_validate(resume)


@router.get("/{resume_id}", response_model=ResumeOut)
async def get_resume(resume_id: UUID, user: CurrentUser, db: DbSession) -> ResumeOut:
    resume = await ResumeService(db).get(resume_id, user.id)
    return ResumeOut.model_validate(resume)
