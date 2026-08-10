"""Job source protocol and shared dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol


@dataclass
class JobSearchCriteria:
    query: str = "software engineer"
    location: str | None = None
    remote_only: bool = False
    limit: int = 25
    company_board_token: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveredJob:
    title: str
    company: str
    external_job_id: str
    source: str
    description: str = ""
    location: str | None = None
    remote_status: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    source_url: str | None = None
    official_application_url: str | None = None
    requirements: list[Any] = field(default_factory=list)
    responsibilities: list[Any] = field(default_factory=list)
    technologies: list[Any] = field(default_factory=list)
    closing_date: date | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


class JobSource(Protocol):
    name: str

    async def search(self, criteria: JobSearchCriteria) -> list[DiscoveredJob]:
        """Search the source and return discovered jobs."""
        ...
