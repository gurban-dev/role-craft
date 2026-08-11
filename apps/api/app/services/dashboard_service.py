"""Dashboard statistics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Application, Job, JobMatch, User
from app.models.enums import ApplicationStatus
from app.repositories.application_repository import ApplicationRepository
from app.repositories.user_repository import UserRepository
from app.schemas import DashboardStats


class DashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.apps = ApplicationRepository(db)
        self.users = UserRepository(db)

    async def stats(self, user: User) -> DashboardStats:
        settings = await self.users.get_settings(user.id)
        daily_target = (
            settings.daily_application_limit
            if settings
            else user.daily_application_limit
        )
        submitted_today = await self.apps.count_submitted_today(user.id)
        by_status = await self.apps.count_by_status(user.id)

        in_progress_statuses = {
            ApplicationStatus.DISCOVERED.value,
            ApplicationStatus.ANALYZING.value,
            ApplicationStatus.MATCHED.value,
            ApplicationStatus.RESUME_GENERATING.value,
            ApplicationStatus.RESUME_READY.value,
            ApplicationStatus.CONTACT_RESEARCH.value,
            ApplicationStatus.READY_FOR_REVIEW.value,
            ApplicationStatus.APPLYING.value,
        }
        in_progress = sum(by_status.get(s, 0) for s in in_progress_statuses)
        needs_human = by_status.get(ApplicationStatus.NEEDS_HUMAN_ACTION.value, 0)

        week_start = datetime.now(UTC) - timedelta(days=7)
        submitted_week = int(
            (
                await self.db.execute(
                    select(func.count())
                    .select_from(Application)
                    .where(
                        Application.user_id == user.id,
                        Application.status == ApplicationStatus.SUBMITTED.value,
                        Application.submitted_at >= week_start,
                    )
                )
            ).scalar_one()
        )

        profile = await self.users.get_profile(user.id)
        avg_score = None
        if profile:
            avg_score = (
                await self.db.execute(
                    select(func.avg(JobMatch.overall_score)).where(
                        JobMatch.candidate_id == profile.id
                    )
                )
            ).scalar_one_or_none()
            if avg_score is not None:
                avg_score = float(avg_score)

        by_source_rows = (
            await self.db.execute(
                select(Job.source, func.count())
                .join(Application, Application.job_id == Job.id)
                .where(Application.user_id == user.id)
                .group_by(Job.source)
            )
        ).all()
        by_company_rows = (
            await self.db.execute(
                select(Job.company, func.count())
                .join(Application, Application.job_id == Job.id)
                .where(Application.user_id == user.id)
                .group_by(Job.company)
                .order_by(func.count().desc())
                .limit(20)
            )
        ).all()

        rejected_by_quality = 0
        qg_apps = (
            await self.db.execute(
                select(Application).where(
                    Application.user_id == user.id,
                    Application.status == ApplicationStatus.NEEDS_HUMAN_ACTION.value,
                )
            )
        ).scalars().all()
        for a in qg_apps:
            gate = a.quality_gate or {}
            if gate.get("passed") is False:
                rejected_by_quality += 1

        submitted_apps = (
            await self.db.execute(
                select(Application).where(
                    Application.user_id == user.id,
                    Application.status == ApplicationStatus.SUBMITTED.value,
                )
            )
        ).scalars().all()
        submitted_count = len(submitted_apps)
        response_rate = None
        interview_rate = None
        if submitted_count > 0:
            responded = sum(
                1
                for a in submitted_apps
                if a.confirmation_text or a.confirmation_url or a.external_application_id
            )
            interviews = sum(
                1
                for a in submitted_apps
                if (a.application_answers or {}).get("outcome") == "interview"
                or (a.quality_gate or {}).get("interview") is True
            )
            response_rate = round(responded / submitted_count, 4)
            interview_rate = round(interviews / submitted_count, 4)

        return DashboardStats(
            daily_target=daily_target,
            submitted_today=submitted_today,
            in_progress=in_progress,
            needs_human_action=needs_human,
            rejected_by_quality=rejected_by_quality,
            remaining=max(0, daily_target - submitted_today),
            submitted_this_week=submitted_week,
            average_match_score=avg_score,
            response_rate=response_rate,
            interview_rate=interview_rate,
            by_source={r[0]: int(r[1]) for r in by_source_rows},
            by_company={r[0]: int(r[1]) for r in by_company_rows},
            pipeline=by_status,
        )
