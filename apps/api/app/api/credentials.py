"""Integration credential routes (encrypted at rest)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession, require_csrf
from app.schemas import CredentialOut
from app.services.credential_service import CredentialService

router = APIRouter(
    prefix="/credentials",
    tags=["credentials"],
    dependencies=[Depends(require_csrf)],
)


class CredentialCreate(BaseModel):
    provider: str = Field(min_length=1, max_length=64)
    payload: dict = Field(default_factory=dict)


class CredentialUpdate(BaseModel):
    payload: dict = Field(default_factory=dict)
    status: str | None = None


@router.get("", response_model=list[CredentialOut])
async def list_credentials(user: CurrentUser, db: DbSession) -> list[CredentialOut]:
    rows = await CredentialService(db).list_for_user(user.id)
    return [CredentialOut.model_validate(r) for r in rows]


@router.post("", response_model=CredentialOut)
async def create_credential(
    data: CredentialCreate, user: CurrentUser, db: DbSession
) -> CredentialOut:
    row = await CredentialService(db).upsert(user.id, data.provider, data.payload)
    return CredentialOut.model_validate(row)


@router.get("/{credential_id}", response_model=CredentialOut)
async def get_credential(
    credential_id: UUID, user: CurrentUser, db: DbSession
) -> CredentialOut:
    row = await CredentialService(db).get(credential_id, user.id)
    return CredentialOut.model_validate(row)


@router.patch("/{credential_id}", response_model=CredentialOut)
async def update_credential(
    credential_id: UUID, data: CredentialUpdate, user: CurrentUser, db: DbSession
) -> CredentialOut:
    row = await CredentialService(db).update(
        user.id, credential_id, payload=data.payload or None, status=data.status
    )
    return CredentialOut.model_validate(row)


@router.delete("/{credential_id}")
async def delete_credential(
    credential_id: UUID, user: CurrentUser, db: DbSession
) -> dict[str, str]:
    await CredentialService(db).delete(user.id, credential_id)
    return {"status": "ok"}
