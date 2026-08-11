"""Application lifecycle orchestration."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    ConflictError,
    NeedsHumanActionError,
    NotFoundError,
    QualityGateError,
)
from app.core.logging import get_logger
from app.models import Application, User
from app.models.enums import ApplicationStatus
from app.repositories.application_repository import ApplicationRepository
from app.repositories.user_repository import UserRepository
from app.services.application_state import transition
from app.services.audit_service import AuditService
from app.services.quality_gate import QualityGateService

logger = get_logger(__name__)


class ApplicationService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.apps = ApplicationRepository(db)
        self.users = UserRepository(db)
        self.audit = AuditService(db)
        self.quality = QualityGateService(db, settings)

    async def get(self, application_id: UUID, user_id: UUID) -> Application:
        app = await self.apps.get_by_id(application_id)
        if not app or app.user_id != user_id:
            raise NotFoundError("Application not found")
        return app

    async def list(
        self, user_id: UUID, *, status: str | None = None, limit: int = 100
    ) -> list[Application]:
        return await self.apps.list_for_user(user_id, status=status, limit=limit)

    async def set_status(
        self,
        app: Application,
        target: ApplicationStatus | str,
        *,
        actor: str,
        reason: str | None = None,
    ) -> Application:
        previous = app.status
        new_status = transition(previous, target)
        app.status = new_status.value
        if reason:
            app.failure_reason = reason
        await self.db.flush()
        await self.audit.log(
            actor=actor,
            action="application.transition",
            entity_type="application",
            entity_id=app.id,
            previous_state=previous,
            new_state=new_status.value,
            details={"reason": reason} if reason else {},
        )
        return app

    async def begin_prepare(self, user: User, application_id: UUID) -> Application:
        """Mark prep in progress without claiming READY_FOR_REVIEW (avoids Celery race)."""
        app = await self.get(application_id, user.id)
        if app.status in {
            ApplicationStatus.READY_FOR_REVIEW.value,
            ApplicationStatus.APPLYING.value,
            ApplicationStatus.SUBMITTED.value,
            ApplicationStatus.RESUME_GENERATING.value,
            ApplicationStatus.CONTACT_RESEARCH.value,
        }:
            return app
        if app.status in {
            ApplicationStatus.DISCOVERED.value,
            ApplicationStatus.MATCHED.value,
            ApplicationStatus.ANALYZING.value,
            ApplicationStatus.FAILED.value,
            ApplicationStatus.NEEDS_HUMAN_ACTION.value,
        }:
            path = self._path_to(app.status, ApplicationStatus.RESUME_GENERATING)
            for step in path:
                await self.set_status(app, step, actor=str(user.id))
            if app.status != ApplicationStatus.RESUME_GENERATING.value:
                await self.set_status(
                    app, ApplicationStatus.RESUME_GENERATING, actor=str(user.id)
                )
        return app

    async def prepare(self, user: User, application_id: UUID) -> Application:
        """Mark application ready for human review after prep pipeline."""
        app = await self.get(application_id, user.id)
        if app.status == ApplicationStatus.READY_FOR_REVIEW.value:
            return app  # idempotent

        # Allow from several prep states
        if app.status in {
            ApplicationStatus.DISCOVERED.value,
            ApplicationStatus.MATCHED.value,
            ApplicationStatus.RESUME_GENERATING.value,
            ApplicationStatus.RESUME_READY.value,
            ApplicationStatus.CONTACT_RESEARCH.value,
            ApplicationStatus.ANALYZING.value,
        }:
            # Walk toward READY_FOR_REVIEW via legal hops when needed
            path = self._path_to(app.status, ApplicationStatus.READY_FOR_REVIEW)
            for step in path:
                await self.set_status(app, step, actor=str(user.id))
        elif app.status == ApplicationStatus.FAILED.value:
            await self.set_status(app, ApplicationStatus.READY_FOR_REVIEW, actor=str(user.id))
        else:
            await self.set_status(app, ApplicationStatus.READY_FOR_REVIEW, actor=str(user.id))
        return app

    def _path_to(self, current: str, target: ApplicationStatus) -> list[ApplicationStatus]:
        """Best-effort linear path for common prep flow."""
        order = [
            ApplicationStatus.DISCOVERED,
            ApplicationStatus.ANALYZING,
            ApplicationStatus.MATCHED,
            ApplicationStatus.RESUME_GENERATING,
            ApplicationStatus.RESUME_READY,
            ApplicationStatus.CONTACT_RESEARCH,
            ApplicationStatus.READY_FOR_REVIEW,
        ]
        try:
            start = ApplicationStatus(current)
            if start == target:
                return []
            if start in order and target in order:
                si = order.index(start)
                ti = order.index(target)
                if si < ti:
                    return order[si + 1 : ti + 1]
        except ValueError:
            pass
        return [target]

    async def approve(
        self, user: User, application_id: UUID, *, idempotency_key: str | None = None
    ) -> Application:
        app = await self.get(application_id, user.id)
        if idempotency_key:
            existing = await self.apps.get_by_idempotency_key(idempotency_key)
            if existing and existing.id != app.id:
                raise ConflictError("Idempotency key already used for another application")
            if app.idempotency_key and app.idempotency_key != idempotency_key:
                raise ConflictError("Application already has a different idempotency key")
            app.idempotency_key = idempotency_key

        if app.approved_at and app.status == ApplicationStatus.READY_FOR_REVIEW.value:
            return app  # idempotent re-approve

        if app.status not in {
            ApplicationStatus.READY_FOR_REVIEW.value,
            ApplicationStatus.NEEDS_HUMAN_ACTION.value,
        }:
            raise ConflictError(f"Cannot approve from status {app.status}")

        app.approved_at = datetime.now(UTC)
        app.approved_by = user.id
        if not app.idempotency_key:
            app.idempotency_key = f"approve:{app.id}:{uuid4().hex[:8]}"
        await self.db.flush()
        await self.audit.log(
            actor=str(user.id),
            action="application.approve",
            entity_type="application",
            entity_id=app.id,
            previous_state=app.status,
            new_state=app.status,
        )
        return app

    async def submit(
        self,
        user: User,
        application_id: UUID,
        *,
        idempotency_key: str | None = None,
        automation_result: dict | None = None,
    ) -> Application:
        app = await self.get(application_id, user.id)

        if idempotency_key:
            existing = await self.apps.get_by_idempotency_key(idempotency_key)
            if existing:
                if existing.id == app.id and existing.status == ApplicationStatus.SUBMITTED.value:
                    return existing
                if existing.id != app.id:
                    raise ConflictError("Idempotency key already used")
            app.idempotency_key = idempotency_key

        if app.status == ApplicationStatus.SUBMITTED.value:
            return app  # idempotent

        # Daily limit
        submitted_today = await self.apps.count_submitted_today(user.id)
        settings = await self.users.get_settings(user.id)
        limit = (
            settings.daily_application_limit
            if settings
            else self.settings.daily_application_limit
        )
        if submitted_today >= limit:
            raise ConflictError("Daily application limit reached")

        try:
            await self.quality.require_pass(app)
        except QualityGateError:
            await self.set_status(
                app,
                ApplicationStatus.NEEDS_HUMAN_ACTION,
                actor=str(user.id),
                reason="Quality gate failed",
            )
            raise

        if app.status != ApplicationStatus.APPLYING.value:
            await self.set_status(app, ApplicationStatus.APPLYING, actor=str(user.id))

        result = automation_result or {}
        if result.get("deferred"):
            return app
        if result.get("needs_human_action") or result.get("captcha") or result.get("mfa"):
            reason = result.get("reason") or "CAPTCHA/MFA or human action required"
            await self.set_status(
                app,
                ApplicationStatus.NEEDS_HUMAN_ACTION,
                actor="automation",
                reason=reason,
            )
            raise NeedsHumanActionError(reason)

        if result.get("failed"):
            await self.set_status(
                app,
                ApplicationStatus.FAILED,
                actor="automation",
                reason=result.get("reason") or "Submit failed",
            )
            raise ConflictError(app.failure_reason or "Submit failed")

        app.submitted_at = datetime.now(UTC)
        app.confirmation_text = result.get("confirmation_text")
        app.confirmation_url = result.get("confirmation_url")
        app.screenshot_path = result.get("screenshot_path")
        app.external_application_id = result.get("external_application_id")
        if result.get("browser_automation_run_id"):
            with contextlib.suppress(ValueError):
                app.browser_automation_run_id = UUID(str(result["browser_automation_run_id"]))
        await self.set_status(app, ApplicationStatus.SUBMITTED, actor=str(user.id))
        logger.info("application_submitted", application_id=str(app.id))
        return app

    async def begin_submit(self, user: User, application_id: UUID) -> Application:
        """Validate quality gate and move into APPLYING before browser automation."""
        app = await self.get(application_id, user.id)
        if app.status == ApplicationStatus.SUBMITTED.value:
            return app
        if app.status == ApplicationStatus.APPLYING.value:
            return app
        submitted_today = await self.apps.count_submitted_today(user.id)
        settings = await self.users.get_settings(user.id)
        limit = (
            settings.daily_application_limit
            if settings
            else self.settings.daily_application_limit
        )
        if submitted_today >= limit:
            raise ConflictError("Daily application limit reached")
        await self.quality.require_pass(app)
        return await self.set_status(app, ApplicationStatus.APPLYING, actor=str(user.id))

    async def mark_needs_human(self, user: User, application_id: UUID, reason: str) -> Application:
        app = await self.get(application_id, user.id)
        return await self.set_status(
            app,
            ApplicationStatus.NEEDS_HUMAN_ACTION,
            actor=str(user.id),
            reason=reason,
        )

    async def record_submission(
        self,
        user: User,
        application_id: UUID,
        *,
        confirmation_text: str | None = None,
        confirmation_url: str | None = None,
        external_id: str | None = None,
        screenshot_path: str | None = None,
        run_id: UUID | None = None,
    ) -> Application:
        return await self.submit(
            user,
            application_id,
            automation_result={
                "confirmation_text": confirmation_text,
                "confirmation_url": confirmation_url,
                "external_application_id": external_id,
                "screenshot_path": screenshot_path,
                "browser_automation_run_id": str(run_id) if run_id else None,
            },
        )
