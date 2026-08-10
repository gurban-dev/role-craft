"""Company research via LLM with evidence requirements."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.logging import get_logger
from app.integrations.llm.factory import get_llm_provider
from app.integrations.llm.schemas import CompanyResearchResult
from app.models import CompanyResearch, Job, User
from app.repositories.user_repository import UserRepository

logger = get_logger(__name__)


class ResearchService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.users = UserRepository(db)

    async def research_company(self, user: User, job_id: UUID) -> CompanyResearch:
        job = await self.db.get(Job, job_id)
        if not job:
            raise NotFoundError("Job not found")
        profile = await self.users.get_profile(user.id)
        if not profile:
            raise NotFoundError("Profile not found")

        existing = (
            await self.db.execute(
                select(CompanyResearch).where(
                    CompanyResearch.user_id == user.id, CompanyResearch.job_id == job_id
                )
            )
        ).scalar_one_or_none()

        result = await self._generate(job, profile.professional_summary, str(user.id))
        self._require_evidence(result)

        if existing:
            existing.company = result.company or job.company
            existing.problem_summary = result.problem_summary
            existing.evidence = [e.model_dump() for e in result.evidence]
            existing.sources = result.sources
            existing.confidence_score = result.confidence_score
            existing.candidate_value_proposition = result.candidate_value_proposition
            existing.raw_analysis = result.model_dump()
            await self.db.flush()
            return existing

        row = CompanyResearch(
            user_id=user.id,
            job_id=job_id,
            company=result.company or job.company,
            problem_summary=result.problem_summary,
            evidence=[e.model_dump() for e in result.evidence],
            sources=result.sources,
            confidence_score=result.confidence_score,
            candidate_value_proposition=result.candidate_value_proposition,
            raw_analysis=result.model_dump(),
        )
        self.db.add(row)
        await self.db.flush()
        logger.info("company_research_done", job_id=str(job_id), confidence=result.confidence_score)
        return row

    async def _generate(
        self, job: Job, candidate_summary: str, user_id: str
    ) -> CompanyResearchResult:
        if not self.settings.openai_api_key:
            # Offline/dev fallback with explicit low confidence
            return CompanyResearchResult(
                company=job.company,
                problem_summary=(
                    f"{job.company} is hiring for {job.title}. "
                    "Insufficient public evidence available without LLM."
                ),
                evidence=[],
                sources=[],
                confidence_score=0.0,
                candidate_value_proposition=candidate_summary[:500],
                notes="LLM unavailable; evidence required before outreach",
            )
        provider = get_llm_provider(self.settings, db=self.db)
        prompt = (
            "Research the company's likely problems related to this role. "
            "Every claim MUST include evidence with a source_url when possible. "
            "If evidence is weak, set confidence_score below 0.5 and say so.\n\n"
            f"Company: {job.company}\nRole: {job.title}\n"
            f"Description:\n{job.description[:5000]}\n\n"
            f"Candidate summary: {candidate_summary}"
        )
        return await provider.generate(
            prompt, CompanyResearchResult, operation="company_research", user_id=user_id
        )

    def _require_evidence(self, result: CompanyResearchResult) -> None:
        if result.confidence_score >= 0.5 and not result.evidence:
            raise ValidationAppError(
                "Company research with confidence >= 0.5 requires evidence items"
            )

    async def get(self, research_id: UUID, user_id: UUID) -> CompanyResearch:
        row = await self.db.get(CompanyResearch, research_id)
        if not row or row.user_id != user_id:
            raise NotFoundError("Research not found")
        return row

    async def research_for_application(
        self, user_id: UUID, application_id: UUID
    ) -> CompanyResearch:
        from app.models import Application, User

        user = await self.db.get(User, user_id)
        app = await self.db.get(Application, application_id)
        if not user or not app or app.user_id != user_id:
            raise NotFoundError("Application not found")
        research = await self.research_company(user, app.job_id)
        app.research_id = research.id
        await self.db.flush()
        return research
