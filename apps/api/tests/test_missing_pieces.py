"""Tests for newly implemented missing pieces."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_csrf
from app.automation.registry import list_workflows
from app.automation.workflows.linkedin import (
    LinkedInEasyApplyWorkflow,
    linkedin_easy_apply_enabled,
)
from app.core.config import Settings
from app.core.exceptions import ConflictError, ForbiddenError
from app.core.security import decrypt_value, encrypt_value
from app.models import (
    Application,
    AutomationRun,
    CandidateProfile,
    CompanyResearch,
    Contact,
    Job,
    OutreachMessage,
    Resume,
    User,
    UserSettings,
)
from app.models.enums import (
    ApplicationStatus,
    AutomationStatus,
    AutomationTaskType,
    ContactType,
    OutreachStatus,
)
from app.services.answer_service import AnswerService
from app.services.application_service import ApplicationService
from app.services.credential_service import CredentialService
from app.services.dashboard_service import DashboardService
from app.services.job_service import JobService
from app.services.outreach_service import OutreachService
from app.services.rate_limit import RateLimitService, reset_memory_rate_limits
from app.services.retention_service import RetentionService
from app.services.scoring_service import ScoringService
from fastapi import Request


async def _seed_job(db: AsyncSession) -> Job:
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
    return job


# --- Outreach API ---


@pytest.mark.asyncio
async def test_outreach_list_approve_send(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    user: User,
    profile: CandidateProfile,
) -> None:
    job = await _seed_job(db_session)
    app = Application(
        user_id=user.id,
        job_id=job.id,
        candidate_id=profile.id,
        status=ApplicationStatus.READY_FOR_REVIEW.value,
    )
    db_session.add(app)
    await db_session.flush()
    msg = OutreachMessage(
        user_id=user.id,
        application_id=app.id,
        recipient_name="Recruiter",
        recipient_type=ContactType.RECRUITER.value,
        generated_message="Hello, interested in the role.",
        status=OutreachStatus.DRAFT.value,
        channel="email",
    )
    db_session.add(msg)
    await db_session.commit()

    listed = await client.get("/api/outreach", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    got = await client.get(f"/api/outreach/{msg.id}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["recipient_name"] == "Recruiter"

    approved = await client.post(f"/api/outreach/{msg.id}/approve", headers=auth_headers)
    assert approved.status_code == 200
    assert approved.json()["status"] == OutreachStatus.APPROVED.value

    sent = await client.post(f"/api/outreach/{msg.id}/send", headers=auth_headers)
    assert sent.status_code == 200
    assert sent.json()["status"] == OutreachStatus.SENT.value
    assert sent.json()["sent_at"] is not None


@pytest.mark.asyncio
async def test_outreach_send_requires_approval(
    db_session: AsyncSession, user: User
) -> None:
    job = await _seed_job(db_session)
    from sqlalchemy import select

    profile = (
        await db_session.execute(
            select(CandidateProfile).where(CandidateProfile.user_id == user.id)
        )
    ).scalar_one()
    app = Application(
        user_id=user.id,
        job_id=job.id,
        candidate_id=profile.id,
        status=ApplicationStatus.READY_FOR_REVIEW.value,
    )
    db_session.add(app)
    await db_session.flush()
    msg = OutreachMessage(
        user_id=user.id,
        application_id=app.id,
        recipient_name="R",
        generated_message="Hi",
        status=OutreachStatus.DRAFT.value,
    )
    db_session.add(msg)
    await db_session.flush()
    with pytest.raises(ConflictError):
        await OutreachService(db_session).send(user.id, msg.id)


# --- List endpoints ---


@pytest.mark.asyncio
async def test_list_contacts_resumes_research(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    user: User,
    profile: CandidateProfile,
) -> None:
    job = await _seed_job(db_session)
    db_session.add(
        Contact(
            user_id=user.id,
            job_id=job.id,
            name="Alex Recruiter",
            company="TestCo",
            contact_type=ContactType.RECRUITER.value,
            confidence_score=0.9,
        )
    )
    db_session.add(
        Resume(
            user_id=user.id,
            candidate_id=profile.id,
            job_id=job.id,
            quality_score=0.9,
            file_path="/tmp/r.pdf",
            content={"summary": "x"},
        )
    )
    db_session.add(
        CompanyResearch(
            user_id=user.id,
            job_id=job.id,
            company="TestCo",
            problem_summary="Need backend help",
            confidence_score=0.8,
            evidence=[{"claim": "Hiring", "confidence": 0.8}],
        )
    )
    await db_session.commit()

    contacts = await client.get("/api/contacts", headers=auth_headers)
    resumes = await client.get("/api/resumes", headers=auth_headers)
    research = await client.get("/api/research", headers=auth_headers)
    assert contacts.status_code == 200 and len(contacts.json()) == 1
    assert resumes.status_code == 200 and len(resumes.json()) == 1
    assert research.status_code == 200 and len(research.json()) == 1


# --- CSRF ---


@pytest.mark.asyncio
async def test_csrf_rejects_cookie_mutation_without_token() -> None:
    request = MagicMock(spec=Request)
    request.method = "POST"
    request.cookies = {"jaa_session": "tok"}

    with patch("app.api.deps.get_settings") as gs:
        settings = Settings(app_env="development", cookie_name="jaa_session")
        gs.return_value = settings
        with pytest.raises(ForbiddenError):
            await require_csrf(
                request,
                csrf_header=None,
                csrf_cookie="abc",
                authorization=None,
            )


@pytest.mark.asyncio
async def test_csrf_skips_bearer_auth() -> None:
    request = MagicMock(spec=Request)
    request.method = "POST"
    request.cookies = {"jaa_session": "tok"}

    with patch("app.api.deps.get_settings") as gs:
        settings = Settings(app_env="development", cookie_name="jaa_session")
        gs.return_value = settings
        await require_csrf(
            request,
            csrf_header=None,
            csrf_cookie=None,
            authorization="Bearer something",
        )


# --- Scoring weights ---


@pytest.mark.asyncio
async def test_user_scoring_weights_applied(
    db_session: AsyncSession, user: User, profile: CandidateProfile
) -> None:
    from sqlalchemy import select

    settings = (
        await db_session.execute(select(UserSettings).where(UserSettings.user_id == user.id))
    ).scalar_one()
    settings.scoring_weights = {
        "technical": 1.0,
        "experience": 0.0,
        "seniority": 0.0,
        "location": 0.0,
        "domain": 0.0,
        "salary": 0.0,
        "preference": 0.0,
    }
    await db_session.flush()
    job = await _seed_job(db_session)
    svc = JobService(db_session)
    scorer = await svc._scoring_for_user(user.id)
    assert scorer.weights["technical"] == 1.0
    score = scorer.score(job, profile)
    # With only technical weight, overall equals skill_match
    assert score.overall_score == score.skill_match


def test_scoring_service_custom_weights() -> None:
    svc = ScoringService(
        weights={
            "technical": 1.0,
            "experience": 0.0,
            "seniority": 0.0,
            "location": 0.0,
            "domain": 0.0,
            "salary": 0.0,
            "preference": 0.0,
        }
    )
    assert svc.weights["technical"] == 1.0


# --- Prepare race fix ---


@pytest.mark.asyncio
async def test_begin_prepare_does_not_jump_to_ready(
    db_session: AsyncSession, user: User, profile: CandidateProfile
) -> None:
    job = await _seed_job(db_session)
    app = Application(
        user_id=user.id,
        job_id=job.id,
        candidate_id=profile.id,
        status=ApplicationStatus.DISCOVERED.value,
        application_url=job.official_application_url,
    )
    db_session.add(app)
    await db_session.flush()
    with patch("app.workers.tasks.prepare_application_task.delay"):
        result = await ApplicationService(db_session).begin_prepare(user, app.id)
    assert result.status == ApplicationStatus.RESUME_GENERATING.value
    assert result.status != ApplicationStatus.READY_FOR_REVIEW.value


@pytest.mark.asyncio
async def test_prepare_endpoint_enqueues_without_ready(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    user: User,
    profile: CandidateProfile,
) -> None:
    job = await _seed_job(db_session)
    app = Application(
        user_id=user.id,
        job_id=job.id,
        candidate_id=profile.id,
        status=ApplicationStatus.MATCHED.value,
        application_url=job.official_application_url,
    )
    db_session.add(app)
    await db_session.commit()
    with patch("app.workers.tasks.prepare_application_task.delay") as delay:
        resp = await client.post(
            f"/api/applications/{app.id}/prepare", headers=auth_headers
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == ApplicationStatus.RESUME_GENERATING.value
    delay.assert_called_once()


# --- Auto submit ---


@pytest.mark.asyncio
async def test_approve_auto_submits_when_enabled(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    user: User,
    profile: CandidateProfile,
) -> None:
    from sqlalchemy import select

    settings = (
        await db_session.execute(select(UserSettings).where(UserSettings.user_id == user.id))
    ).scalar_one()
    settings.auto_submit_enabled = True
    job = await _seed_job(db_session)
    app = Application(
        user_id=user.id,
        job_id=job.id,
        candidate_id=profile.id,
        status=ApplicationStatus.READY_FOR_REVIEW.value,
        application_url=job.official_application_url,
    )
    db_session.add(app)
    await db_session.commit()
    with patch("app.workers.tasks.submit_application_task.delay") as delay:
        resp = await client.post(
            f"/api/applications/{app.id}/approve", headers=auth_headers
        )
    assert resp.status_code == 200
    delay.assert_called_once_with(str(user.id), str(app.id))


# --- Credentials ---


@pytest.mark.asyncio
async def test_credentials_encrypt_roundtrip(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    user: User,
) -> None:
    created = await client.post(
        "/api/credentials",
        headers=auth_headers,
        json={"provider": "greenhouse", "payload": {"api_key": "secret-key"}},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["provider"] == "greenhouse"
    assert "encrypted_payload" not in body

    listed = await client.get("/api/credentials", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    row = await CredentialService(db_session).get_by_provider(user.id, "greenhouse")
    assert row is not None
    payload = CredentialService(db_session).decrypt_payload(row)
    assert payload["api_key"] == "secret-key"

    deleted = await client.delete(f"/api/credentials/{body['id']}", headers=auth_headers)
    assert deleted.status_code == 200


def test_encrypt_decrypt_helpers() -> None:
    token = encrypt_value("hello-world")
    assert decrypt_value(token) == "hello-world"
    assert token != "hello-world"


# --- Rate limits ---


def test_rate_limit_enforced() -> None:
    reset_memory_rate_limits()
    svc = RateLimitService(Settings(rate_limit_job_discovery_per_hour=2))
    svc.check(scope="job_discovery", identity="u1", limit=2)
    svc.check(scope="job_discovery", identity="u1", limit=2)
    with pytest.raises(ConflictError):
        svc.check(scope="job_discovery", identity="u1", limit=2)
    reset_memory_rate_limits()


# --- Retention ---


@pytest.mark.asyncio
async def test_retention_cleanup_deletes_old_runs(db_session: AsyncSession, user: User) -> None:
    from sqlalchemy import update

    old = AutomationRun(
        user_id=user.id,
        task_type=AutomationTaskType.JOB_DISCOVERY.value,
        status=AutomationStatus.SUCCEEDED.value,
    )
    db_session.add(old)
    await db_session.flush()
    await db_session.execute(
        update(AutomationRun)
        .where(AutomationRun.id == old.id)
        .values(created_at=datetime.now(UTC) - timedelta(days=200))
    )
    await db_session.flush()

    settings = Settings(
        retention_days_automation_runs=90,
        retention_days_applications=0,
        retention_days_ai_usage=0,
    )
    deleted = await RetentionService(db_session, settings).cleanup()
    assert deleted["automation_runs"] >= 1


# --- Dashboard rates ---


@pytest.mark.asyncio
async def test_dashboard_response_and_interview_rates(
    db_session: AsyncSession, user: User, profile: CandidateProfile
) -> None:
    job = await _seed_job(db_session)
    app1 = Application(
        user_id=user.id,
        job_id=job.id,
        candidate_id=profile.id,
        status=ApplicationStatus.SUBMITTED.value,
        submitted_at=datetime.now(UTC),
        confirmation_text="Thanks",
        application_answers={"outcome": "interview"},
    )
    job2 = Job(
        title="Other",
        company="OtherCo",
        description="x",
        source="test",
        external_job_id=str(uuid4()),
    )
    db_session.add(job2)
    await db_session.flush()
    app2 = Application(
        user_id=user.id,
        job_id=job2.id,
        candidate_id=profile.id,
        status=ApplicationStatus.SUBMITTED.value,
        submitted_at=datetime.now(UTC),
    )
    db_session.add_all([app1, app2])
    await db_session.flush()

    stats = await DashboardService(db_session).stats(user)
    assert stats.response_rate == 0.5
    assert stats.interview_rate == 0.5


# --- Answer draft ---


@pytest.mark.asyncio
async def test_answer_service_offline_draft(
    db_session: AsyncSession, user: User, profile: CandidateProfile
) -> None:
    profile.answer_bank = {"Why this company?": "Mission alignment", "Visa?": "Authorized"}
    job = await _seed_job(db_session)
    app = Application(
        user_id=user.id,
        job_id=job.id,
        candidate_id=profile.id,
        status=ApplicationStatus.RESUME_GENERATING.value,
    )
    db_session.add(app)
    await db_session.flush()
    draft = await AnswerService(db_session).draft_for_application(user.id, app.id)
    assert "Why this company?" in draft.answers
    await db_session.refresh(app)
    assert app.application_answers["answers"]["Why this company?"] == "Mission alignment"


# --- LinkedIn workflow ---


@pytest.mark.asyncio
async def test_linkedin_workflow_disabled_needs_human() -> None:
    assert "linkedin_easy_apply" in list_workflows()
    wf = LinkedInEasyApplyWorkflow()
    assert await wf.can_handle(MagicMock(), "https://www.linkedin.com/jobs/view/123")
    token = linkedin_easy_apply_enabled.set(False)
    try:
        with patch("app.automation.workflows.linkedin.get_settings") as gs:
            gs.return_value = Settings(linkedin_easy_apply_fallback=False)
            result = await wf.submit(MagicMock())
        assert result.needs_human is True
    finally:
        linkedin_easy_apply_enabled.reset(token)


@pytest.mark.asyncio
async def test_linkedin_enabled_delegates_to_generic() -> None:
    from app.automation.models import SubmissionResult

    wf = LinkedInEasyApplyWorkflow()
    token = linkedin_easy_apply_enabled.set(True)

    async def fake_submit(self, page):  # type: ignore[no-untyped-def]
        return SubmissionResult(success=True)

    try:
        with patch("app.automation.workflows.linkedin.get_settings") as gs:
            gs.return_value = Settings(linkedin_easy_apply_fallback=True)
            with patch.object(wf, "detect_blocker", return_value=False):
                with patch(
                    "app.automation.workflows.generic.GenericWorkflow.submit",
                    fake_submit,
                ):
                    result = await wf.submit(MagicMock())
        assert result.success is True
        assert result.needs_human is False
    finally:
        linkedin_easy_apply_enabled.reset(token)
