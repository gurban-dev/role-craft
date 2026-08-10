"""Application repository."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Application
from app.models.enums import ApplicationStatus


class ApplicationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, application_id: UUID) -> Application | None:
        result = await self.db.execute(select(Application).where(Application.id == application_id))
        return result.scalar_one_or_none()

    async def get_by_user_job(self, user_id: UUID, job_id: UUID) -> Application | None:
        result = await self.db.execute(
            select(Application).where(
                Application.user_id == user_id, Application.job_id == job_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, key: str) -> Application | None:
        result = await self.db.execute(
            select(Application).where(Application.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: UUID, *, status: str | None = None, limit: int = 100
    ) -> list[Application]:
        stmt = select(Application).where(Application.user_id == user_id)
        if status:
            stmt = stmt.where(Application.status == status)
        stmt = stmt.order_by(Application.updated_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_submitted_today(self, user_id: UUID) -> int:
        start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.db.execute(
            select(func.count())
            .select_from(Application)
            .where(
                Application.user_id == user_id,
                Application.status == ApplicationStatus.SUBMITTED.value,
                Application.submitted_at >= start,
            )
        )
        return int(result.scalar_one())

    async def count_by_status(self, user_id: UUID) -> dict[str, int]:
        result = await self.db.execute(
            select(Application.status, func.count())
            .where(Application.user_id == user_id)
            .group_by(Application.status)
        )
        return {row[0]: int(row[1]) for row in result.all()}
