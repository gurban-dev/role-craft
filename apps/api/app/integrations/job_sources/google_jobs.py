"""Google / public web job discovery (CSE when configured)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote_plus

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.integrations.job_sources.base import DiscoveredJob, JobSearchCriteria
from app.services.eea_filters import detect_country_code

logger = get_logger(__name__)

# ATS / career domains commonly hosting direct apply links
PREFERRED_DOMAINS = (
    "boards.greenhouse.io",
    "jobs.lever.co",
    "jobs.ashbyhq.com",
    "apply.workable.com",
    "jobs.smartrecruiters.com",
    "careers.",
)


class GoogleJobsSource:
    name = "google_jobs"

    async def search(self, criteria: JobSearchCriteria) -> list[DiscoveredJob]:
        settings = get_settings()
        if not settings.google_jobs_cse_api_key or not settings.google_jobs_cse_cx:
            logger.info("google_jobs_skipped", reason="CSE API key/cx unset")
            return []

        hours = criteria.posted_within_hours or settings.eea_posted_within_hours
        location_hint = criteria.location or "EEA OR Netherlands OR Germany OR Ireland OR France"
        query = (
            f'{criteria.query} ({location_hint}) '
            f'(software engineer OR developer) after:{_date_restrict(hours)}'
        )
        params = {
            "key": settings.google_jobs_cse_api_key,
            "cx": settings.google_jobs_cse_cx,
            "q": query,
            "num": min(criteria.limit, 10),
            "dateRestrict": f"d{max(1, hours // 24)}" if hours >= 24 else "d1",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://www.googleapis.com/customsearch/v1", params=params
                )
                if response.status_code >= 400:
                    logger.warning(
                        "google_jobs_failed",
                        status=response.status_code,
                        body=response.text[:400],
                    )
                    return []
                payload = response.json()
        except Exception as exc:
            logger.warning("google_jobs_error", error=str(exc))
            return []

        jobs: list[DiscoveredJob] = []
        now = datetime.now(UTC)
        for item in payload.get("items") or []:
            if not isinstance(item, dict):
                continue
            link = item.get("link") or ""
            title = item.get("title") or "Untitled"
            snippet = item.get("snippet") or ""
            company = _guess_company(item)
            # Only trust CSE dateRestrict — still require posted_at evidence.
            # Use metadata pagemap if present; otherwise leave None (hard filter excludes).
            posted_at = _extract_posted(item)
            if posted_at is None and hours <= 24:
                # Spec: if recency cannot be established, exclude — leave None
                posted_at = None
            jobs.append(
                DiscoveredJob(
                    title=_clean_title(title),
                    company=company,
                    external_job_id=link or quote_plus(title)[:200],
                    source=self.name,
                    description=snippet,
                    location=criteria.location,
                    source_url=link,
                    official_application_url=link if _looks_apply_url(link) else link,
                    posted_at=posted_at,
                    applicant_count=None,
                    country_code=detect_country_code(criteria.location, snippet),
                    raw_payload=item,
                )
            )
            if len(jobs) >= criteria.limit:
                break
        logger.info("google_jobs_search", count=len(jobs), as_of=now.isoformat())
        return jobs


def _date_restrict(hours: int) -> str:
    day = (datetime.now(UTC) - timedelta(hours=hours)).date()
    return day.isoformat()


def _clean_title(title: str) -> str:
    return title.split("|")[0].split(" - ")[0].strip()[:512]


def _guess_company(item: dict[str, Any]) -> str:
    pagemap = item.get("pagemap") or {}
    for key in ("metatags", "jobposting", "organization"):
        entries = pagemap.get(key) or []
        if not entries:
            continue
        first = entries[0] if isinstance(entries, list) else entries
        if isinstance(first, dict):
            for field in ("og:site_name", "hiringOrganization", "name", "company"):
                if first.get(field):
                    return str(first[field])[:255]
    display = item.get("displayLink") or "Unknown"
    return str(display).replace("www.", "").split(".")[0].title()


def _extract_posted(item: dict[str, Any]) -> datetime | None:
    pagemap = item.get("pagemap") or {}
    for key in ("jobposting", "metatags"):
        entries = pagemap.get(key) or []
        if not entries:
            continue
        first = entries[0] if isinstance(entries, list) else entries
        if not isinstance(first, dict):
            continue
        for field in ("dateposted", "datePublished", "og:updated_time", "article:published_time"):
            raw = first.get(field)
            if not raw:
                continue
            try:
                text = str(raw)
                if text.endswith("Z"):
                    text = text[:-1] + "+00:00"
                dt = datetime.fromisoformat(text)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                return dt
            except ValueError:
                continue
    return None


def _looks_apply_url(url: str) -> bool:
    lower = url.lower()
    return any(d in lower for d in PREFERRED_DOMAINS)
