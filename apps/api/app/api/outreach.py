"""Outreach message routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, DbSession, require_csrf
from app.schemas import OutreachOut
from app.services.outreach_service import OutreachService

router = APIRouter(
    prefix="/outreach",
    tags=["outreach"],
    dependencies=[Depends(require_csrf)],
)


@router.get("", response_model=list[OutreachOut])
async def list_outreach(
    user: CurrentUser,
    db: DbSession,
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[OutreachOut]:
    rows = await OutreachService(db).list_for_user(user.id, status=status, limit=limit)
    return [OutreachOut.model_validate(r) for r in rows]


@router.get("/{outreach_id}", response_model=OutreachOut)
async def get_outreach(
    outreach_id: UUID, user: CurrentUser, db: DbSession
) -> OutreachOut:
    row = await OutreachService(db).get(outreach_id, user.id)
    return OutreachOut.model_validate(row)


@router.post("/{outreach_id}/approve", response_model=OutreachOut)
async def approve_outreach(
    outreach_id: UUID, user: CurrentUser, db: DbSession
) -> OutreachOut:
    row = await OutreachService(db).approve(user.id, outreach_id)
    return OutreachOut.model_validate(row)


@router.post("/{outreach_id}/reject", response_model=OutreachOut)
async def reject_outreach(
    outreach_id: UUID, user: CurrentUser, db: DbSession
) -> OutreachOut:
    row = await OutreachService(db).reject(user.id, outreach_id)
    return OutreachOut.model_validate(row)


@router.post("/{outreach_id}/send", response_model=OutreachOut)
async def send_outreach(
    outreach_id: UUID, user: CurrentUser, db: DbSession
) -> OutreachOut:
    row = await OutreachService(db).send(user.id, outreach_id)
    return OutreachOut.model_validate(row)
