"""Extract structured candidate profile from resume text / CandidateProfile."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models import CandidateProfile

logger = get_logger(__name__)


class StructuredCandidateProfile(BaseModel):
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    frontend: list[str] = Field(default_factory=list)
    backend: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    cloud: list[str] = Field(default_factory=list)
    devops: list[str] = Field(default_factory=list)
    infrastructure: list[str] = Field(default_factory=list)
    testing: list[str] = Field(default_factory=list)
    architecture: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    years_of_experience: float | None = None
    relevant_job_titles: list[str] = Field(default_factory=list)
    relevant_responsibilities: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    other_relevant_qualifications: list[str] = Field(default_factory=list)

    def to_display(self) -> str:
        lines = [
            f"Languages: {', '.join(self.languages) or '—'}",
            f"Frameworks: {', '.join(self.frameworks) or '—'}",
            f"Frontend: {', '.join(self.frontend) or '—'}",
            f"Backend: {', '.join(self.backend) or '—'}",
            f"Databases: {', '.join(self.databases) or '—'}",
            f"Cloud: {', '.join(self.cloud) or '—'}",
            f"DevOps: {', '.join(self.devops) or '—'}",
            f"Infrastructure: {', '.join(self.infrastructure) or '—'}",
            f"Testing: {', '.join(self.testing) or '—'}",
            f"Architecture: {', '.join(self.architecture) or '—'}",
            f"Tools: {', '.join(self.tools) or '—'}",
            f"Industries: {', '.join(self.industries) or '—'}",
            "Years of experience: "
            f"{self.years_of_experience if self.years_of_experience is not None else '—'}",
            f"Relevant job titles: {', '.join(self.relevant_job_titles) or '—'}",
            f"Relevant responsibilities: {'; '.join(self.relevant_responsibilities) or '—'}",
            f"Education: {'; '.join(self.education) or '—'}",
            "Other relevant qualifications: "
            f"{', '.join(self.other_relevant_qualifications) or '—'}",
        ]
        return "\n".join(lines)


class CandidateProfileExtractor:
    def __init__(self, db: AsyncSession | None = None, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    def from_candidate_profile(self, profile: CandidateProfile) -> StructuredCandidateProfile:
        if profile.structured_profile:
            try:
                return StructuredCandidateProfile.model_validate(profile.structured_profile)
            except Exception:
                pass
        return self._heuristic_from_profile(profile)

    def _heuristic_from_profile(self, profile: CandidateProfile) -> StructuredCandidateProfile:
        skills = [str(s.get("name") if isinstance(s, dict) else s) for s in (profile.skills or [])]
        skills_l = [s.lower() for s in skills]
        buckets = {
            "languages": [],
            "frameworks": [],
            "frontend": [],
            "backend": [],
            "databases": [],
            "cloud": [],
            "devops": [],
            "infrastructure": [],
            "testing": [],
            "architecture": [],
            "tools": [],
        }
        rules: list[tuple[str, tuple[str, ...]]] = [
            (
                "languages",
                ("python", "typescript", "javascript", "java", "go", "rust", "kotlin", "c#", "sql"),
            ),
            ("frameworks", ("django", "fastapi", "flask", "spring", "express", "nestjs")),
            ("frontend", ("react", "next.js", "vue", "angular", "svelte", "css", "html")),
            ("backend", ("fastapi", "django", "flask", "node", "nestjs", "spring")),
            ("databases", ("postgresql", "postgres", "mysql", "mongodb", "redis", "sqlite")),
            ("cloud", ("aws", "gcp", "azure", "cloudflare")),
            ("devops", ("docker", "kubernetes", "ci/cd", "github actions", "gitlab ci")),
            ("infrastructure", ("terraform", "ansible", "nginx", "linux")),
            ("testing", ("pytest", "jest", "playwright", "cypress", "unittest")),
            ("architecture", ("microservices", "rest", "graphql", "event-driven")),
            ("tools", ("git", "jira", "figma", "postman")),
        ]
        for skill, lower in zip(skills, skills_l, strict=False):
            placed = False
            for bucket, tokens in rules:
                if any(t in lower for t in tokens):
                    buckets[bucket].append(skill)
                    placed = True
            if not placed and skill:
                buckets["tools"].append(skill)

        titles = []
        responsibilities: list[str] = []
        for role in profile.work_history or []:
            if isinstance(role, dict):
                if role.get("title"):
                    titles.append(str(role["title"]))
                if role.get("responsibilities"):
                    responsibilities.extend(str(r) for r in role["responsibilities"])
                elif role.get("description"):
                    responsibilities.append(str(role["description"])[:240])

        education = []
        for ed in profile.education or []:
            if isinstance(ed, dict):
                education.append(
                    " — ".join(
                        str(x)
                        for x in [ed.get("degree"), ed.get("field"), ed.get("institution")]
                        if x
                    )
                )
            else:
                education.append(str(ed))

        return StructuredCandidateProfile(
            languages=buckets["languages"],
            frameworks=buckets["frameworks"],
            frontend=buckets["frontend"],
            backend=buckets["backend"],
            databases=buckets["databases"],
            cloud=buckets["cloud"],
            devops=buckets["devops"],
            infrastructure=buckets["infrastructure"],
            testing=buckets["testing"],
            architecture=buckets["architecture"],
            tools=buckets["tools"],
            industries=[],
            years_of_experience=profile.years_experience,
            relevant_job_titles=titles,
            relevant_responsibilities=responsibilities[:12],
            education=education,
            other_relevant_qualifications=[str(c) for c in (profile.certifications or [])],
        )

    async def extract_from_resume_text(
        self, resume_text: str, *, user_id: str | None = None
    ) -> StructuredCandidateProfile:
        """LLM extract when available; otherwise empty-safe heuristic from free text."""
        if self.settings.open_router_token and self.db is not None:
            from app.integrations.llm.factory import get_llm_provider

            provider = get_llm_provider(self.settings, db=self.db)
            prompt = (
                "Extract a structured software-engineering candidate profile from the resume. "
                "Only include technologies, experience, titles, and qualifications explicitly "
                "supported by the resume. Do not invent skills.\n\n"
                f"Resume:\n{resume_text[:12000]}"
            )
            try:
                return await provider.generate(
                    prompt,
                    StructuredCandidateProfile,
                    operation="resume_profile_extract",
                    user_id=user_id or "system",
                )
            except Exception as exc:
                logger.warning("resume_profile_llm_failed", error=str(exc))
        return self._heuristic_from_text(resume_text)

    def _heuristic_from_text(self, text: str) -> StructuredCandidateProfile:
        stub = CandidateProfile(
            user_id=__import__("uuid").uuid4(),
            skills=[],
            work_history=[],
            education=[],
            years_experience=0.0,
        )
        # Tokenize tech words present in text into skills list
        known = [
            "Python",
            "TypeScript",
            "JavaScript",
            "Java",
            "C#",
            "C++",
            "Go",
            "Rust",
            "Ruby",
            "PHP",
            "Kotlin",
            "React",
            "Next.js",
            "Vue",
            "Angular",
            "FastAPI",
            "Django",
            "Flask",
            "Node.js",
            "Spring",
            "PostgreSQL",
            "MySQL",
            "MongoDB",
            "Redis",
            "Docker",
            "Kubernetes",
            "Terraform",
            "AWS",
            "Azure",
            "GCP",
            "Playwright",
            "Jest",
            "pytest",
            "SQL",
            "GraphQL",
            "Kafka",
            "Git",
            "CI/CD",
        ]
        lower = text.lower()
        stub.skills = [k for k in known if k.lower() in lower]
        structured = self._heuristic_from_profile(stub)
        years = re.search(
            r"\b(\d+(?:\.\d+)?)\s*\+?\s+years?\s+(?:of\s+)?(?:professional\s+)?experience\b",
            lower,
        )
        structured.years_of_experience = float(years.group(1)) if years else None
        title_lines = [
            line.strip(" •\t-")
            for line in text.splitlines()
            if re.search(r"\b(engineer|developer|architect|programmer|technician)\b", line, re.I)
        ]
        structured.relevant_job_titles = title_lines[:8]
        return structured

    async def persist(
        self, profile: CandidateProfile, structured: StructuredCandidateProfile
    ) -> None:
        profile.structured_profile = structured.model_dump()
        # Sync flat skills for existing scorers without inventing new ones
        flat: list[Any] = []
        for key in (
            "languages",
            "frameworks",
            "frontend",
            "backend",
            "databases",
            "cloud",
            "devops",
            "infrastructure",
            "testing",
            "architecture",
            "tools",
        ):
            for item in getattr(structured, key):
                if item and item not in flat:
                    flat.append(item)
        existing = [
            str(skill.get("name") if isinstance(skill, dict) else skill)
            for skill in (profile.skills or [])
            if skill
        ]
        seen = {skill.casefold() for skill in existing}
        for skill in flat:
            if skill.casefold() not in seen:
                existing.append(skill)
                seen.add(skill.casefold())
        profile.skills = existing
        if structured.years_of_experience is not None:
            profile.years_experience = float(structured.years_of_experience)
        titles = " ".join(structured.relevant_job_titles).lower()
        for title_word, level in (
            ("principal", "principal"),
            ("staff", "staff"),
            ("lead", "lead"),
            ("senior", "senior"),
            ("junior", "junior"),
            ("intern", "intern"),
        ):
            if re.search(rf"\b{title_word}\b", titles):
                profile.seniority_level = level
                break
        if self.db is not None:
            await self.db.flush()
