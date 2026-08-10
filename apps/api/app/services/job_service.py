"""Job discovery, persistence, and match scoring."""

from __future__ import annotations

import hashlib
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.integrations.job_sources.base import DiscoveredJob, JobSearchCriteria
from app.integrations.job_sources.registry import get_job_source, list_job_sources
from app.models import Application, CandidateProfile, Job, JobMatch, User
from app.models.enums import ApplicationStatus, JobStatus
from app.repositories.job_repository import JobRepository
from app.repositories.user_repository import UserRepository
from app.schemas import JobSearchRequest
from app.services.scoring_service import ScoringService

logger = get_logger(__name__)


def normalize_job_key(company: str, title: str, location: str | None = None) -> str:
    def _clean(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

    parts = [_clean(company), _clean(title)]
    if location:
        parts.append(_clean(location))
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:64]


class JobService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.jobs = JobRepository(db)
        self.users = UserRepository(db)
        self.scoring = ScoringService()

    async def search_and_persist(
        self, user: User, request: JobSearchRequest
    ) -> list[tuple[Job, JobMatch | None]]:
        sources = request.sources or list_job_sources()
        criteria = JobSearchCriteria(
            query=request.query,
            location=request.location,
            remote_only=request.remote_only,
            limit=request.limit,
        )
        discovered: list[DiscoveredJob] = []
        for name in sources:
            try:
                source = get_job_source(name)
                discovered.extend(await source.search(criteria))
            except Exception as exc:
                logger.warning("job_source_failed", source=name, error=str(exc))

        profile = await self.users.get_profile(user.id)
        results: list[tuple[Job, JobMatch | None]] = []
        seen_keys: set[str] = set()

        for item in discovered:
            key = normalize_job_key(item.company, item.title, item.location)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            existing = await self.jobs.get_by_source_external(item.source, item.external_job_id)
            if existing is None:
                by_key = await self.jobs.get_by_normalized_key(key)
                if by_key is not None:
                    existing = by_key

            if existing:
                job = existing
            else:
                job = Job(
                    title=item.title,
                    company=item.company,
                    location=item.location,
                    remote_status=item.remote_status,
                    salary_min=item.salary_min,
                    salary_max=item.salary_max,
                    salary_currency=item.salary_currency,
                    description=item.description,
                    requirements=item.requirements,
                    responsibilities=item.responsibilities,
                    technologies=item.technologies,
                    source=item.source,
                    source_url=item.source_url,
                    official_application_url=item.official_application_url,
                    external_job_id=item.external_job_id,
                    closing_date=item.closing_date,
                    status=JobStatus.ACTIVE.value,
                    normalized_key=key,
                    raw_payload=item.raw_payload,
                )
                self.db.add(job)
                await self.db.flush()

            match = None
            if profile:
                match = await self._upsert_match(job, profile)
                await self._ensure_application(user, job, profile, match)

            results.append((job, match))
            if len(results) >= request.limit:
                break

        logger.info("jobs_persisted", user_id=str(user.id), count=len(results))
        return results

    async def _upsert_match(self, job: Job, profile: CandidateProfile) -> JobMatch:
        score = self.scoring.score(job, profile)
        existing = await self.jobs.get_match(job.id, profile.id)
        if existing:
            existing.overall_score = score.overall_score
            existing.skill_match = score.skill_match
            existing.experience_match = score.experience_match
            existing.location_match = score.location_match
            existing.seniority_match = score.seniority_match
            existing.salary_match = score.salary_match
            existing.domain_match = score.domain_match
            existing.preference_match = score.preference_match
            existing.required_skills = score.required_skills
            existing.missing_skills = score.missing_skills
            existing.strengths = score.strengths
            existing.weaknesses = score.weaknesses
            existing.explanation = score.explanation
            existing.score_breakdown = score.score_breakdown
            existing.recommendation = score.recommendation.value
            await self.db.flush()
            return existing

        match = JobMatch(
            job_id=job.id,
            candidate_id=profile.id,
            overall_score=score.overall_score,
            skill_match=score.skill_match,
            experience_match=score.experience_match,
            location_match=score.location_match,
            seniority_match=score.seniority_match,
            salary_match=score.salary_match,
            domain_match=score.domain_match,
            preference_match=score.preference_match,
            required_skills=score.required_skills,
            missing_skills=score.missing_skills,
            strengths=score.strengths,
            weaknesses=score.weaknesses,
            explanation=score.explanation,
            score_breakdown=score.score_breakdown,
            recommendation=score.recommendation.value,
        )
        self.db.add(match)
        await self.db.flush()
        return match

    async def _ensure_application(
        self,
        user: User,
        job: Job,
        profile: CandidateProfile,
        match: JobMatch,
    ) -> Application:
        result = await self.db.execute(
            select(Application).where(
                Application.user_id == user.id, Application.job_id == job.id
            )
        )
        app = result.scalar_one_or_none()
        if app:
            app.match_id = match.id
            await self.db.flush()
            return app
        app = Application(
            user_id=user.id,
            job_id=job.id,
            candidate_id=profile.id,
            match_id=match.id,
            application_url=job.official_application_url or job.source_url,
            status=ApplicationStatus.DISCOVERED.value,
        )
        self.db.add(app)
        await self.db.flush()
        return app

    async def get_job(self, job_id: UUID) -> Job:
        job = await self.jobs.get_by_id(job_id)
        if not job:
            raise NotFoundError("Job not found")
        return job

    async def list_matches(self, user: User, *, limit: int = 50) -> list[JobMatch]:
        profile = await self.users.get_profile(user.id)
        if not profile:
            return []
        result = await self.db.execute(
            select(JobMatch)
            .where(JobMatch.candidate_id == profile.id)
            .order_by(JobMatch.overall_score.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_and_ingest(self, user_id: UUID, request: JobSearchRequest) -> list:
        user = await self.db.get(User, user_id)
        if not user:
            raise NotFoundError("User not found")
        results = await self.search_and_persist(user, request)
        return [job for job, _ in results]

    async def analyze_and_score(self, user_id: UUID, job_id: UUID) -> JobMatch:
        user = await self.db.get(User, user_id)
        if not user:
            raise NotFoundError("User not found")
        profile = await self.users.get_profile(user.id)
        if not profile:
            raise NotFoundError("Profile not found")
        job = await self.get_job(job_id)
        return await self._upsert_match(job, profile)

    async def queue_daily_pipeline(self, user_id: UUID) -> int:
        """Queue prepare tasks for strongest matches under daily remaining capacity."""
        from app.models import Application
        from app.repositories.application_repository import ApplicationRepository
        from app.workers.tasks import prepare_application_task

        user = await self.db.get(User, user_id)
        if not user:
            return 0
        settings = await self.users.get_settings(user_id)
        limit = settings.daily_application_limit if settings else 10
        min_score = settings.min_match_score if settings else 0.65
        submitted = await ApplicationRepository(self.db).count_submitted_today(user_id)
        remaining = max(0, limit - submitted)
        if remaining == 0:
            return 0
        matches = await self.list_matches(user, limit=remaining * 3)
        queued = 0
        for match in matches:
            if match.overall_score < min_score:
                continue
            app = (
                await self.db.execute(
                    select(Application).where(
                        Application.user_id == user_id,
                        Application.job_id == match.job_id,
                    )
                )
            ).scalar_one_or_none()
            if not app or app.status in {
                ApplicationStatus.SUBMITTED.value,
                ApplicationStatus.APPLYING.value,
                ApplicationStatus.REJECTED.value,
            }:
                continue
            prepare_application_task.delay(str(user_id), str(app.id))
            queued += 1
            if queued >= remaining:
                break
        return queued
