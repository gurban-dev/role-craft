"""Company research routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.schemas import ResearchOut
from app.services.research_service import ResearchService

router = APIRouter(prefix="/research", tags=["research"])


class ResearchRequest(BaseModel):
    job_id: UUID


@router.post("", response_model=ResearchOut)
async def research_company(
    data: ResearchRequest, user: CurrentUser, db: DbSession
) -> ResearchOut:
    row = await ResearchService(db).research_company(user, data.job_id)
    return ResearchOut.model_validate(row)


@router.get("/{research_id}", response_model=ResearchOut)
async def get_research(
    research_id: UUID, user: CurrentUser, db: DbSession
) -> ResearchOut:
    row = await ResearchService(db).get(research_id, user.id)
    return ResearchOut.model_validate(row)
