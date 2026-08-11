"""Encrypted integration credentials."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import decrypt_value, encrypt_value
from app.models import IntegrationCredential
from app.services.audit_service import AuditService


class CredentialService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.audit = AuditService(db)

    async def list_for_user(self, user_id: UUID) -> list[IntegrationCredential]:
        result = await self.db.execute(
            select(IntegrationCredential)
            .where(IntegrationCredential.user_id == user_id)
            .order_by(IntegrationCredential.provider.asc())
        )
        return list(result.scalars().all())

    async def get(self, credential_id: UUID, user_id: UUID) -> IntegrationCredential:
        row = await self.db.get(IntegrationCredential, credential_id)
        if not row or row.user_id != user_id:
            raise NotFoundError("Credential not found")
        return row

    async def get_by_provider(
        self, user_id: UUID, provider: str
    ) -> IntegrationCredential | None:
        return (
            await self.db.execute(
                select(IntegrationCredential).where(
                    IntegrationCredential.user_id == user_id,
                    IntegrationCredential.provider == provider,
                )
            )
        ).scalar_one_or_none()

    def decrypt_payload(self, row: IntegrationCredential) -> dict:
        raw = decrypt_value(row.encrypted_payload, settings=self.settings)
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ConflictError("Stored credential payload is invalid")
        return data

    async def upsert(self, user_id: UUID, provider: str, payload: dict) -> IntegrationCredential:
        encrypted = encrypt_value(json.dumps(payload), settings=self.settings)
        existing = await self.get_by_provider(user_id, provider)
        if existing:
            existing.encrypted_payload = encrypted
            existing.status = "active"
            existing.last_verified_at = datetime.now(UTC)
            await self.db.flush()
            await self.audit.log(
                actor=str(user_id),
                action="credential.update",
                entity_type="integration_credential",
                entity_id=existing.id,
                details={"provider": provider},
            )
            return existing

        row = IntegrationCredential(
            user_id=user_id,
            provider=provider,
            encrypted_payload=encrypted,
            status="active",
            last_verified_at=datetime.now(UTC),
        )
        self.db.add(row)
        await self.db.flush()
        await self.audit.log(
            actor=str(user_id),
            action="credential.create",
            entity_type="integration_credential",
            entity_id=row.id,
            details={"provider": provider},
        )
        return row

    async def update(
        self,
        user_id: UUID,
        credential_id: UUID,
        *,
        payload: dict | None = None,
        status: str | None = None,
    ) -> IntegrationCredential:
        row = await self.get(credential_id, user_id)
        if payload is not None:
            row.encrypted_payload = encrypt_value(
                json.dumps(payload), settings=self.settings
            )
            row.last_verified_at = datetime.now(UTC)
        if status is not None:
            row.status = status
        await self.db.flush()
        await self.audit.log(
            actor=str(user_id),
            action="credential.update",
            entity_type="integration_credential",
            entity_id=row.id,
            details={"provider": row.provider, "status": row.status},
        )
        return row

    async def delete(self, user_id: UUID, credential_id: UUID) -> None:
        row = await self.get(credential_id, user_id)
        await self.db.delete(row)
        await self.db.flush()
        await self.audit.log(
            actor=str(user_id),
            action="credential.delete",
            entity_type="integration_credential",
            entity_id=credential_id,
            details={"provider": row.provider},
        )
