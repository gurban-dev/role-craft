"""Remotive public job board API."""

from __future__ import annotations

import httpx

from app.core.logging import get_logger
from app.integrations.job_sources.base import DiscoveredJob, JobSearchCriteria

logger = get_logger(__name__)

REMOTIVE_API = "https://remotive.com/api/remote-jobs"


class RemotiveSource:
    name = "remotive"

    async def search(self, criteria: JobSearchCriteria) -> list[DiscoveredJob]:
        params: dict[str, str | int] = {"limit": criteria.limit}
        if criteria.query:
            params["search"] = criteria.query
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(REMOTIVE_API, params=params)
            response.raise_for_status()
            payload = response.json()
        jobs: list[DiscoveredJob] = []
        for item in payload.get("jobs", [])[: criteria.limit]:
            job_id = str(item.get("id") or item.get("url") or "")
            if not job_id:
                continue
            category = item.get("category") or ""
            tags = item.get("tags") or []
            jobs.append(
                DiscoveredJob(
                    title=item.get("title") or "Untitled",
                    company=item.get("company_name") or "Unknown",
                    external_job_id=job_id,
                    source=self.name,
                    description=item.get("description") or "",
                    location=item.get("candidate_required_location") or "Remote",
                    remote_status="remote",
                    source_url=item.get("url"),
                    official_application_url=item.get("url"),
                    technologies=list(tags) if isinstance(tags, list) else [],
                    requirements=[category] if category else [],
                    salary_currency="USD",
                    raw_payload=item if isinstance(item, dict) else {},
                )
            )
        logger.info("remotive_search", query=criteria.query, count=len(jobs))
        return jobs
