"""Contact discovery via LLM (recruiter preferred)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.integrations.llm.factory import get_llm_provider
from app.integrations.llm.schemas import ContactRecommendation
from app.models import Contact, Job, User
from app.models.enums import ContactType

logger = get_logger(__name__)


class ContactService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    async def discover(self, user: User, job_id: UUID) -> Contact | None:
        job = await self.db.get(Job, job_id)
        if not job:
            raise NotFoundError("Job not found")

        recommendation = await self._recommend(job, str(user.id))
        if recommendation.confidence_score < self.settings.min_contact_confidence:
            logger.info(
                "contact_skipped_low_confidence",
                job_id=str(job_id),
                confidence=recommendation.confidence_score,
            )
            return None

        # Prefer recruiter; never return both recruiter + HM as primary
        contact_type = recommendation.contact_type.upper()
        if contact_type not in {c.value for c in ContactType}:
            contact_type = ContactType.RECRUITER.value
        # Force recruiter preference when type is ambiguous
        if (
            contact_type == ContactType.HIRING_MANAGER.value
            and recommendation.confidence_score < 0.8
        ):
            contact_type = ContactType.RECRUITER.value

        existing = (
            await self.db.execute(
                select(Contact).where(
                    Contact.user_id == user.id,
                    Contact.job_id == job_id,
                    Contact.contact_type == contact_type,
                )
            )
        ).scalar_one_or_none()

        if existing:
            existing.name = recommendation.name or existing.name
            existing.title = recommendation.title
            existing.linkedin_url = recommendation.linkedin_url
            existing.email = recommendation.email
            existing.confidence_score = recommendation.confidence_score
            existing.evidence = [e.model_dump() for e in recommendation.evidence]
            existing.why_selected = recommendation.why_selected
            existing.source = recommendation.source
            await self.db.flush()
            return existing

        contact = Contact(
            user_id=user.id,
            job_id=job_id,
            name=recommendation.name or "Unknown Recruiter",
            title=recommendation.title,
            company=recommendation.company or job.company,
            linkedin_url=recommendation.linkedin_url,
            email=recommendation.email,
            source=recommendation.source,
            confidence_score=recommendation.confidence_score,
            contact_type=contact_type,
            evidence=[e.model_dump() for e in recommendation.evidence],
            why_selected=recommendation.why_selected,
        )
        self.db.add(contact)
        await self.db.flush()
        return contact

    async def _recommend(self, job: Job, user_id: str) -> ContactRecommendation:
        if not self.settings.openai_api_key:
            return ContactRecommendation(
                name="",
                company=job.company,
                contact_type=ContactType.RECRUITER.value,
                confidence_score=0.0,
                why_selected="LLM unavailable; cannot verify contact identity",
                evidence=[],
            )
        provider = get_llm_provider(self.settings, db=self.db)
        prompt = (
            "Recommend ONE primary contact for outreach about this role. "
            "Prefer a recruiter over a hiring manager. "
            "Include evidence and confidence. Do not invent emails.\n\n"
            f"Company: {job.company}\nRole: {job.title}\nURL: {job.source_url}\n"
            f"Description excerpt:\n{job.description[:3000]}"
        )
        return await provider.generate(
            prompt, ContactRecommendation, operation="contact_discovery", user_id=user_id
        )

    async def get(self, contact_id: UUID, user_id: UUID) -> Contact:
        contact = await self.db.get(Contact, contact_id)
        if not contact or contact.user_id != user_id:
            raise NotFoundError("Contact not found")
        return contact

    async def list_for_job(self, user_id: UUID, job_id: UUID) -> list[Contact]:
        result = await self.db.execute(
            select(Contact).where(Contact.user_id == user_id, Contact.job_id == job_id)
        )
        return list(result.scalars().all())

    async def discover_for_application(self, user_id: UUID, application_id: UUID) -> Contact | None:
        from app.models import Application, User

        user = await self.db.get(User, user_id)
        app = await self.db.get(Application, application_id)
        if not user or not app or app.user_id != user_id:
            raise NotFoundError("Application not found")
        contact = await self.discover(user, app.job_id)
        if contact:
            app.contact_id = contact.id
            await self.db.flush()
        return contact
