"""User settings routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DbSession, require_csrf
from app.core.exceptions import NotFoundError
from app.models import UserSettings
from app.repositories.user_repository import UserRepository
from app.schemas import SettingsOut, SettingsUpdate
from app.services.audit_service import AuditService

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(require_csrf)])


@router.get("", response_model=SettingsOut)
async def get_settings(user: CurrentUser, db: DbSession) -> SettingsOut:
    settings = await UserRepository(db).get_settings(user.id)
    if not settings:
        raise NotFoundError("Settings not found")
    return SettingsOut.model_validate(settings)


@router.patch("", response_model=SettingsOut)
async def update_settings(
    data: SettingsUpdate, user: CurrentUser, db: DbSession
) -> SettingsOut:
    settings = await UserRepository(db).get_settings(user.id)
    if not settings:
        settings = UserSettings(user_id=user.id)
        db.add(settings)
        await db.flush()
    payload = data.model_dump(exclude_unset=True)
    for key, value in payload.items():
        setattr(settings, key, value)
    if "daily_application_limit" in payload:
        user.daily_application_limit = payload["daily_application_limit"]
    await db.flush()
    await AuditService(db).log(
        actor=str(user.id),
        action="settings.update",
        entity_type="user_settings",
        entity_id=settings.id,
        details={"fields": list(payload.keys())},
    )
    return SettingsOut.model_validate(settings)
