"""Job source registry."""

from __future__ import annotations

from app.core.exceptions import NotFoundError
from app.integrations.job_sources.apify_linkedin import ApifyLinkedInJobsSource
from app.integrations.job_sources.arbeitnow import ArbeitnowSource
from app.integrations.job_sources.base import JobSource
from app.integrations.job_sources.chatgpt_google import ChatGPTGoogleJobsSource
from app.integrations.job_sources.google_jobs import GoogleJobsSource
from app.integrations.job_sources.greenhouse import GreenhouseSource
from app.integrations.job_sources.remotive import RemotiveSource

_SOURCES: dict[str, JobSource] = {
    RemotiveSource.name: RemotiveSource(),
    ArbeitnowSource.name: ArbeitnowSource(),
    GreenhouseSource.name: GreenhouseSource(),
    ApifyLinkedInJobsSource.name: ApifyLinkedInJobsSource(),
    GoogleJobsSource.name: GoogleJobsSource(),
    ChatGPTGoogleJobsSource.name: ChatGPTGoogleJobsSource(),
}

# Resume-focused job discovery uses LinkedIn listings only.
RESUME_MATCH_SOURCES = ["linkedin_apify"]
EEA_DISCOVERY_SOURCES = RESUME_MATCH_SOURCES


def list_job_sources() -> list[str]:
    return sorted(_SOURCES.keys())


def get_job_source(name: str) -> JobSource:
    source = _SOURCES.get(name.lower())
    if not source:
        raise NotFoundError(f"Unknown job source: {name}")
    return source
