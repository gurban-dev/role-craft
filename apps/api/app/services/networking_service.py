"""Networking research: recruiter, hiring manager, peer discovery."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models import Contact, Job, User
from app.models.enums import ContactType

logger = get_logger(__name__)

RECRUITER_TITLE_RE = re.compile(
    r"technical recruiter|engineering recruiter|talent (acquisition )?partner|"
    r"talent acquisition|technical talent|internal recruiter|recruiter",
    re.I,
)
EXTERNAL_RECRUITER_RE = re.compile(
    r"agency|staffing|consultant|freelance recruiter|independent recruiter",
    re.I,
)
HM_TITLE_RE = re.compile(
    r"engineering manager|software engineering manager|engineering lead|"
    r"team lead|director of engineering|head of engineering|eng manager",
    re.I,
)
PEER_TITLE_RE = re.compile(
    r"software engineer|software developer|full[\s-]?stack|backend|frontend|"
    r"web developer|application developer",
    re.I,
)


@dataclass
class Prospect:
    name: str
    persona: str  # Recruiter | Hiring Manager | Peer
    title: str
    relevance_score: float
    linkedin_url: str
    email: str = ""
    notes: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    currently_employed: bool = False


class NetworkingService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    async def research_job_link(self, user: User, job_link: str) -> dict[str, Any]:
        job = await self._resolve_job(user, job_link)
        analysis = self._analyze_job(job)
        prospects = await self._find_prospects(job, analysis)
        prospects = [p for p in prospects if p.currently_employed and p.relevance_score >= self.settings.min_relevance_score_10]
        prospects = self._prioritize(prospects, analysis)
        saved = await self._persist_prospects(user, job, prospects)

        by_persona: dict[str, list[Prospect]] = {
            "Recruiter": [],
            "Hiring Manager": [],
            "Peer": [],
        }
        for p in prospects:
            by_persona.setdefault(p.persona, []).append(p)
        for key in by_persona:
            by_persona[key] = sorted(
                by_persona[key], key=lambda x: -x.relevance_score
            )[:8]

        table_rows = []
        n = 1
        for persona in ("Recruiter", "Hiring Manager", "Peer"):
            for p in by_persona.get(persona, []):
                table_rows.append(
                    {
                        "rank": n,
                        "name": p.name,
                        "persona": p.persona,
                        "title": p.title,
                        "relevance_score": p.relevance_score,
                        "linkedin_url": p.linkedin_url,
                        "email": p.email,
                        "notes": p.notes[:99],
                    }
                )
                n += 1

        priority = [
            {
                "priority": i,
                "name": p.name,
                "persona": p.persona,
                "why": self._why_reach_out(p, analysis),
            }
            for i, p in enumerate(self._outreach_priority(prospects), start=1)
        ]
        return {
            "job_id": str(job.id),
            "job_analysis": analysis,
            "contacts": table_rows,
            "priority": priority,
            "saved_contact_ids": [str(c.id) for c in saved],
        }

    async def _resolve_job(self, user: User, job_link: str) -> Job:
        result = await self.db.execute(
            select(Job).where(
                (Job.source_url == job_link)
                | (Job.official_application_url == job_link)
            )
        )
        job = result.scalar_one_or_none()
        if job:
            return job
        # Create lightweight job shell from URL for networking mode
        job = Job(
            title="Software Engineer",
            company=self._guess_company_from_url(job_link),
            description="",
            source="networking_link",
            source_url=job_link,
            official_application_url=job_link,
            external_job_id=job_link[:240],
            is_eea=True,
        )
        self.db.add(job)
        await self.db.flush()
        return job

    def _analyze_job(self, job: Job) -> dict[str, Any]:
        desc = job.description or ""
        techs = list(job.technologies or [])
        return {
            "core_skills": techs[:12],
            "responsibilities": list(job.responsibilities or [])[:8],
            "team_function": "engineering",
            "location": job.location,
            "seniority": "mid",
            "technologies": techs,
            "business_domain": job.company,
            "title": job.title,
            "company": job.company,
            "description_excerpt": desc[:2000],
        }

    async def _find_prospects(self, job: Job, analysis: dict[str, Any]) -> list[Prospect]:
        prospects: list[Prospect] = []
        prospects.extend(await self._apify_employees(job, analysis))
        prospects.extend(await self._vibe_prospects(job, analysis))
        # Dedupe by LinkedIn URL
        seen: set[str] = set()
        unique: list[Prospect] = []
        for p in prospects:
            key = (p.linkedin_url or p.name).lower()
            if key in seen or not p.linkedin_url:
                continue
            if "/in/" not in p.linkedin_url.lower():
                continue  # reject search/directory URLs
            seen.add(key)
            unique.append(p)
        return unique

    async def _apify_employees(self, job: Job, analysis: dict[str, Any]) -> list[Prospect]:
        if not self.settings.apify_api_token:
            logger.info("networking_apify_skipped", reason="no token")
            return []
        url = (
            f"https://api.apify.com/v2/acts/{self.settings.apify_linkedin_employees_actor_id}"
            "/run-sync-get-dataset-items"
        )
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    url,
                    params={"token": self.settings.apify_api_token},
                    json={"companyName": job.company, "maxItems": 40},
                )
                if response.status_code >= 400:
                    logger.warning("apify_employees_failed", status=response.status_code)
                    return []
                items = response.json()
        except Exception as exc:
            logger.warning("apify_employees_error", error=str(exc))
            return []
        if not isinstance(items, list):
            return []
        return [p for item in items if (p := self._map_employee(item, job, analysis))]

    async def _vibe_prospects(self, job: Job, analysis: dict[str, Any]) -> list[Prospect]:
        if not self.settings.vibe_prospecting_api_key:
            return []
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.settings.vibe_prospecting_base_url.rstrip('/')}/v1/search",
                    headers={"Authorization": f"Bearer {self.settings.vibe_prospecting_api_key}"},
                    json={
                        "company": job.company,
                        "titles": [
                            "Technical Recruiter",
                            "Engineering Manager",
                            "Software Engineer",
                        ],
                        "limit": 30,
                    },
                )
                if response.status_code >= 400:
                    return []
                payload = response.json()
        except Exception as exc:
            logger.warning("vibe_prospecting_error", error=str(exc))
            return []
        items = payload.get("results") or payload.get("people") or []
        return [p for item in items if (p := self._map_employee(item, job, analysis))]

    def _map_employee(
        self, item: dict[str, Any], job: Job, analysis: dict[str, Any]
    ) -> Prospect | None:
        name = item.get("fullName") or item.get("name") or ""
        title = item.get("title") or item.get("headline") or ""
        linkedin = item.get("linkedinUrl") or item.get("profileUrl") or item.get("url") or ""
        if not name or not linkedin:
            return None
        company_now = item.get("companyName") or item.get("currentCompany") or item.get("company")
        if not company_now:
            exp = item.get("experience")
            if isinstance(exp, list) and exp and isinstance(exp[0], dict):
                company_now = exp[0].get("company") or exp[0].get("companyName")

        current = self._verify_current_employment(company_now, job.company, item)
        if not current:
            return None

        persona = self._classify_persona(title, item)
        if persona is None:
            return None
        score = self._relevance_score(persona, title, item, job, analysis)
        notes = self._short_note(persona, title, item, job)
        email = item.get("email") or ""
        # Never invent emails — only keep if looks real
        if email and ("@" not in email or "example.com" in email):
            email = ""
        return Prospect(
            name=name,
            persona=persona,
            title=title,
            relevance_score=score,
            linkedin_url=linkedin.split("?")[0],
            email=email,
            notes=notes,
            evidence={
                "source": item.get("source") or "apify",
                "current_company": company_now,
                "location": item.get("location"),
            },
            currently_employed=True,
        )

    def _verify_current_employment(
        self, company_now: Any, target: str, item: dict[str, Any]
    ) -> bool:
        if not company_now:
            # Explicit current flag from scraper
            if item.get("isCurrent") is True or item.get("currentlyWorksHere") is True:
                return True
            return False
        a = re.sub(r"[^a-z0-9]", "", str(company_now).lower())
        b = re.sub(r"[^a-z0-9]", "", target.lower())
        if not a or not b:
            return False
        return a in b or b in a

    def _classify_persona(self, title: str, item: dict[str, Any]) -> str | None:
        blob = f"{title} {item.get('headline') or ''}"
        if EXTERNAL_RECRUITER_RE.search(blob):
            return None
        if RECRUITER_TITLE_RE.search(blob):
            return "Recruiter"
        if HM_TITLE_RE.search(blob):
            return "Hiring Manager"
        if PEER_TITLE_RE.search(blob):
            return "Peer"
        return None

    def _relevance_score(
        self,
        persona: str,
        title: str,
        item: dict[str, Any],
        job: Job,
        analysis: dict[str, Any],
    ) -> float:
        score = 6.0
        # Role relevance
        if persona == "Recruiter" and "technical" in title.lower():
            score += 1.5
        if persona == "Hiring Manager" and "engineering" in title.lower():
            score += 1.5
        if persona == "Peer" and any(
            t.lower() in title.lower() for t in (analysis.get("title") or "").split()[:3]
        ):
            score += 1.2
        # Location
        loc = (item.get("location") or "").lower()
        job_loc = (job.location or "").lower()
        if job_loc and loc and any(part in loc for part in job_loc.split(",") if len(part) > 2):
            score += 1.0
        # Technical overlap for peers
        if persona == "Peer":
            headline = (item.get("headline") or title).lower()
            hits = sum(1 for t in analysis.get("technologies") or [] if str(t).lower() in headline)
            score += min(1.5, hits * 0.5)
        # Hiring influence
        if persona == "Hiring Manager":
            score += 0.8
        if persona == "Recruiter":
            score += 0.6
        return round(min(10.0, max(0.0, score)), 1)

    def _short_note(
        self, persona: str, title: str, item: dict[str, Any], job: Job
    ) -> str:
        loc = item.get("location") or ""
        note = f"{persona}; {title}"
        if loc:
            note += f"; {loc}"
        return note[:99]

    def _prioritize(self, prospects: list[Prospect], analysis: dict[str, Any]) -> list[Prospect]:
        def key(p: Prospect) -> tuple:
            loc_bonus = 1 if (analysis.get("location") or "").lower()[:4] in (
                p.evidence.get("location") or ""
            ).lower() else 0
            return (-p.relevance_score, -loc_bonus)

        return sorted(prospects, key=key)

    def _outreach_priority(self, prospects: list[Prospect]) -> list[Prospect]:
        order = {"Hiring Manager": 0, "Recruiter": 1, "Peer": 2}
        return sorted(
            prospects,
            key=lambda p: (order.get(p.persona, 9), -p.relevance_score),
        )[:10]

    def _why_reach_out(self, p: Prospect, analysis: dict[str, Any]) -> str:
        if p.persona == "Hiring Manager":
            return "Likely owns hiring for this eng role"
        if p.persona == "Recruiter":
            return "Internal technical recruiting for this opening"
        return "Peer on similar stack/team — relationship first"

    async def _persist_prospects(
        self, user: User, job: Job, prospects: list[Prospect]
    ) -> list[Contact]:
        saved: list[Contact] = []
        type_map = {
            "Recruiter": ContactType.RECRUITER.value,
            "Hiring Manager": ContactType.HIRING_MANAGER.value,
            "Peer": ContactType.PEER.value,
        }
        for p in prospects:
            contact_type = type_map.get(p.persona, ContactType.OTHER.value)
            existing = (
                await self.db.execute(
                    select(Contact).where(
                        Contact.user_id == user.id,
                        Contact.job_id == job.id,
                        Contact.linkedin_url == p.linkedin_url,
                    )
                )
            ).scalar_one_or_none()
            if existing:
                existing.confidence_score = p.relevance_score / 10.0
                existing.title = p.title
                existing.contact_type = contact_type
                existing.why_selected = p.notes
                existing.evidence = [p.evidence]
                saved.append(existing)
                continue
            contact = Contact(
                user_id=user.id,
                job_id=job.id,
                name=p.name,
                title=p.title,
                company=job.company,
                linkedin_url=p.linkedin_url,
                email=p.email or None,
                source=str(p.evidence.get("source") or "networking"),
                confidence_score=p.relevance_score / 10.0,
                contact_type=contact_type,
                evidence=[p.evidence],
                why_selected=p.notes,
            )
            self.db.add(contact)
            saved.append(contact)
        await self.db.flush()
        return saved

    @staticmethod
    def _guess_company_from_url(url: str) -> str:
        m = re.search(r"linkedin\.com/company/([^/?#]+)", url, re.I)
        if m:
            return m.group(1).replace("-", " ").title()
        host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
        return host.split(".")[0].title() if host else "Unknown"
