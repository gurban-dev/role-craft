"""Job source registry."""

from __future__ import annotations

from app.core.exceptions import NotFoundError
from app.integrations.job_sources.arbeitnow import ArbeitnowSource
from app.integrations.job_sources.base import JobSource
from app.integrations.job_sources.greenhouse import GreenhouseSource
from app.integrations.job_sources.remotive import RemotiveSource

_SOURCES: dict[str, JobSource] = {
    RemotiveSource.name: RemotiveSource(),
    ArbeitnowSource.name: ArbeitnowSource(),
    GreenhouseSource.name: GreenhouseSource(),
}


def list_job_sources() -> list[str]:
    return sorted(_SOURCES.keys())


def get_job_source(name: str) -> JobSource:
    source = _SOURCES.get(name.lower())
    if not source:
        raise NotFoundError(f"Unknown job source: {name}")
    return source
