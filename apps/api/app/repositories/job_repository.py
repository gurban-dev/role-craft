"""Job repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, JobMatch


class JobRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, job_id: UUID) -> Job | None:
        result = await self.db.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    async def get_by_source_external(self, source: str, external_job_id: str) -> Job | None:
        result = await self.db.execute(
            select(Job).where(Job.source == source, Job.external_job_id == external_job_id)
        )
        return result.scalar_one_or_none()

    async def get_by_normalized_key(self, key: str) -> Job | None:
        result = await self.db.execute(select(Job).where(Job.normalized_key == key))
        return result.scalar_one_or_none()

    async def list_recent(self, *, limit: int = 50) -> list[Job]:
        result = await self.db.execute(
            select(Job).order_by(Job.discovered_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get_match(self, job_id: UUID, candidate_id: UUID) -> JobMatch | None:
        result = await self.db.execute(
            select(JobMatch).where(
                JobMatch.job_id == job_id, JobMatch.candidate_id == candidate_id
            )
        )
        return result.scalar_one_or_none()
