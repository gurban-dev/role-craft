"""Quality gate tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import QualityGateError
from app.models import Application, CandidateProfile, Job, JobMatch, Resume, User
from app.models.enums import ApplicationStatus, MatchRecommendation
from app.services.quality_gate import QualityGateService


async def _build(
    db: AsyncSession,
    user: User,
    profile: CandidateProfile,
    *,
    match_score: float = 0.9,
    resume_score: float = 0.9,
    approved: bool = True,
    status: str = ApplicationStatus.READY_FOR_REVIEW.value,
) -> Application:
    from datetime import UTC, datetime

    job = Job(
        title="Engineer",
        company="Co",
        description="python fastapi",
        technologies=["python"],
        source="test",
        external_job_id=str(uuid4()),
        official_application_url="https://example.com/apply",
    )
    db.add(job)
    await db.flush()
    match = JobMatch(
        job_id=job.id,
        candidate_id=profile.id,
        overall_score=match_score,
        recommendation=(
            MatchRecommendation.READY_TO_APPLY.value
            if match_score >= 0.65
            else MatchRecommendation.REJECTED.value
        ),
    )
    db.add(match)
    await db.flush()
    resume = Resume(
        user_id=user.id,
        candidate_id=profile.id,
        job_id=job.id,
        quality_score=resume_score,
        file_path="/tmp/r.pdf" if resume_score else None,
        content={"summary": "x", "skills": ["python"]},
    )
    db.add(resume)
    await db.flush()
    app = Application(
        user_id=user.id,
        job_id=job.id,
        candidate_id=profile.id,
        match_id=match.id,
        tailored_resume_id=resume.id,
        application_url=job.official_application_url,
        status=status,
        approved_at=datetime.now(UTC) if approved else None,
        approved_by=user.id if approved else None,
        application_answers={"confidence_by_question": {"q1": 0.95}},
    )
    db.add(app)
    await db.flush()
    return app


@pytest.mark.asyncio
async def test_quality_gate_passes(
    db_session: AsyncSession, user: User, profile: CandidateProfile
) -> None:
    app = await _build(db_session, user, profile)
    result = await QualityGateService(db_session).evaluate(app)
    assert result.passed is True
    assert not result.failures


@pytest.mark.asyncio
async def test_quality_gate_fails_low_match(
    db_session: AsyncSession, user: User, profile: CandidateProfile
) -> None:
    app = await _build(db_session, user, profile, match_score=0.2)
    result = await QualityGateService(db_session).evaluate(app)
    assert result.passed is False
    assert result.checks["match_score"] is False


@pytest.mark.asyncio
async def test_quality_gate_require_pass(
    db_session: AsyncSession, user: User, profile: CandidateProfile
) -> None:
    app = await _build(db_session, user, profile, approved=False)
    with pytest.raises(QualityGateError):
        await QualityGateService(db_session).require_pass(app)
