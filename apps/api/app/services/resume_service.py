"""Resume tailoring, validation, and PDF generation."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any
from uuid import UUID

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.logging import get_logger
from app.integrations.llm.factory import get_llm_provider
from app.integrations.llm.schemas import ResumeChanges
from app.models import CandidateProfile, Job, Resume, User
from app.models.enums import ResumeKind
from app.repositories.user_repository import UserRepository

logger = get_logger(__name__)


class ResumeService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.users = UserRepository(db)

    async def tailor_for_job(self, user: User, job_id: UUID) -> Resume:
        profile = await self.users.get_profile(user.id)
        if not profile:
            raise NotFoundError("Profile not found")
        job = await self.db.get(Job, job_id)
        if not job:
            raise NotFoundError("Job not found")

        changes = await self._generate_changes(profile, job, user_id=str(user.id))
        self.validate_truthful(profile, changes)

        content = self._build_content(profile, changes)
        quality = self.score_quality(content, job)
        explainability = list(changes.explainability)

        version = await self._next_version(user.id, job_id)
        resume = Resume(
            user_id=user.id,
            candidate_id=profile.id,
            job_id=job_id,
            kind=ResumeKind.TAILORED.value,
            version=version,
            content=content,
            generation_metadata={
                "model": self.settings.openai_model,
                "highlighted_skills": changes.highlighted_skills,
                "keyword_alignments": changes.keyword_alignments,
            },
            ats_analysis={"keyword_alignments": changes.keyword_alignments},
            quality_score=quality,
            explainability=explainability,
        )
        self.db.add(resume)
        await self.db.flush()

        pdf_path = self.render_pdf(resume)
        resume.file_path = str(pdf_path)
        resume.checksum = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
        await self.db.flush()
        logger.info("resume_tailored", resume_id=str(resume.id), quality=quality)
        return resume

    async def _generate_changes(
        self, profile: CandidateProfile, job: Job, *, user_id: str
    ) -> ResumeChanges:
        # Prefer LLM when configured; otherwise deterministic truthful subset
        if self.settings.openai_api_key:
            provider = get_llm_provider(self.settings, db=self.db)
            prompt = (
                "Tailor a resume using ONLY facts from the candidate profile. "
                "Do not invent employers, titles, dates, skills, or accomplishments. "
                "If unsure, omit. invented_claims must be empty.\n\n"
                f"PROFILE:\n{profile.professional_summary}\n"
                f"skills={profile.skills}\nwork_history={profile.work_history}\n"
                f"projects={profile.projects}\naccomplishments={profile.quantified_accomplishments}\n\n"
                f"JOB:\n{job.title} at {job.company}\n{job.description[:4000]}"
            )
            return await provider.generate(
                prompt, ResumeChanges, operation="resume_tailor", user_id=user_id
            )
        return self._deterministic_changes(profile, job)

    @staticmethod
    def _deterministic_changes(profile: CandidateProfile, job: Job) -> ResumeChanges:
        job_blob = f"{job.title} {job.description}".lower()
        skills = []
        for s in profile.skills or []:
            name = s if isinstance(s, str) else str(s.get("name", s) if isinstance(s, dict) else s)
            if name.lower() in job_blob or True:
                skills.append(name)
        skills = skills[:12]
        return ResumeChanges(
            summary=profile.professional_summary or "",
            highlighted_skills=skills,
            reordered_experience=list(profile.work_history or [])[:5],
            selected_projects=list(profile.projects or [])[:3],
            selected_accomplishments=[
                str(a) for a in (profile.quantified_accomplishments or [])[:5]
            ],
            keyword_alignments=skills[:8],
            explainability=["Deterministic tailoring from profile facts only"],
            invented_claims=[],
        )

    def validate_truthful(self, profile: CandidateProfile, changes: ResumeChanges) -> None:
        if changes.invented_claims:
            raise ValidationAppError(
                "Resume contains invented claims: " + ", ".join(changes.invented_claims)
            )
        known_skills = {
            (s.lower() if isinstance(s, str) else str(s.get("name", "")).lower())
            for s in (profile.skills or [])
            if s
        }
        # Also allow skills appearing in work history / projects text
        blob = " ".join(
            [
                profile.professional_summary or "",
                str(profile.work_history),
                str(profile.projects),
                str(profile.certifications),
            ]
        ).lower()
        for skill in changes.highlighted_skills:
            sl = skill.lower()
            if sl not in known_skills and sl not in blob:
                raise ValidationAppError(f"Skill not found in profile: {skill}")

    def score_quality(self, content: dict[str, Any], job: Job) -> float:
        score = 0.4
        if content.get("summary"):
            score += 0.15
        skills = content.get("skills") or []
        if skills:
            score += 0.15
        if content.get("experience"):
            score += 0.15
        job_tokens = set(re.findall(r"[a-z0-9+#.]{3,}", (job.description or "").lower()))
        skill_tokens = {str(s).lower() for s in skills}
        overlap = len(job_tokens & skill_tokens)
        score += min(0.15, overlap * 0.02)
        return round(min(1.0, score), 4)

    def _build_content(
        self, profile: CandidateProfile, changes: ResumeChanges
    ) -> dict[str, Any]:
        return {
            "summary": changes.summary or profile.professional_summary,
            "skills": changes.highlighted_skills or profile.skills,
            "experience": changes.reordered_experience or profile.work_history,
            "education": profile.education,
            "projects": changes.selected_projects or profile.projects,
            "accomplishments": changes.selected_accomplishments
            or profile.quantified_accomplishments,
            "personal_info": profile.personal_info,
        }

    def render_pdf(self, resume: Resume) -> Path:
        storage = Path(self.settings.storage_path) / "resumes"
        storage.mkdir(parents=True, exist_ok=True)
        path = storage / f"{resume.id}.pdf"
        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(str(path), pagesize=letter)
        story = []
        content = resume.content or {}
        info = content.get("personal_info") or {}
        name = info.get("name") or info.get("full_name") or "Candidate"
        story.append(Paragraph(str(name), styles["Title"]))
        story.append(Spacer(1, 12))
        if content.get("summary"):
            story.append(Paragraph("Summary", styles["Heading2"]))
            story.append(Paragraph(str(content["summary"]), styles["Normal"]))
            story.append(Spacer(1, 8))
        if content.get("skills"):
            story.append(Paragraph("Skills", styles["Heading2"]))
            skills = ", ".join(str(s) for s in content["skills"])
            story.append(Paragraph(skills, styles["Normal"]))
            story.append(Spacer(1, 8))
        if content.get("experience"):
            story.append(Paragraph("Experience", styles["Heading2"]))
            for item in content["experience"]:
                text = item if isinstance(item, str) else str(item)
                story.append(Paragraph(text[:2000], styles["Normal"]))
                story.append(Spacer(1, 4))
        if content.get("accomplishments"):
            story.append(Paragraph("Accomplishments", styles["Heading2"]))
            for item in content["accomplishments"]:
                story.append(Paragraph(f"• {item}", styles["Normal"]))
        doc.build(story)
        return path

    async def _next_version(self, user_id: UUID, job_id: UUID) -> int:
        result = await self.db.execute(
            select(func.max(Resume.version)).where(
                Resume.user_id == user_id, Resume.job_id == job_id
            )
        )
        current = result.scalar_one_or_none() or 0
        return int(current) + 1

    async def get(self, resume_id: UUID, user_id: UUID) -> Resume:
        resume = await self.db.get(Resume, resume_id)
        if not resume or resume.user_id != user_id:
            raise NotFoundError("Resume not found")
        return resume

    async def generate_for_application(self, user_id: UUID, application_id: UUID) -> Resume:
        from app.models import Application, User

        user = await self.db.get(User, user_id)
        app = await self.db.get(Application, application_id)
        if not user or not app or app.user_id != user_id:
            raise NotFoundError("Application not found")
        resume = await self.tailor_for_job(user, app.job_id)
        app.tailored_resume_id = resume.id
        await self.db.flush()
        return resume
