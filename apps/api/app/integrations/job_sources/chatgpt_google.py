"""Google job discovery via ChatGPT web search, posted in the last 24 hours."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.logging import get_logger
from app.integrations.job_sources.base import DiscoveredJob, JobSearchCriteria
from app.integrations.job_sources.google_jobs import GoogleJobsSource
from app.services.eea_filters import detect_country_code, normalize_regions

logger = get_logger(__name__)


class ChatGPTGoogleJobsSource:
    """Ask ChatGPT to search Google for jobs, then keep only rows with real fields."""

    name = "chatgpt_google"

    async def search(self, criteria: JobSearchCriteria) -> list[DiscoveredJob]:
        settings = get_settings()
        if not settings.open_router_token:
            logger.info("chatgpt_google_fallback", reason="OPEN_ROUTER_TOKEN unset")
            return await GoogleJobsSource().search(criteria)

        hours = criteria.posted_within_hours or settings.eea_posted_within_hours
        regions = normalize_regions(criteria.extras.get("regions"))
        region_text = ", ".join(regions)
        skills = criteria.extras.get("profile_skills") or []
        skill_hint = ", ".join(str(s) for s in skills[:8]) or "general software engineering"
        prompt = (
            "Search Google for software engineering jobs posted in the last "
            f"{hours} hours. Limit the search to these regions: {region_text}. "
            "Include both in-person and remote roles when the role is based in a selected region. "
            f"Prefer roles close to these skills: {skill_hint}. "
            "Exclude senior, staff, principal, lead, manager, and director titles. "
            "Exclude postings that say the company cannot provide a work permit or visa "
            "for the country where the role is based. "
            "Exclude roles that require a language other than English. "
            "Return ONLY a JSON array. Each object must use these keys: "
            "title, company, location, remote (true/false), posted_at (ISO-8601 UTC, "
            "only if the page shows a posting time in the window; otherwise omit the job), "
            "apply_url (company career site or ATS link, never LinkedIn/Indeed/Glassdoor), "
            "description (short excerpt of responsibilities and skills), "
            "applicant_count (integer only if the page states it, else null). "
            "Do not invent companies, links, dates, or applicant counts. "
            "If a required field is not on the page, omit that job. "
            f"Return at most {min(criteria.limit, 20)} jobs."
        )
        kwargs: dict[str, Any] = {"api_key": settings.open_router_token}
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        client = AsyncOpenAI(**kwargs, timeout=settings.llm_timeout_seconds)
        try:
            response = await client.responses.create(
                model=settings.openai_model,
                tools=[{"type": "openrouter:web_search"}],
                input=prompt,
            )
            text = _response_text(response)
        except Exception as exc:
            logger.warning("chatgpt_google_error", error=str(exc))
            return []

        rows = _extract_json_array(text)
        jobs: list[DiscoveredJob] = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            parsed = _to_discovered(item)
            if parsed is None:
                continue
            jobs.append(parsed)
            if len(jobs) >= criteria.limit:
                break
        logger.info("chatgpt_google_search", count=len(jobs), regions=regions)
        return jobs


def _response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    parts: list[str] = []
    for item in getattr(response, "output", None) or []:
        for block in getattr(item, "content", None) or []:
            text = getattr(block, "text", None)
            if text:
                parts.append(str(text))
    return "\n".join(parts)


def _extract_json_array(text: str) -> list[Any]:
    fence = re.search(r"```(?:json)?\s*(\[.*\])\s*```", text, re.DOTALL)
    raw = fence.group(1) if fence else None
    if raw is None:
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end <= start:
            return []
        raw = text[start : end + 1]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _to_discovered(item: dict[str, Any]) -> DiscoveredJob | None:
    title = str(item.get("title") or "").strip()
    company = str(item.get("company") or "").strip()
    apply_url = str(item.get("apply_url") or item.get("url") or "").strip()
    if not title or not company or not apply_url.startswith("http"):
        return None
    posted_at = _parse_posted(item.get("posted_at"))
    location = item.get("location")
    location_text = str(location).strip() if location else None
    remote = item.get("remote")
    remote_status = "remote" if remote is True else None
    description = str(item.get("description") or "")
    applicants = item.get("applicant_count")
    applicant_count = applicants if isinstance(applicants, int) else None
    return DiscoveredJob(
        title=title[:512],
        company=company[:255],
        external_job_id=apply_url[:500],
        source="chatgpt_google",
        description=description,
        location=location_text,
        remote_status=remote_status,
        source_url=apply_url,
        official_application_url=apply_url,
        posted_at=posted_at,
        applicant_count=applicant_count,
        country_code=detect_country_code(location_text, description),
        raw_payload=item,
    )


def _parse_posted(raw: Any) -> datetime | None:
    if not raw or not isinstance(raw, str):
        return None
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt
