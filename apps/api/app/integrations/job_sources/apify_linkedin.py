"""Apify LinkedIn jobs discovery source."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote_plus

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.integrations.job_sources.base import DiscoveredJob, JobSearchCriteria
from app.services.eea_filters import detect_country_code, normalize_regions

logger = get_logger(__name__)

APIFY_RUN_SYNC = "https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items"

# curious_coder/linkedin-jobs-scraper ignores free-text filters when `urls` is set.
# f_TPR=r86400 is LinkedIn's "past 24 hours".


def linkedin_search_urls(
    query: str,
    regions: list[str] | None = None,
    posted_within_hours: int = 24,
) -> list[str]:
    """Search each selected region using LinkedIn's nearest supported date window."""
    keywords = quote_plus(query or "software engineer")
    if posted_within_hours <= 24:
        date_filter = "r86400"
    elif posted_within_hours > 168:
        date_filter = "r2592000"
    else:
        date_filter = "r604800"
    return [
        "https://www.linkedin.com/jobs/search/"
        f"?keywords={keywords}&location={quote_plus(region)}&f_TPR={date_filter}&sortBy=DD"
        for region in normalize_regions(regions)
    ]


def _parse_posted_at(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, int | float):
        # epoch ms or s
        ts = float(raw)
        if ts > 1e12:
            ts /= 1000.0
        return datetime.fromtimestamp(ts, tz=UTC)
    text = str(raw).strip()
    if not text:
        return None
    # Relative LinkedIn labels — only accept unambiguous <24h signals with clock
    lower = text.lower()
    now = datetime.now(UTC)
    if lower in {"just now", "today"}:
        # Spec: do not treat "today" as automatically <24h — exclude
        return None
    if "hour" in lower or "minute" in lower or "min" in lower:
        digits = "".join(c for c in lower if c.isdigit())
        hours = int(digits) if digits else 0
        if "minute" in lower or "min" in lower:
            return now - timedelta(minutes=max(hours, 1))
        return now - timedelta(hours=max(hours, 1))
    relative = re.fullmatch(r"(\d+)\s+(day|days|week|weeks|month|months)\s+ago", lower)
    if relative:
        count = int(relative.group(1))
        unit = relative.group(2)
        if unit.startswith("week"):
            age_days = count * 7
            upper_bound_days = 7
        elif unit.startswith("month"):
            age_days = count * 30
            upper_bound_days = 30
        else:
            age_days = count
            upper_bound_days = 1
        # Use the oldest bound of the relative label so the exact cutoff never
        # accepts a result that might be older than the requested window.
        return now - timedelta(days=age_days + upper_bound_days)
    try:
        # ISO
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError:
        return None


def _parse_applicants(raw: Any) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    text = str(raw).lower().replace(",", "").strip()
    digits = "".join(c for c in text if c.isdigit())
    if not digits:
        return None
    return int(digits)


def _normalize_location(raw: Any) -> str | None:
    if isinstance(raw, str):
        return raw.strip() or None
    if isinstance(raw, dict):
        preferred_keys = (
            "city", "state", "region", "country", "countryCode", "country_code",
            "displayName", "name", "location",
        )
        values = [raw[key] for key in preferred_keys if raw.get(key)]
        if not values:
            values = list(raw.values())
        return ", ".join(str(value).strip() for value in values if value) or None
    if isinstance(raw, list | tuple):
        return ", ".join(str(value).strip() for value in raw if value) or None
    return str(raw).strip() if raw else None


class ApifyLinkedInJobsSource:
    name = "linkedin_apify"

    async def search(self, criteria: JobSearchCriteria) -> list[DiscoveredJob]:
        settings = get_settings()
        if not settings.apify_api_token:
            logger.info("apify_linkedin_skipped", reason="APIFY_API_TOKEN unset")
            return []

        actor_input: dict[str, Any] = {
            "urls": linkedin_search_urls(
                criteria.query,
                criteria.extras.get("regions"),
                criteria.posted_within_hours or 24,
            ),
            "limitPerSource": min(max(criteria.limit, 10), 20),
            "scrapeCompany": False,
        }
        actor_input.update(criteria.extras.get("apify_input") or {})

        actor_id = settings.apify_linkedin_jobs_actor_id.replace("/", "~")
        url = APIFY_RUN_SYNC.format(actor_id=actor_id)
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {settings.apify_api_token}"},
                    json=actor_input,
                )
                if response.status_code >= 400:
                    logger.warning(
                        "apify_linkedin_failed",
                        status=response.status_code,
                        body=response.text[:500],
                    )
                    return []
                items = response.json()
        except Exception as exc:
            logger.warning("apify_linkedin_error", error=str(exc))
            return []

        if not isinstance(items, list):
            return []

        jobs: list[DiscoveredJob] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = item.get("title") or item.get("jobTitle") or ""
            company = item.get("companyName") or item.get("company") or "Unknown"
            job_url = (
                item.get("jobUrl")
                or item.get("url")
                or item.get("link")
                or item.get("jobLink")
            )
            job_id = str(
                item.get("jobId")
                or item.get("id")
                or item.get("urn")
                or job_url
                or f"{company}-{title}"
            )
            location = _normalize_location(item.get("location") or item.get("jobLocation"))
            description = (
                item.get("description")
                or item.get("descriptionText")
                or item.get("jobDescription")
                or ""
            )
            posted_at = _parse_posted_at(
                item.get("postedAt")
                or item.get("publishedAt")
                or item.get("listedAt")
                or item.get("postedTime")
                or item.get("postedDate")
            )
            applicants = _parse_applicants(
                item.get("applicants")
                or item.get("applicantCount")
                or item.get("numApplicants")
                or item.get("applicationsCount")
                or item.get("applicantsCount")
            )
            jobs.append(
                DiscoveredJob(
                    title=title or "Untitled",
                    company=company,
                    external_job_id=job_id,
                    source=self.name,
                    description=description,
                    location=location,
                    remote_status=item.get("workplaceType") or item.get("remoteStatus"),
                    source_url=job_url,
                    official_application_url=item.get("applyUrl")
                    or item.get("applyLink")
                    or item.get("companyApplyUrl")
                    or job_url,
                    posted_at=posted_at,
                    applicant_count=applicants,
                    country_code=detect_country_code(location),
                    employment_type=item.get("employmentType"),
                    seniority_label=(
                        item.get("seniorityLevel")
                        or item.get("seniority_label")
                        or item.get("experienceLevel")
                        or item.get("seniority")
                    ),
                    technologies=list(item.get("skills") or []),
                    raw_payload=item,
                )
            )
            if len(jobs) >= criteria.limit:
                break
        logger.info("apify_linkedin_search", count=len(jobs))
        return jobs
