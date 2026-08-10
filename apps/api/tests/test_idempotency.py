"""Idempotency tests for approve/submit."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.models import Application, CandidateProfile, Job, JobMatch, Resume, User
from app.models.enums import ApplicationStatus, MatchRecommendation
from app.services.application_service import ApplicationService


async def _seed_ready_app(
    db: AsyncSession, user: User, profile: CandidateProfile
) -> Application:
    job = Job(
        title="Python Engineer",
        company="TestCo",
        description="python fastapi postgresql 5 years remote",
        technologies=["python", "fastapi"],
        requirements=["python"],
        source="test",
        external_job_id=str(uuid4()),
        official_application_url="https://example.com/apply",
        remote_status="remote",
    )
    db.add(job)
    await db.flush()
    match = JobMatch(
        job_id=job.id,
        candidate_id=profile.id,
        overall_score=0.9,
        skill_match=0.9,
        experience_match=0.9,
        location_match=1.0,
        seniority_match=0.9,
        salary_match=0.8,
        domain_match=0.7,
        preference_match=0.8,
        recommendation=MatchRecommendation.READY_TO_APPLY.value,
        explanation="strong",
    )
    db.add(match)
    await db.flush()
    resume = Resume(
        user_id=user.id,
        candidate_id=profile.id,
        job_id=job.id,
        quality_score=0.9,
        file_path="/tmp/resume.pdf",
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
        status=ApplicationStatus.READY_FOR_REVIEW.value,
        application_answers={"answers": {"q1": "yes"}, "confidence_by_question": {"q1": 0.95}},
    )
    db.add(app)
    await db.flush()
    return app


@pytest.mark.asyncio
async def test_approve_idempotent(
    db_session: AsyncSession, user: User, profile: CandidateProfile
) -> None:
    app = await _seed_ready_app(db_session, user, profile)
    svc = ApplicationService(db_session)
    key = f"approve-{app.id}"
    a1 = await svc.approve(user, app.id, idempotency_key=key)
    a2 = await svc.approve(user, app.id, idempotency_key=key)
    assert a1.approved_at is not None
    assert a1.id == a2.id
    assert a1.idempotency_key == key


@pytest.mark.asyncio
async def test_submit_idempotent(
    db_session: AsyncSession, user: User, profile: CandidateProfile
) -> None:
    app = await _seed_ready_app(db_session, user, profile)
    svc = ApplicationService(db_session)
    await svc.approve(user, app.id, idempotency_key=f"appr-{app.id}")
    key = f"submit-{app.id}"
    s1 = await svc.submit(
        user,
        app.id,
        idempotency_key=key,
        automation_result={"confirmation_text": "ok"},
    )
    assert s1.status == ApplicationStatus.SUBMITTED.value
    s2 = await svc.submit(user, app.id, idempotency_key=key)
    assert s2.id == s1.id
    assert s2.status == ApplicationStatus.SUBMITTED.value


@pytest.mark.asyncio
async def test_idempotency_key_conflict(
    db_session: AsyncSession, user: User, profile: CandidateProfile
) -> None:
    app1 = await _seed_ready_app(db_session, user, profile)
    app2 = await _seed_ready_app(db_session, user, profile)
    svc = ApplicationService(db_session)
    key = "shared-key"
    await svc.approve(user, app1.id, idempotency_key=key)
    with pytest.raises(ConflictError):
        await svc.approve(user, app2.id, idempotency_key=key)
