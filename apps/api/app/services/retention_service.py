"""Data retention cleanup."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models import AiUsage, Application, AutomationRun
from app.models.enums import ApplicationStatus

logger = get_logger(__name__)


class RetentionService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    async def cleanup(self) -> dict[str, int]:
        deleted = {
            "applications": await self._cleanup_applications(),
            "automation_runs": await self._cleanup_runs(),
            "ai_usage": await self._cleanup_ai_usage(),
        }
        logger.info("retention_cleanup_done", **deleted)
        return deleted

    async def _cleanup_applications(self) -> int:
        days = self.settings.retention_days_applications
        if days <= 0:
            return 0
        cutoff = datetime.now(UTC) - timedelta(days=days)
        # Only purge terminal submitted/rejected/withdrawn older than retention
        result = await self.db.execute(
            delete(Application).where(
                Application.updated_at < cutoff,
                Application.status.in_(
                    [
                        ApplicationStatus.SUBMITTED.value,
                        ApplicationStatus.REJECTED.value,
                        ApplicationStatus.WITHDRAWN.value,
                    ]
                ),
            )
        )
        await self.db.flush()
        return int(result.rowcount or 0)

    async def _cleanup_runs(self) -> int:
        days = self.settings.retention_days_automation_runs
        if days <= 0:
            return 0
        cutoff = datetime.now(UTC) - timedelta(days=days)
        result = await self.db.execute(
            delete(AutomationRun).where(AutomationRun.created_at < cutoff)
        )
        await self.db.flush()
        return int(result.rowcount or 0)

    async def _cleanup_ai_usage(self) -> int:
        days = self.settings.retention_days_ai_usage
        if days <= 0:
            return 0
        cutoff = datetime.now(UTC) - timedelta(days=days)
        result = await self.db.execute(delete(AiUsage).where(AiUsage.created_at < cutoff))
        await self.db.flush()
        return int(result.rowcount or 0)
