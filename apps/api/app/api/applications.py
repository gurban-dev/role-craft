"""Application routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession, require_csrf
from app.models.enums import ApplicationStatus
from app.schemas import ApplicationDetailOut, ApplicationOut
from app.services.application_service import ApplicationService
from app.services.rate_limit import RateLimitService

router = APIRouter(
    prefix="/applications",
    tags=["applications"],
    dependencies=[Depends(require_csrf)],
)


class SubmitBody(BaseModel):
    automation_result: dict | None = None


@router.get("", response_model=list[ApplicationOut])
async def list_applications(
    user: CurrentUser,
    db: DbSession,
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[ApplicationOut]:
    apps = await ApplicationService(db).list(user.id, status=status, limit=limit)
    return [ApplicationOut.model_validate(a) for a in apps]


@router.get("/{application_id}", response_model=ApplicationDetailOut)
async def get_application(
    application_id: UUID, user: CurrentUser, db: DbSession
) -> ApplicationDetailOut:
    app = await ApplicationService(db).get(application_id, user.id)
    return ApplicationDetailOut.model_validate(app)


@router.post("/{application_id}/prepare", response_model=ApplicationOut)
async def prepare_application(
    application_id: UUID, user: CurrentUser, db: DbSession
) -> ApplicationOut:
    from app.workers.tasks import prepare_application_task

    # Enqueue prep only — do not race ahead to READY_FOR_REVIEW here.
    # The Celery task performs resume/research/contact/outreach then marks ready.
    app = await ApplicationService(db).begin_prepare(user, application_id)
    prepare_application_task.delay(str(user.id), str(application_id))
    await db.refresh(app)
    return ApplicationOut.model_validate(app)


@router.post("/{application_id}/approve", response_model=ApplicationOut)
async def approve_application(
    application_id: UUID,
    user: CurrentUser,
    db: DbSession,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ApplicationOut:
    app = await ApplicationService(db).approve(
        user, application_id, idempotency_key=idempotency_key
    )
    # Auto-submit when enabled: enqueue browser submit after approval
    settings = await ApplicationService(db).users.get_settings(user.id)
    if settings and settings.auto_submit_enabled:
        from app.workers.tasks import submit_application_task

        RateLimitService().check_browser(str(user.id))
        if app.status == ApplicationStatus.READY_FOR_REVIEW.value:
            submit_application_task.delay(str(user.id), str(application_id))
    await db.refresh(app)
    return ApplicationOut.model_validate(app)


@router.post("/{application_id}/submit", response_model=ApplicationOut)
async def submit_application(
    application_id: UUID,
    user: CurrentUser,
    db: DbSession,
    body: SubmitBody | None = None,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ApplicationOut:
    from app.workers.tasks import submit_application_task

    # Prefer async browser submit unless a mocked automation_result is provided (tests)
    if body and body.automation_result is not None:
        app = await ApplicationService(db).submit(
            user,
            application_id,
            idempotency_key=idempotency_key,
            automation_result=body.automation_result,
        )
        return ApplicationOut.model_validate(app)

    RateLimitService().check_browser(str(user.id))
    submit_application_task.delay(str(user.id), str(application_id))
    app = await ApplicationService(db).get(application_id, user.id)
    return ApplicationOut.model_validate(app)
