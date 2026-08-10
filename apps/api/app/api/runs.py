"""Automation run routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import NotFoundError
from app.models import AutomationRun
from app.models.enums import AutomationStatus, AutomationTaskType
from app.schemas import AutomationRunOut, TaskEnqueueResponse

router = APIRouter(prefix="/runs", tags=["runs"])


class EnqueueRequest(BaseModel):
    task_type: AutomationTaskType
    application_id: UUID | None = None
    job_id: UUID | None = None
    payload: dict | None = None


@router.get("", response_model=list[AutomationRunOut])
async def list_runs(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AutomationRunOut]:
    result = await db.execute(
        select(AutomationRun)
        .where(AutomationRun.user_id == user.id)
        .order_by(AutomationRun.created_at.desc())
        .limit(limit)
    )
    return [AutomationRunOut.model_validate(r) for r in result.scalars().all()]


@router.get("/{run_id}", response_model=AutomationRunOut)
async def get_run(run_id: UUID, user: CurrentUser, db: DbSession) -> AutomationRunOut:
    run = await db.get(AutomationRun, run_id)
    if not run or run.user_id != user.id:
        raise NotFoundError("Run not found")
    return AutomationRunOut.model_validate(run)


@router.post("/enqueue", response_model=TaskEnqueueResponse)
async def enqueue_task(
    data: EnqueueRequest, user: CurrentUser, db: DbSession
) -> TaskEnqueueResponse:
    from app.workers.tasks import dispatch_task

    run = AutomationRun(
        user_id=user.id,
        application_id=data.application_id,
        job_id=data.job_id,
        task_type=data.task_type.value,
        status=AutomationStatus.QUEUED.value,
        result=data.payload or {},
    )
    db.add(run)
    await db.flush()

    task_id = dispatch_task(
        data.task_type,
        user_id=str(user.id),
        run_id=str(run.id),
        application_id=str(data.application_id) if data.application_id else None,
        job_id=str(data.job_id) if data.job_id else None,
        payload=data.payload or {},
    )
    run.celery_task_id = task_id
    await db.flush()
    return TaskEnqueueResponse(task_id=task_id, run_id=run.id, status="queued")
