"""Pre-submit quality gate checklist."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import QualityGateError
from app.models import Application, CandidateProfile, Job, JobMatch, Resume, UserSettings
from app.models.enums import ApplicationStatus, MatchRecommendation


@dataclass
class QualityGateResult:
    passed: bool
    checks: dict[str, bool] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "checks": self.checks,
            "failures": self.failures,
            "details": self.details,
        }


class QualityGateService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    async def evaluate(self, application: Application) -> QualityGateResult:
        checks: dict[str, bool] = {}
        failures: list[str] = []
        details: dict[str, Any] = {}

        job = await self.db.get(Job, application.job_id)
        profile = await self.db.get(CandidateProfile, application.candidate_id)
        settings_row = (
            await self.db.execute(
                select(UserSettings).where(UserSettings.user_id == application.user_id)
            )
        ).scalar_one_or_none()

        min_match = (
            settings_row.min_match_score if settings_row else self.settings.min_match_score
        )
        min_resume = (
            settings_row.min_resume_score if settings_row else self.settings.min_resume_score
        )
        daily_limit = (
            settings_row.daily_application_limit
            if settings_row
            else self.settings.daily_application_limit
        )

        # Profile completeness
        profile_ok = bool(
            profile
            and profile.professional_summary
            and (profile.skills or profile.work_history)
        )
        checks["profile_complete"] = profile_ok
        if not profile_ok:
            failures.append("Candidate profile incomplete")

        # Match score
        match: JobMatch | None = None
        if application.match_id:
            match = await self.db.get(JobMatch, application.match_id)
        if match is None and profile:
            match = (
                await self.db.execute(
                    select(JobMatch).where(
                        JobMatch.job_id == application.job_id,
                        JobMatch.candidate_id == profile.id,
                    )
                )
            ).scalar_one_or_none()
        match_ok = bool(match and match.overall_score >= min_match)
        checks["match_score"] = match_ok
        details["match_score"] = match.overall_score if match else None
        details["min_match_score"] = min_match
        if not match_ok:
            failures.append(f"Match score below threshold ({min_match})")

        # Not rejected recommendation
        rec_ok = bool(
            match
            and match.recommendation
            not in {MatchRecommendation.REJECTED.value, MatchRecommendation.LOW_MATCH.value}
        )
        checks["recommendation"] = rec_ok
        if not rec_ok:
            failures.append("Match recommendation too low")

        # Resume quality
        resume: Resume | None = None
        if application.tailored_resume_id:
            resume = await self.db.get(Resume, application.tailored_resume_id)
        resume_ok = bool(
            resume
            and resume.file_path
            and (resume.quality_score or 0) >= min_resume
        )
        checks["resume_quality"] = resume_ok
        details["resume_score"] = resume.quality_score if resume else None
        details["min_resume_score"] = min_resume
        if not resume_ok:
            failures.append(f"Resume quality below threshold ({min_resume})")

        # Application URL present
        url_ok = bool(application.application_url or (job and job.official_application_url))
        checks["application_url"] = url_ok
        if not url_ok:
            failures.append("Missing application URL")

        # Approved for submit
        approved_ok = application.approved_at is not None
        checks["approved"] = approved_ok
        if not approved_ok:
            failures.append("Application not approved")

        # Status allows apply
        status_ok = application.status in {
            ApplicationStatus.READY_FOR_REVIEW.value,
            ApplicationStatus.APPLYING.value,
            ApplicationStatus.NEEDS_HUMAN_ACTION.value,
            ApplicationStatus.FAILED.value,
        }
        checks["status"] = status_ok
        if not status_ok:
            failures.append(f"Invalid status for submit: {application.status}")

        # Daily limit (informational check – caller also enforces)
        from app.repositories.application_repository import ApplicationRepository

        submitted_today = await ApplicationRepository(self.db).count_submitted_today(
            application.user_id
        )
        limit_ok = submitted_today < daily_limit
        checks["daily_limit"] = limit_ok
        details["submitted_today"] = submitted_today
        details["daily_limit"] = daily_limit
        if not limit_ok:
            failures.append("Daily application limit reached")

        # Low-confidence answers
        answers = application.application_answers or {}
        confidences = answers.get("confidence_by_question") or {}
        weak = [
            q
            for q, c in confidences.items()
            if isinstance(c, int | float) and c < self.settings.min_answer_confidence
        ]
        answers_ok = not weak
        checks["answer_confidence"] = answers_ok
        details["weak_answers"] = weak
        if not answers_ok:
            failures.append(f"Low-confidence answers: {', '.join(weak[:5])}")

        passed = all(checks.values())
        return QualityGateResult(passed=passed, checks=checks, failures=failures, details=details)

    async def require_pass(self, application: Application) -> QualityGateResult:
        result = await self.evaluate(application)
        application.quality_gate = result.to_dict()
        await self.db.flush()
        if not result.passed:
            raise QualityGateError(
                "Quality gate failed: " + "; ".join(result.failures),
                details=result.to_dict(),
            )
        return result
