"""Arbeitnow public job board API."""

from __future__ import annotations

import httpx

from app.core.logging import get_logger
from app.integrations.job_sources.base import DiscoveredJob, JobSearchCriteria

logger = get_logger(__name__)

ARBEITNOW_API = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowSource:
    name = "arbeitnow"

    async def search(self, criteria: JobSearchCriteria) -> list[DiscoveredJob]:
        params: dict[str, str | int] = {}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(ARBEITNOW_API, params=params)
            response.raise_for_status()
            payload = response.json()
        query_lower = (criteria.query or "").lower()
        jobs: list[DiscoveredJob] = []
        for item in payload.get("data", []):
            title = item.get("title") or ""
            if query_lower and query_lower not in title.lower() and query_lower not in (
                item.get("description") or ""
            ).lower():
                continue
            if criteria.remote_only and not item.get("remote"):
                continue
            if criteria.location:
                loc = (item.get("location") or "").lower()
                if criteria.location.lower() not in loc and not item.get("remote"):
                    continue
            slug = item.get("slug") or item.get("url") or title
            jobs.append(
                DiscoveredJob(
                    title=title or "Untitled",
                    company=item.get("company_name") or "Unknown",
                    external_job_id=str(slug),
                    source=self.name,
                    description=item.get("description") or "",
                    location=item.get("location"),
                    remote_status="remote" if item.get("remote") else "onsite",
                    source_url=item.get("url"),
                    official_application_url=item.get("url"),
                    technologies=list(item.get("tags") or []),
                    raw_payload=item if isinstance(item, dict) else {},
                )
            )
            if len(jobs) >= criteria.limit:
                break
        logger.info("arbeitnow_search", query=criteria.query, count=len(jobs))
        return jobs
