"""EEA software-engineering daily discovery workflow."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.integrations.job_sources.base import DiscoveredJob, JobSearchCriteria
from app.integrations.job_sources.registry import EEA_DISCOVERY_SOURCES, get_job_source
from app.models import CandidateProfile, Job, User
from app.models.enums import JobStatus
from app.repositories.job_repository import JobRepository
from app.repositories.user_repository import UserRepository
from app.services.candidate_profile_extractor import CandidateProfileExtractor
from app.services.eea_filters import classify_visa_sponsorship, detect_country_code, is_eea_location
from app.services.eea_pipeline import (
    QualifiedJob,
    dedupe_discovered,
    rank_qualified,
    validate_hard_requirements,
)
from app.services.job_service import JobService, normalize_job_key

logger = get_logger(__name__)


class EEAJobSearchService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.jobs = JobRepository(db)
        self.users = UserRepository(db)
        self.job_service = JobService(db)

    async def ensure_structured_profile(self, profile: CandidateProfile, user_id: str) -> None:
        extractor = CandidateProfileExtractor(self.db, self.settings)
        if profile.structured_profile:
            return
        structured = extractor.from_candidate_profile(profile)
        await extractor.persist(profile, structured)

    async def discover_and_rank(
        self,
        user: User,
        *,
        query: str = "software engineer",
        limit: int = 10,
        sources: list[str] | None = None,
    ) -> list[dict]:
        """Run phases 1–20 of the EEA workflow; return top qualifying rows (≤10)."""
        from app.services.rate_limit import RateLimitService

        RateLimitService(self.settings).check_job_discovery(str(user.id))
        profile = await self.users.get_profile(user.id)
        if not profile:
            return []
        await self.ensure_structured_profile(profile, str(user.id))

        hours = self.settings.eea_posted_within_hours
        criteria = JobSearchCriteria(
            query=query,
            location=None,
            remote_only=False,
            limit=max(limit * 5, 40),
            posted_within_hours=hours,
            eea_only=True,
        )
        source_names = sources or EEA_DISCOVERY_SOURCES
        discovered: list[DiscoveredJob] = []
        for name in source_names:
            try:
                source = get_job_source(name)
                discovered.extend(await source.search(criteria))
            except Exception as exc:
                logger.warning("eea_source_failed", source=name, error=str(exc))

        discovered = dedupe_discovered(discovered)
        scoring = await self.job_service._scoring_for_user(user.id)
        min_fit = self.settings.min_fit_score_10
        now = datetime.now(UTC)
        qualified: list[QualifiedJob] = []

        for item in discovered:
            ok, evidence, meta = validate_hard_requirements(item, now=now, hours=hours)
            if not ok:
                logger.debug(
                    "eea_job_rejected",
                    title=item.title,
                    company=item.company,
                    reasons=evidence.reasons_rejected,
                )
                continue

            job = await self._persist_discovered(item, meta, evidence_dump=evidence.__dict__)
            self.job_service.scoring = scoring
            match = await self.job_service._upsert_match(job, profile)
            await self.job_service._ensure_application(user, job, profile, match)

            if (job.fit_score_10 or 0) < min_fit:
                continue
            qualified.append(
                QualifiedJob(
                    job=item,
                    fit_score_10=float(job.fit_score_10 or 0),
                    evidence=evidence,
                    country_code=meta.get("country_code"),
                    visa_sponsorship=meta.get("visa_sponsorship", "unknown"),
                )
            )
            item.official_application_url = (
                job.official_application_url or item.official_application_url or item.source_url
            )

        ranked = rank_qualified(qualified, limit=limit)
        rows = []
        for idx, q in enumerate(ranked, start=1):
            posted = q.job.posted_at.isoformat() if q.job.posted_at else ""
            apply = q.job.official_application_url or q.job.source_url or ""
            rows.append(
                {
                    "rank": idx,
                    "role": q.job.title,
                    "company": q.job.company,
                    "posted": posted,
                    "source": q.job.source,
                    "fit_score": q.fit_score_10,
                    "apply_link": apply,
                    "location": q.job.location,
                    "applicant_count": q.job.applicant_count,
                }
            )
        logger.info("eea_search_complete", user_id=str(user.id), returned=len(rows))
        return rows

    async def _persist_discovered(self, item: DiscoveredJob, meta: dict, evidence_dump: dict) -> Job:
        key = normalize_job_key(item.company, item.title, item.location)
        existing = await self.jobs.get_by_source_external(item.source, item.external_job_id)
        if existing is None:
            existing = await self.jobs.get_by_normalized_key(key)

        country = meta.get("country_code") or detect_country_code(item.location, item.description)
        visa = meta.get("visa_sponsorship") or classify_visa_sponsorship(item.description)
        raw = dict(item.raw_payload or {})
        raw["eea_evidence"] = {
            k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in evidence_dump.items()
        }

        if existing:
            job = existing
            if item.posted_at and (job.posted_at is None or item.posted_at > job.posted_at):
                job.posted_at = item.posted_at
            if item.applicant_count is not None:
                job.applicant_count = item.applicant_count
            if item.description and len(item.description) > len(job.description or ""):
                job.description = item.description
            if item.official_application_url:
                job.official_application_url = item.official_application_url
            job.country_code = country
            job.is_eea = bool(country) or is_eea_location(item.location, item.description)
            job.visa_sponsorship = visa
            job.raw_payload = {**(job.raw_payload or {}), **raw}
            await self.db.flush()
            return job

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
            official_application_url=item.official_application_url or item.source_url,
            external_job_id=item.external_job_id,
            closing_date=item.closing_date,
            posted_at=item.posted_at,
            applicant_count=item.applicant_count,
            country_code=country,
            is_eea=bool(country) or is_eea_location(item.location, item.description),
            english_required=True,
            visa_sponsorship=visa,
            status=JobStatus.ACTIVE.value,
            normalized_key=key,
            raw_payload=raw,
        )
        self.db.add(job)
        await self.db.flush()
        return job
