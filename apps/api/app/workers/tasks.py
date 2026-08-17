"""Celery background tasks — expensive work stays out of request handlers."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.logging import get_logger, new_correlation_id, task_id_var, user_id_var
from app.models import AutomationRun, User
from app.models.enums import ApplicationStatus, AutomationStatus, AutomationTaskType
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


def _run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


async def _session() -> AsyncSession:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return factory()


async def _start_run(
    db: AsyncSession,
    *,
    task_type: str,
    user_id: UUID | None,
    application_id: UUID | None = None,
    job_id: UUID | None = None,
    celery_task_id: str | None = None,
) -> AutomationRun:
    run = AutomationRun(
        user_id=user_id,
        application_id=application_id,
        job_id=job_id,
        task_type=task_type,
        status=AutomationStatus.RUNNING.value,
        started_at=datetime.now(UTC),
        correlation_id=new_correlation_id(),
        celery_task_id=celery_task_id,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


async def _finish_run(
    db: AsyncSession,
    run: AutomationRun,
    *,
    ok: bool,
    result: dict | None = None,
    error: str | None = None,
) -> None:
    run.completed_at = datetime.now(UTC)
    if run.started_at:
        run.duration_ms = int((run.completed_at - run.started_at).total_seconds() * 1000)
    run.status = AutomationStatus.SUCCEEDED.value if ok else AutomationStatus.FAILED.value
    run.result = result or {}
    run.error = error
    await db.commit()


@celery_app.task(name="app.workers.tasks.discover_jobs_task", bind=True, max_retries=3)
def discover_jobs_task(
    self, user_id: str, query: str = "software engineer", limit: int = 25
) -> dict:
    task_id_var.set(self.request.id or "")
    user_id_var.set(user_id)
    return _run(_discover_jobs(user_id, query, limit, self.request.id))


async def _discover_jobs(user_id: str, query: str, limit: int, celery_id: str | None) -> dict:
    from app.schemas import JobSearchRequest
    from app.services.job_service import JobService

    db = await _session()
    try:
        uid = UUID(user_id)
        run = await _start_run(
            db,
            task_type=AutomationTaskType.JOB_DISCOVERY.value,
            user_id=uid,
            celery_task_id=celery_id,
        )
        try:
            jobs = await JobService(db).search_and_ingest(
                uid, JobSearchRequest(query=query, limit=limit)
            )
            await _finish_run(db, run, ok=True, result={"count": len(jobs)})
            return {"run_id": str(run.id), "count": len(jobs)}
        except Exception as exc:
            await _finish_run(db, run, ok=False, error=str(exc))
            raise
    finally:
        await db.close()


@celery_app.task(name="app.workers.tasks.analyze_job_task", bind=True, max_retries=3)
def analyze_job_task(self, user_id: str, job_id: str) -> dict:
    return _run(_analyze_job(user_id, job_id, self.request.id))


async def _analyze_job(user_id: str, job_id: str, celery_id: str | None) -> dict:
    from app.services.job_service import JobService

    db = await _session()
    try:
        uid, jid = UUID(user_id), UUID(job_id)
        run = await _start_run(
            db,
            task_type=AutomationTaskType.JOB_ANALYSIS.value,
            user_id=uid,
            job_id=jid,
            celery_task_id=celery_id,
        )
        try:
            match = await JobService(db).analyze_and_score(uid, jid)
            await _finish_run(
                db,
                run,
                ok=True,
                result={"match_id": str(match.id), "score": match.overall_score},
            )
            return {"match_id": str(match.id), "score": match.overall_score}
        except Exception as exc:
            await _finish_run(db, run, ok=False, error=str(exc))
            raise
    finally:
        await db.close()


@celery_app.task(name="app.workers.tasks.generate_resume_task", bind=True, max_retries=2)
def generate_resume_task(self, user_id: str, application_id: str) -> dict:
    return _run(_generate_resume(user_id, application_id, self.request.id))


async def _generate_resume(user_id: str, application_id: str, celery_id: str | None) -> dict:
    from app.services.resume_service import ResumeService

    db = await _session()
    try:
        uid, aid = UUID(user_id), UUID(application_id)
        run = await _start_run(
            db,
            task_type=AutomationTaskType.RESUME_GENERATION.value,
            user_id=uid,
            application_id=aid,
            celery_task_id=celery_id,
        )
        try:
            resume = await ResumeService(db).generate_for_application(uid, aid)
            await _finish_run(db, run, ok=True, result={"resume_id": str(resume.id)})
            return {"resume_id": str(resume.id)}
        except Exception as exc:
            await _finish_run(db, run, ok=False, error=str(exc))
            raise
    finally:
        await db.close()


@celery_app.task(name="app.workers.tasks.research_company_task", bind=True, max_retries=2)
def research_company_task(self, user_id: str, application_id: str) -> dict:
    return _run(_research(user_id, application_id, self.request.id))


async def _research(user_id: str, application_id: str, celery_id: str | None) -> dict:
    from app.services.research_service import ResearchService

    db = await _session()
    try:
        uid, aid = UUID(user_id), UUID(application_id)
        run = await _start_run(
            db,
            task_type=AutomationTaskType.COMPANY_RESEARCH.value,
            user_id=uid,
            application_id=aid,
            celery_task_id=celery_id,
        )
        try:
            research = await ResearchService(db).research_for_application(uid, aid)
            await _finish_run(db, run, ok=True, result={"research_id": str(research.id)})
            return {"research_id": str(research.id)}
        except Exception as exc:
            await _finish_run(db, run, ok=False, error=str(exc))
            raise
    finally:
        await db.close()


@celery_app.task(name="app.workers.tasks.discover_contact_task", bind=True, max_retries=2)
def discover_contact_task(self, user_id: str, application_id: str) -> dict:
    return _run(_contact(user_id, application_id, self.request.id))


async def _contact(user_id: str, application_id: str, celery_id: str | None) -> dict:
    from app.services.contact_service import ContactService

    db = await _session()
    try:
        uid, aid = UUID(user_id), UUID(application_id)
        run = await _start_run(
            db,
            task_type=AutomationTaskType.CONTACT_DISCOVERY.value,
            user_id=uid,
            application_id=aid,
            celery_task_id=celery_id,
        )
        try:
            contact = await ContactService(db).discover_for_application(uid, aid)
            await _finish_run(
                db,
                run,
                ok=True,
                result={"contact_id": str(contact.id) if contact else None},
            )
            return {"contact_id": str(contact.id) if contact else None}
        except Exception as exc:
            await _finish_run(db, run, ok=False, error=str(exc))
            raise
    finally:
        await db.close()


@celery_app.task(name="app.workers.tasks.generate_outreach_task", bind=True, max_retries=2)
def generate_outreach_task(self, user_id: str, application_id: str) -> dict:
    return _run(_outreach(user_id, application_id, self.request.id))


async def _outreach(user_id: str, application_id: str, celery_id: str | None) -> dict:
    from app.services.outreach_service import OutreachService

    db = await _session()
    try:
        uid, aid = UUID(user_id), UUID(application_id)
        run = await _start_run(
            db,
            task_type=AutomationTaskType.OUTREACH_GENERATION.value,
            user_id=uid,
            application_id=aid,
            celery_task_id=celery_id,
        )
        try:
            msg = await OutreachService(db).generate_for_application(uid, aid)
            await _finish_run(
                db, run, ok=True, result={"outreach_id": str(msg.id) if msg else None}
            )
            return {"outreach_id": str(msg.id) if msg else None}
        except Exception as exc:
            await _finish_run(db, run, ok=False, error=str(exc))
            raise
    finally:
        await db.close()


@celery_app.task(name="app.workers.tasks.prepare_application_task", bind=True, max_retries=2)
def prepare_application_task(self, user_id: str, application_id: str) -> dict:
    return _run(_prepare(user_id, application_id, self.request.id))


async def _prepare(user_id: str, application_id: str, celery_id: str | None) -> dict:
    from app.services.application_service import ApplicationService
    from app.services.contact_service import ContactService
    from app.services.outreach_service import OutreachService
    from app.services.research_service import ResearchService
    from app.services.resume_service import ResumeService

    db = await _session()
    try:
        uid, aid = UUID(user_id), UUID(application_id)
        run = await _start_run(
            db,
            task_type=AutomationTaskType.APPLICATION_PREPARE.value,
            user_id=uid,
            application_id=aid,
            celery_task_id=celery_id,
        )
        try:
            user = await db.get(User, uid)
            assert user
            await ResumeService(db).generate_for_application(uid, aid)
            from app.services.answer_service import AnswerService

            await AnswerService(db).draft_for_application(uid, aid)
            await ResearchService(db).research_for_application(uid, aid)
            await ContactService(db).discover_for_application(uid, aid)
            await OutreachService(db).generate_for_application(uid, aid)
            app = await ApplicationService(db).prepare(user, aid)
            await _finish_run(db, run, ok=True, result={"status": app.status})
            return {"status": app.status}
        except Exception as exc:
            await _finish_run(db, run, ok=False, error=str(exc))
            raise
    finally:
        await db.close()


@celery_app.task(name="app.workers.tasks.submit_application_task", bind=True, max_retries=1)
def submit_application_task(self, user_id: str, application_id: str) -> dict:
    return _run(_submit(user_id, application_id, self.request.id))


async def _submit(user_id: str, application_id: str, celery_id: str | None) -> dict:
    from app.automation.playwright_manager import PlaywrightManager
    from app.automation.registry import get_workflow_for_url
    from app.core.exceptions import NeedsHumanActionError
    from app.models import Job, Resume
    from app.services.application_service import ApplicationService

    db = await _session()
    try:
        uid, aid = UUID(user_id), UUID(application_id)
        run = await _start_run(
            db,
            task_type=AutomationTaskType.APPLICATION_SUBMIT.value,
            user_id=uid,
            application_id=aid,
            celery_task_id=celery_id,
        )
        try:
            user = await db.get(User, uid)
            assert user
            service = ApplicationService(db)
            app = await service.get(aid, uid)
            # Quality gate + status transition to APPLYING
            await service.begin_submit(user, aid)

            job = await db.get(Job, app.job_id)
            resume = None
            if app.tailored_resume_id:
                resume = await db.get(Resume, app.tailored_resume_id)
            url = app.application_url or (job.official_application_url if job else None)
            if not url or not job:
                raise NeedsHumanActionError("Missing application URL")

            from app.automation.workflows.linkedin import linkedin_easy_apply_enabled
            from app.repositories.user_repository import UserRepository

            user_settings = await UserRepository(db).get_settings(uid)
            token = linkedin_easy_apply_enabled.set(
                bool(user_settings.linkedin_easy_apply_fallback) if user_settings else False
            )
            try:
                manager = PlaywrightManager()
                async with manager.page() as page:
                    await page.goto(url, wait_until="domcontentloaded")
                    workflow = await get_workflow_for_url(page, url)
                    if await workflow.detect_blocker(page):
                        await service.mark_needs_human(user, aid, "CAPTCHA/MFA or blocker detected")
                        await _finish_run(db, run, ok=False, error="needs_human_action")
                        return {"status": ApplicationStatus.NEEDS_HUMAN_ACTION.value}

                    from app.automation.models import ApplicationData

                    data = ApplicationData(
                        job_title=job.title,
                        company=job.company,
                        resume_path=resume.file_path if resume else None,
                        answers=app.application_answers or {},
                        candidate_email=user.email,
                        candidate_name=user.name,
                    )
                    await workflow.fill_application(page, data)
                    result = await workflow.submit(page)
                    if result.needs_human:
                        reason = result.message or "Human action required"
                        await service.mark_needs_human(user, aid, reason)
                        await _finish_run(db, run, ok=False, error=result.message)
                        return {"status": ApplicationStatus.NEEDS_HUMAN_ACTION.value}

                    await service.record_submission(
                        user,
                        aid,
                        confirmation_text=result.confirmation_text,
                        confirmation_url=result.confirmation_url,
                        external_id=result.external_id,
                        screenshot_path=result.screenshot_path,
                        run_id=run.id,
                    )
                    await _finish_run(db, run, ok=True, result={"status": "SUBMITTED"})
                    return {"status": "SUBMITTED"}
            finally:
                linkedin_easy_apply_enabled.reset(token)
        except NeedsHumanActionError as exc:
            await _finish_run(db, run, ok=False, error=str(exc))
            return {"status": ApplicationStatus.NEEDS_HUMAN_ACTION.value, "error": str(exc)}
        except Exception as exc:
            await _finish_run(db, run, ok=False, error=str(exc))
            raise
    finally:
        await db.close()


@celery_app.task(name="app.workers.tasks.daily_scheduler_task", bind=True)
def daily_scheduler_task(self) -> dict:
    return _run(_daily_scheduler(self.request.id))


@celery_app.task(name="app.workers.tasks.retention_cleanup_task", bind=True)
def retention_cleanup_task(self) -> dict:
    return _run(_retention_cleanup(self.request.id))


def dispatch_task(
    task_type: AutomationTaskType,
    *,
    user_id: str,
    run_id: str | None = None,
    application_id: str | None = None,
    job_id: str | None = None,
    payload: dict | None = None,
) -> str:
    """Enqueue the Celery task for an API-created AutomationRun."""
    payload = payload or {}
    if task_type == AutomationTaskType.JOB_DISCOVERY:
        async_result = discover_jobs_task.delay(
            user_id,
            query=payload.get("query", "software engineer"),
            limit=int(payload.get("limit", 25)),
        )
    elif task_type in {AutomationTaskType.JOB_ANALYSIS, AutomationTaskType.MATCH_SCORING}:
        if not job_id:
            raise ValueError("job_id required")
        async_result = analyze_job_task.delay(user_id, job_id)
    elif task_type == AutomationTaskType.RESUME_GENERATION:
        if not application_id:
            raise ValueError("application_id required")
        async_result = generate_resume_task.delay(user_id, application_id)
    elif task_type == AutomationTaskType.COMPANY_RESEARCH:
        if not application_id:
            raise ValueError("application_id required")
        async_result = research_company_task.delay(user_id, application_id)
    elif task_type == AutomationTaskType.CONTACT_DISCOVERY:
        if not application_id:
            raise ValueError("application_id required")
        async_result = discover_contact_task.delay(user_id, application_id)
    elif task_type == AutomationTaskType.OUTREACH_GENERATION:
        if not application_id:
            raise ValueError("application_id required")
        async_result = generate_outreach_task.delay(user_id, application_id)
    elif task_type == AutomationTaskType.APPLICATION_PREPARE:
        if not application_id:
            raise ValueError("application_id required")
        async_result = prepare_application_task.delay(user_id, application_id)
    elif task_type == AutomationTaskType.APPLICATION_SUBMIT:
        if not application_id:
            raise ValueError("application_id required")
        async_result = submit_application_task.delay(user_id, application_id)
    elif task_type == AutomationTaskType.DAILY_SCHEDULER:
        async_result = daily_scheduler_task.delay()
    elif task_type == AutomationTaskType.RETENTION_CLEANUP:
        async_result = retention_cleanup_task.delay()
    else:
        raise ValueError(f"Unsupported task type: {task_type}")
    return async_result.id


async def _retention_cleanup(celery_id: str | None) -> dict:
    from app.services.retention_service import RetentionService

    db = await _session()
    try:
        run = await _start_run(
            db,
            task_type=AutomationTaskType.RETENTION_CLEANUP.value,
            user_id=None,
            celery_task_id=celery_id,
        )
        try:
            deleted = await RetentionService(db).cleanup()
            await db.commit()
            await _finish_run(db, run, ok=True, result=deleted)
            return deleted
        except Exception as exc:
            await _finish_run(db, run, ok=False, error=str(exc))
            raise
    finally:
        await db.close()


async def _daily_scheduler(celery_id: str | None) -> dict:
    """Discover EEA jobs (hard filters) then queue prepares for top matches."""
    from app.services.eea_job_search_service import EEAJobSearchService
    from app.services.job_service import JobService

    db = await _session()
    try:
        result = await db.execute(select(User).where(User.is_active.is_(True)))
        users = list(result.scalars().all())
        totals = {"users": 0, "queued": 0, "eea_jobs": 0}
        for user in users:
            run = await _start_run(
                db,
                task_type=AutomationTaskType.DAILY_SCHEDULER.value,
                user_id=user.id,
                celery_task_id=celery_id,
            )
            try:
                settings = get_settings()
                eea_count = 0
                if settings.eea_search_enabled:
                    rows = await EEAJobSearchService(db).discover_and_rank(user, limit=10)
                    eea_count = len(rows)
                    totals["eea_jobs"] += eea_count
                queued = await JobService(db).queue_daily_pipeline(user.id)
                totals["users"] += 1
                totals["queued"] += queued
                await db.commit()
                await _finish_run(
                    db, run, ok=True, result={"queued": queued, "eea_jobs": eea_count}
                )
            except Exception as exc:
                await _finish_run(db, run, ok=False, error=str(exc))
        return totals
    finally:
        await db.close()
