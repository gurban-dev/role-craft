"""Greenhouse public board jobs API."""

from __future__ import annotations

import httpx

from app.core.logging import get_logger
from app.integrations.job_sources.base import DiscoveredJob, JobSearchCriteria

logger = get_logger(__name__)

GREENHOUSE_BOARDS = "https://boards-api.greenhouse.io/v1/boards"


# Well-known demo boards when no token provided
DEFAULT_BOARDS = ("airbnb", "stripe", "gitlab")


class GreenhouseSource:
    name = "greenhouse"

    async def search(self, criteria: JobSearchCriteria) -> list[DiscoveredJob]:
        boards = []
        if criteria.company_board_token:
            boards = [criteria.company_board_token]
        elif criteria.extras.get("boards"):
            boards = list(criteria.extras["boards"])
        else:
            boards = list(DEFAULT_BOARDS)

        query_lower = (criteria.query or "").lower()
        jobs: list[DiscoveredJob] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for board in boards:
                try:
                    url = f"{GREENHOUSE_BOARDS}/{board}/jobs"
                    response = await client.get(url, params={"content": "true"})
                    response.raise_for_status()
                    payload = response.json()
                except httpx.HTTPError as exc:
                    logger.warning("greenhouse_board_failed", board=board, error=str(exc))
                    continue
                for item in payload.get("jobs", []):
                    title = item.get("title") or ""
                    if query_lower and query_lower not in title.lower():
                        # Also check content
                        content = (item.get("content") or "").lower()
                        if query_lower not in content:
                            continue
                    job_id = str(item.get("id") or "")
                    if not job_id:
                        continue
                    location = None
                    if isinstance(item.get("location"), dict):
                        location = item["location"].get("name")
                    elif item.get("location"):
                        location = str(item["location"])
                    abs_url = item.get("absolute_url")
                    jobs.append(
                        DiscoveredJob(
                            title=title or "Untitled",
                            company=board.replace("-", " ").title(),
                            external_job_id=f"{board}:{job_id}",
                            source=self.name,
                            description=item.get("content") or "",
                            location=location,
                            remote_status=(
                                "remote"
                                if location and "remote" in location.lower()
                                else None
                            ),
                            source_url=abs_url,
                            official_application_url=abs_url,
                            raw_payload=item if isinstance(item, dict) else {},
                        )
                    )
                    if len(jobs) >= criteria.limit:
                        logger.info("greenhouse_search", query=criteria.query, count=len(jobs))
                        return jobs
        logger.info("greenhouse_search", query=criteria.query, count=len(jobs))
        return jobs
