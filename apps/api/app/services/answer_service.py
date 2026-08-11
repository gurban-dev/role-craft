"""Application answer drafting from candidate answer bank."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.integrations.llm.factory import get_llm_provider
from app.integrations.llm.schemas import ApplicationAnswerDraft
from app.models import Application, Job, User
from app.repositories.user_repository import UserRepository

logger = get_logger(__name__)


class AnswerService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.users = UserRepository(db)

    async def draft_for_application(
        self, user_id: UUID, application_id: UUID
    ) -> ApplicationAnswerDraft:
        user = await self.db.get(User, user_id)
        app = await self.db.get(Application, application_id)
        if not user or not app or app.user_id != user_id:
            raise NotFoundError("Application not found")
        profile = await self.users.get_profile(user_id)
        if not profile:
            raise NotFoundError("Profile not found")
        job = await self.db.get(Job, app.job_id)
        if not job:
            raise NotFoundError("Job not found")

        bank = profile.answer_bank or {}
        draft = await self._generate(job, bank, str(user_id))
        # Merge into application_answers without inventing high-confidence claims
        existing = dict(app.application_answers or {})
        answers = dict(existing.get("answers") or {})
        confidences = dict(existing.get("confidence_by_question") or {})
        answers.update(draft.answers)
        confidences.update(draft.confidence_by_question)
        app.application_answers = {
            **existing,
            "answers": answers,
            "confidence_by_question": confidences,
            "unanswered": draft.unanswered,
            "notes": draft.notes,
        }
        await self.db.flush()
        return draft

    async def _generate(
        self, job: Job, answer_bank: dict, user_id: str
    ) -> ApplicationAnswerDraft:
        if not self.settings.openai_api_key:
            # Deterministic offline draft from answer bank keys only
            answers = {str(k): str(v) for k, v in answer_bank.items() if v is not None}
            return ApplicationAnswerDraft(
                answers=answers,
                confidence_by_question={k: 0.85 for k in answers},
                unanswered=[],
                notes="Offline draft from answer bank",
            )
        provider = get_llm_provider(self.settings, db=self.db)
        prompt = (
            "Draft truthful application form answers using ONLY the answer bank. "
            "Do not invent experience. Leave unanswered when unknown. "
            "Set confidence_by_question for each answered field.\n\n"
            f"Role: {job.title} at {job.company}\n"
            f"Description excerpt:\n{(job.description or '')[:3000]}\n\n"
            f"Answer bank JSON:\n{answer_bank}"
        )
        return await provider.generate(
            prompt, ApplicationAnswerDraft, operation="application_answers", user_id=user_id
        )
