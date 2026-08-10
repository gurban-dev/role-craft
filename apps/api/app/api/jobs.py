"""Job routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.integrations.job_sources.registry import list_job_sources
from app.schemas import JobMatchOut, JobOut, JobSearchRequest
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/sources")
async def sources() -> list[str]:
    return list_job_sources()


@router.get("", response_model=list[JobOut])
async def list_jobs(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[JobOut]:
    from sqlalchemy import select

    from app.models import Job

    result = await db.execute(select(Job).order_by(Job.discovered_at.desc()).limit(limit))
    return [JobOut.model_validate(j) for j in result.scalars().all()]


@router.post("/search", response_model=list[JobOut])
async def search_jobs(
    data: JobSearchRequest, user: CurrentUser, db: DbSession
) -> list[JobOut]:
    results = await JobService(db).search_and_persist(user, data)
    return [JobOut.model_validate(job) for job, _ in results]


@router.get("/matches", response_model=list[JobMatchOut])
async def list_matches(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[JobMatchOut]:
    matches = await JobService(db).list_matches(user, limit=limit)
    return [JobMatchOut.model_validate(m) for m in matches]


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: UUID, user: CurrentUser, db: DbSession) -> JobOut:
    job = await JobService(db).get_job(job_id)
    return JobOut.model_validate(job)
