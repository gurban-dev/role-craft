"""Audit logging service."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log(
        self,
        *,
        actor: str,
        action: str,
        entity_type: str,
        entity_id: str | UUID,
        previous_state: str | None = None,
        new_state: str | None = None,
        result: str = "Success",
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            previous_state=previous_state,
            new_state=new_state,
            result=result,
            details=details or {},
        )
        self.db.add(entry)
        await self.db.flush()
        return entry
