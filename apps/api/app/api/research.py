"""Company research routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession, require_csrf
from app.schemas import ResearchOut
from app.services.rate_limit import RateLimitService
from app.services.research_service import ResearchService

router = APIRouter(prefix="/research", tags=["research"], dependencies=[Depends(require_csrf)])


class ResearchRequest(BaseModel):
    job_id: UUID


@router.get("", response_model=list[ResearchOut])
async def list_research(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[ResearchOut]:
    rows = await ResearchService(db).list_for_user(user.id, limit=limit)
    return [ResearchOut.model_validate(r) for r in rows]


@router.post("", response_model=ResearchOut)
async def research_company(
    data: ResearchRequest, user: CurrentUser, db: DbSession
) -> ResearchOut:
    RateLimitService().check_research(str(user.id))
    row = await ResearchService(db).research_company(user, data.job_id)
    return ResearchOut.model_validate(row)


@router.get("/{research_id}", response_model=ResearchOut)
async def get_research(
    research_id: UUID, user: CurrentUser, db: DbSession
) -> ResearchOut:
    row = await ResearchService(db).get(research_id, user.id)
    return ResearchOut.model_validate(row)
