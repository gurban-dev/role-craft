"""Contact routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.schemas import ContactOut
from app.services.contact_service import ContactService

router = APIRouter(prefix="/contacts", tags=["contacts"])


class DiscoverRequest(BaseModel):
    job_id: UUID


@router.post("/discover", response_model=ContactOut | None)
async def discover_contact(
    data: DiscoverRequest, user: CurrentUser, db: DbSession
) -> ContactOut | None:
    contact = await ContactService(db).discover(user, data.job_id)
    if not contact:
        return None
    return ContactOut.model_validate(contact)


@router.get("/job/{job_id}", response_model=list[ContactOut])
async def list_contacts(
    job_id: UUID, user: CurrentUser, db: DbSession
) -> list[ContactOut]:
    contacts = await ContactService(db).list_for_job(user.id, job_id)
    return [ContactOut.model_validate(c) for c in contacts]


@router.get("/{contact_id}", response_model=ContactOut)
async def get_contact(contact_id: UUID, user: CurrentUser, db: DbSession) -> ContactOut:
    contact = await ContactService(db).get(contact_id, user.id)
    return ContactOut.model_validate(contact)
