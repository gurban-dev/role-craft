"""Apify LinkedIn jobs discovery source."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.integrations.job_sources.base import DiscoveredJob, JobSearchCriteria
from app.services.eea_filters import detect_country_code

logger = get_logger(__name__)

APIFY_RUN_SYNC = "https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items"


def _parse_posted_at(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
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


class ApifyLinkedInJobsSource:
    name = "linkedin_apify"

    async def search(self, criteria: JobSearchCriteria) -> list[DiscoveredJob]:
        settings = get_settings()
        if not settings.apify_api_token:
            logger.info("apify_linkedin_skipped", reason="APIFY_API_TOKEN unset")
            return []

        locations = []
        if criteria.location:
            locations.append(criteria.location)
        elif criteria.eea_only:
            locations = [
                "Netherlands",
                "Germany",
                "Ireland",
                "France",
                "Belgium",
                "Spain",
                "Portugal",
                "Poland",
                "Sweden",
                "Denmark",
            ]
        else:
            locations = ["European Union"]

        actor_input: dict[str, Any] = {
            "queries": [criteria.query],
            "locations": locations,
            "maxResults": min(criteria.limit * 3, 100),
            "postedWithinHours": criteria.posted_within_hours
            or settings.eea_posted_within_hours,
        }
        actor_input.update(criteria.extras.get("apify_input") or {})

        url = APIFY_RUN_SYNC.format(actor_id=settings.apify_linkedin_jobs_actor_id)
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    url,
                    params={"token": settings.apify_api_token},
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
            job_url = item.get("jobUrl") or item.get("url") or item.get("link")
            job_id = str(
                item.get("jobId")
                or item.get("id")
                or item.get("urn")
                or job_url
                or f"{company}-{title}"
            )
            location = item.get("location") or item.get("jobLocation")
            description = item.get("description") or item.get("jobDescription") or ""
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
                    official_application_url=item.get("applyUrl") or job_url,
                    posted_at=posted_at,
                    applicant_count=applicants,
                    country_code=detect_country_code(location, description),
                    employment_type=item.get("employmentType"),
                    seniority_label=item.get("seniorityLevel") or item.get("experienceLevel"),
                    technologies=list(item.get("skills") or []),
                    raw_payload=item,
                )
            )
            if len(jobs) >= criteria.limit:
                break
        logger.info("apify_linkedin_search", count=len(jobs))
        return jobs
