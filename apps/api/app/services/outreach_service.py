"""Outreach message generation."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.integrations.llm.factory import get_llm_provider
from app.integrations.llm.schemas import OutreachDraft
from app.models import Application, CompanyResearch, Contact, OutreachMessage, User
from app.models.enums import ContactType, OutreachStatus
from app.services.audit_service import AuditService

logger = get_logger(__name__)


class OutreachService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.audit = AuditService(db)

    async def get(self, outreach_id: UUID, user_id: UUID) -> OutreachMessage:
        msg = await self.db.get(OutreachMessage, outreach_id)
        if not msg or msg.user_id != user_id:
            raise NotFoundError("Outreach message not found")
        return msg

    async def list_for_user(
        self, user_id: UUID, *, status: str | None = None, limit: int = 100
    ) -> list[OutreachMessage]:
        stmt = (
            select(OutreachMessage)
            .where(OutreachMessage.user_id == user_id)
            .order_by(OutreachMessage.created_at.desc())
            .limit(limit)
        )
        if status:
            stmt = stmt.where(OutreachMessage.status == status)
        return list((await self.db.execute(stmt)).scalars().all())

    async def approve(self, user_id: UUID, outreach_id: UUID) -> OutreachMessage:
        msg = await self.get(outreach_id, user_id)
        if msg.status == OutreachStatus.APPROVED.value:
            return msg
        if msg.status in {
            OutreachStatus.SKIPPED.value,
            OutreachStatus.REJECTED.value,
            OutreachStatus.SENT.value,
        }:
            raise ConflictError(f"Cannot approve outreach in status {msg.status}")
        previous = msg.status
        msg.status = OutreachStatus.APPROVED.value
        await self.db.flush()
        await self.audit.log(
            actor=str(user_id),
            action="outreach.approve",
            entity_type="outreach_message",
            entity_id=msg.id,
            previous_state=previous,
            new_state=msg.status,
        )
        return msg

    async def reject(self, user_id: UUID, outreach_id: UUID) -> OutreachMessage:
        msg = await self.get(outreach_id, user_id)
        if msg.status == OutreachStatus.REJECTED.value:
            return msg
        if msg.status == OutreachStatus.SENT.value:
            raise ConflictError("Cannot reject a sent outreach message")
        previous = msg.status
        msg.status = OutreachStatus.REJECTED.value
        await self.db.flush()
        await self.audit.log(
            actor=str(user_id),
            action="outreach.reject",
            entity_type="outreach_message",
            entity_id=msg.id,
            previous_state=previous,
            new_state=msg.status,
        )
        return msg

    async def send(self, user_id: UUID, outreach_id: UUID) -> OutreachMessage:
        """Mark outreach as sent after approval (delivery is external/manual)."""
        msg = await self.get(outreach_id, user_id)
        if msg.status == OutreachStatus.SENT.value:
            return msg
        if msg.status not in {
            OutreachStatus.APPROVED.value,
            OutreachStatus.PENDING_APPROVAL.value,
        }:
            # Allow send from draft only if already approved via PENDING path
            if msg.status == OutreachStatus.DRAFT.value:
                raise ConflictError("Outreach must be approved before send")
            raise ConflictError(f"Cannot send outreach in status {msg.status}")
        if not msg.generated_message or msg.generated_message.startswith("[SKIPPED]"):
            raise ConflictError("Outreach message is empty or was skipped")
        previous = msg.status
        msg.status = OutreachStatus.SENT.value
        msg.sent_at = datetime.now(UTC)
        await self.db.flush()
        await self.audit.log(
            actor=str(user_id),
            action="outreach.send",
            entity_type="outreach_message",
            entity_id=msg.id,
            previous_state=previous,
            new_state=msg.status,
        )
        return msg

    async def generate_for_application(
        self, user_id: UUID | User, application_id: UUID
    ) -> OutreachMessage | None:
        if isinstance(user_id, User):
            user = user_id
        else:
            user = await self.db.get(User, user_id)
            if not user:
                raise NotFoundError("User not found")
        app = await self.db.get(Application, application_id)
        if not app or app.user_id != user.id:
            raise NotFoundError("Application not found")

        if not self.settings.outreach_enabled:
            return await self._skip(user, app, "Outreach disabled in settings")

        research = None
        if app.research_id:
            research = await self.db.get(CompanyResearch, app.research_id)
        if research is None:
            research = (
                await self.db.execute(
                    select(CompanyResearch).where(
                        CompanyResearch.user_id == user.id,
                        CompanyResearch.job_id == app.job_id,
                    )
                )
            ).scalar_one_or_none()

        contact = None
        if app.contact_id:
            contact = await self.db.get(Contact, app.contact_id)
        if contact is None:
            # Prefer recruiter only — never both recruiter + HM
            contact = (
                await self.db.execute(
                    select(Contact)
                    .where(
                        Contact.user_id == user.id,
                        Contact.job_id == app.job_id,
                        Contact.contact_type == ContactType.RECRUITER.value,
                    )
                    .order_by(Contact.confidence_score.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if contact is None:
                contact = (
                    await self.db.execute(
                        select(Contact)
                        .where(Contact.user_id == user.id, Contact.job_id == app.job_id)
                        .order_by(Contact.confidence_score.desc())
                        .limit(1)
                    )
                ).scalar_one_or_none()

        evidence_confidence = research.confidence_score if research else 0.0
        if evidence_confidence < self.settings.min_outreach_evidence_confidence:
            return await self._skip(
                user,
                app,
                f"Weak research evidence ({evidence_confidence})",
            )
        if not contact or contact.confidence_score < self.settings.min_contact_confidence:
            return await self._skip(user, app, "No sufficiently confident contact")

        draft = await self._draft(user, app, research, contact)
        if draft.skip_reason:
            return await self._skip(user, app, draft.skip_reason)

        msg = OutreachMessage(
            user_id=user.id,
            application_id=app.id,
            contact_id=contact.id,
            recipient_name=draft.recipient_name or contact.name,
            recipient_type=contact.contact_type,
            company_problem=draft.company_problem or (research.problem_summary if research else ""),
            evidence=draft.evidence
            and [e.model_dump() for e in draft.evidence]
            or (research.evidence if research else []),
            value_proposition=draft.value_proposition
            or (research.candidate_value_proposition if research else ""),
            generated_message=draft.message,
            status=OutreachStatus.DRAFT.value,
            channel=draft.channel,
            source="ai",
        )
        self.db.add(msg)
        await self.db.flush()
        app.outreach_id = msg.id
        await self.db.flush()
        return msg

    async def _draft(
        self,
        user: User,
        app: Application,
        research: CompanyResearch | None,
        contact: Contact,
    ) -> OutreachDraft:
        if not self.settings.openai_api_key:
            return OutreachDraft(
                recipient_name=contact.name,
                recipient_type=contact.contact_type,
                company_problem=research.problem_summary if research else "",
                value_proposition=research.candidate_value_proposition if research else "",
                message=(
                    f"Hi {contact.name},\n\n"
                    f"I'm interested in the role and believe I can help with: "
                    f"{(research.problem_summary if research else 'your team goals')}.\n\n"
                    "Happy to share more details.\n"
                ),
                confidence_score=research.confidence_score if research else 0.0,
            )
        provider = get_llm_provider(self.settings, db=self.db)
        prompt = (
            "Write a concise, personalized outreach message. "
            "Use only provided evidence. If evidence is weak, set skip_reason.\n"
            f"Contact: {contact.name} ({contact.contact_type}) at {contact.company}\n"
            f"Research: {research.problem_summary if research else ''}\n"
            f"Evidence: {research.evidence if research else []}\n"
            f"Value prop: {research.candidate_value_proposition if research else ''}"
        )
        return await provider.generate(
            prompt, OutreachDraft, operation="outreach_generate", user_id=str(user.id)
        )

    async def _skip(
        self, user: User, app: Application, reason: str
    ) -> OutreachMessage:
        msg = OutreachMessage(
            user_id=user.id,
            application_id=app.id,
            recipient_name="",
            recipient_type=ContactType.RECRUITER.value,
            company_problem="",
            evidence=[],
            value_proposition="",
            generated_message="",
            status=OutreachStatus.SKIPPED.value,
            channel="email",
            source="system",
        )
        # Store reason in generated_message for visibility
        msg.generated_message = f"[SKIPPED] {reason}"
        self.db.add(msg)
        await self.db.flush()
        app.outreach_id = msg.id
        await self.db.flush()
        logger.info("outreach_skipped", application_id=str(app.id), reason=reason)
        return msg
