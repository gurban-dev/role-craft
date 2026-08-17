"""Persona-aware LinkedIn outreach (<200 chars) with one specific personalization."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models import Contact, Job, User
from app.models.enums import ContactType

logger = get_logger(__name__)

PERSONA_LABEL = {
    ContactType.RECRUITER.value: "Recruiter",
    ContactType.HIRING_MANAGER.value: "Hiring Manager",
    ContactType.PEER.value: "Peer",
}


class LinkedInOutreachService:
    def __init__(self, db: AsyncSession, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    async def generate_for_contacts(
        self,
        user: User,
        contacts: list[Contact],
        job: Job,
        *,
        candidate_skills: list[str] | None = None,
    ) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        skills = candidate_skills or list(job.technologies or [])[:4]
        for idx, contact in enumerate(contacts, start=1):
            profile = await self._scrape_profile(contact.linkedin_url)
            detail = self._one_personalization(profile, contact)
            if not detail:
                logger.info(
                    "outreach_skip_no_personalization",
                    contact_id=str(contact.id),
                    name=contact.name,
                )
                continue
            persona = PERSONA_LABEL.get(contact.contact_type, "Peer")
            message = self._compose(persona, contact, job, detail, skills)
            if len(message) > 200:
                message = message[:197] + "…"
            rows.append(
                {
                    "rank": str(idx),
                    "name": contact.name,
                    "persona": persona,
                    "message": message,
                    "personalization": detail,
                }
            )
        return rows

    async def _scrape_profile(self, linkedin_url: str | None) -> dict[str, Any]:
        if not linkedin_url or not self.settings.apify_api_token:
            return {}
        url = (
            f"https://api.apify.com/v2/acts/{self.settings.apify_linkedin_profile_actor_id}"
            "/run-sync-get-dataset-items"
        )
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    url,
                    params={"token": self.settings.apify_api_token},
                    json={"profileUrls": [linkedin_url]},
                )
                if response.status_code >= 400:
                    return {}
                items = response.json()
        except Exception as exc:
            logger.warning("linkedin_profile_scrape_failed", error=str(exc))
            return {}
        if isinstance(items, list) and items:
            return items[0] if isinstance(items[0], dict) else {}
        return {}

    def _one_personalization(self, profile: dict[str, Any], contact: Contact) -> str | None:
        """Return one specific detail, or None if nothing strong enough."""
        # University
        education = profile.get("education") or profile.get("educations") or []
        if isinstance(education, list) and education:
            first = education[0] if isinstance(education[0], dict) else {}
            school = first.get("schoolName") or first.get("school") or first.get("name")
            if school:
                return f"studied at {school}"

        # Career move: previous company → current
        experience = profile.get("experience") or profile.get("experiences") or []
        if isinstance(experience, list) and len(experience) >= 2:
            cur = experience[0] if isinstance(experience[0], dict) else {}
            prev = experience[1] if isinstance(experience[1], dict) else {}
            prev_co = prev.get("companyName") or prev.get("company")
            cur_title = cur.get("title") or contact.title
            if prev_co and cur_title:
                return f"moved from {prev_co} into {cur_title}"

        # Distinctive specialty from headline (not generic)
        headline = (profile.get("headline") or contact.title or "").strip()
        banned = {"engineer", "software", "recruiter", "manager", "at"}
        tokens = [t for t in headline.replace("|", " ").split() if t.lower() not in banned]
        if len(tokens) >= 3 and len(headline) > 20:
            # Only if headline has a specialization beyond company name
            if contact.company and contact.company.lower() not in headline.lower():
                return f"focus on {headline[:80]}"
            # specialty keywords
            for needle in ("platform", "infra", "payments", "data", "mobile", "security", "ML"):
                if needle.lower() in headline.lower():
                    return f"work on {needle} systems"

        location = profile.get("location") or profile.get("geoLocation")
        if location and isinstance(location, str) and len(location) > 3:
            # Only when location is distinctive and not just "Remote"
            if "remote" not in location.lower():
                return f"based in {location.split(',')[0].strip()}"

        return None

    def _compose(
        self,
        persona: str,
        contact: Contact,
        job: Job,
        detail: str,
        skills: list[str],
    ) -> str:
        first = (contact.name or "").split()[0] or "there"
        skill_bits = [s for s in skills if s][:2]
        skill_text = " & ".join(str(s) for s in skill_bits) if skill_bits else "backend systems"
        reslink = self.settings.reslink_url or "[RESLINK URL]"

        if persona in {"Recruiter", "Hiring Manager"}:
            # Reference hiring; do NOT say applied; include reslink made for them
            return (
                f"Hi {first} — {detail}. Hiring for {job.title}? "
                f"I bring {skill_text}. Video made for you: {reslink}"
            )
        # Peer: no job, apply, referral, or pitch
        return f"Hi {first} — noticed you {detail}. Would enjoy swapping notes on similar work."
