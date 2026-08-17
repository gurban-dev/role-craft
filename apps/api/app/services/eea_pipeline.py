"""Hard-filter validation and ranking for EEA job discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.integrations.job_sources.base import DiscoveredJob
from app.services.eea_filters import (
    applicant_count_ok,
    classify_visa_sponsorship,
    detect_country_code,
    english_required_or_implied,
    is_eea_location,
    posted_within_hours,
    title_looks_preferred_engineering,
    title_looks_senior,
)


@dataclass
class FilterEvidence:
    source_url: str | None = None
    source_type: str = ""
    date_collected: datetime | None = None
    posting_date: str = ""
    applicant_count: str = ""
    location: str = ""
    work_authorization: str = ""
    english: str = ""
    seniority: str = ""
    reasons_rejected: list[str] = field(default_factory=list)


@dataclass
class QualifiedJob:
    job: DiscoveredJob
    fit_score_10: float
    evidence: FilterEvidence
    country_code: str | None
    visa_sponsorship: str


def _is_linkedin(source: str) -> bool:
    return "linkedin" in (source or "").lower()


def validate_hard_requirements(
    item: DiscoveredJob,
    *,
    now: datetime | None = None,
    hours: int = 24,
) -> tuple[bool, FilterEvidence, dict[str, Any]]:
    """Return (ok, evidence, enriched metadata). Never invent missing hard facts."""
    now = now or datetime.now(UTC)
    evidence = FilterEvidence(
        source_url=item.source_url or item.official_application_url,
        source_type=item.source,
        date_collected=now,
    )
    meta: dict[str, Any] = {}

    country = item.country_code or detect_country_code(item.location, item.description)
    meta["country_code"] = country
    if not is_eea_location(item.location, item.description) and not (
        country and country in {
            "at", "be", "bg", "hr", "cy", "cz", "dk", "ee", "fi", "fr", "de", "gr",
            "hu", "is", "ie", "it", "lv", "li", "lt", "lu", "mt", "nl", "no", "pl",
            "pt", "ro", "sk", "si", "es", "se",
        }
    ):
        evidence.reasons_rejected.append("not_eea_location")
        evidence.location = f"rejected:{item.location}"
    else:
        evidence.location = f"eea:{country}:{item.location}"

    if not english_required_or_implied(item.description, item.title):
        evidence.reasons_rejected.append("english_not_ok")
        evidence.english = "rejected"
    else:
        evidence.english = "ok_or_implied"

    if title_looks_senior(item.title, item.description):
        evidence.reasons_rejected.append("seniority_too_high")
        evidence.seniority = "senior_or_lead"
    elif not title_looks_preferred_engineering(item.title) and not any(
        k in item.title.lower() for k in ("engineer", "developer", "software")
    ):
        evidence.reasons_rejected.append("not_software_engineering")
        evidence.seniority = "non_eng"
    else:
        evidence.seniority = "ok"

    visa = classify_visa_sponsorship(item.description)
    meta["visa_sponsorship"] = visa
    evidence.work_authorization = visa
    if visa == "blocked":
        evidence.reasons_rejected.append("visa_sponsorship_blocked")

    linkedin = _is_linkedin(item.source)
    if not posted_within_hours(item.posted_at, hours=hours, now=now):
        evidence.reasons_rejected.append("recency_unverified_or_stale")
        evidence.posting_date = (
            f"unavailable_or_stale:{item.posted_at.isoformat() if item.posted_at else None}"
        )
    else:
        evidence.posting_date = item.posted_at.isoformat() if item.posted_at else "unavailable"

    if not applicant_count_ok(item.applicant_count, linkedin_source=linkedin):
        evidence.reasons_rejected.append("applicant_count_fail")
        evidence.applicant_count = (
            f"unavailable_or_too_high:{item.applicant_count}"
            if linkedin
            else f"n/a_non_linkedin:{item.applicant_count}"
        )
    else:
        evidence.applicant_count = (
            str(item.applicant_count) if item.applicant_count is not None else "n/a_non_linkedin"
        )

    apply_url = item.official_application_url or item.source_url
    if not apply_url:
        evidence.reasons_rejected.append("no_application_path")

    ok = len(evidence.reasons_rejected) == 0
    return ok, evidence, meta


def dedupe_discovered(jobs: list[DiscoveredJob]) -> list[DiscoveredJob]:
    """Prefer canonical apply URL, then LinkedIn id, then company+title+location."""
    by_url: dict[str, DiscoveredJob] = {}
    by_linkedin: dict[str, DiscoveredJob] = {}
    by_key: dict[str, DiscoveredJob] = {}
    ordered: list[DiscoveredJob] = []

    def _canonical(j: DiscoveredJob) -> str | None:
        url = (j.official_application_url or j.source_url or "").strip().lower().rstrip("/")
        return url or None

    def _li_id(j: DiscoveredJob) -> str | None:
        if "linkedin" in j.source.lower() or "linkedin.com" in (j.source_url or "").lower():
            return j.external_job_id
        return None

    def _soft_key(j: DiscoveredJob) -> str:
        return "|".join(
            [
                (j.company or "").strip().lower(),
                (j.title or "").strip().lower(),
                (j.location or "").strip().lower(),
            ]
        )

    for job in jobs:
        url = _canonical(job)
        li = _li_id(job)
        soft = _soft_key(job)
        existing = None
        if url and url in by_url:
            existing = by_url[url]
        elif li and li in by_linkedin:
            existing = by_linkedin[li]
        elif soft in by_key:
            existing = by_key[soft]

        if existing is None:
            ordered.append(job)
            if url:
                by_url[url] = job
            if li:
                by_linkedin[li] = job
            by_key[soft] = job
            continue

        # Prefer LinkedIn for applicant counts; prefer newer posted_at
        merged = _merge_prefer_authoritative(existing, job)
        idx = ordered.index(existing)
        ordered[idx] = merged
        if url:
            by_url[url] = merged
        if li:
            by_linkedin[li] = merged
        by_key[soft] = merged

    return ordered


def _merge_prefer_authoritative(a: DiscoveredJob, b: DiscoveredJob) -> DiscoveredJob:
    """Keep most authoritative/recent fields across duplicate sources."""
    primary, secondary = a, b
    if _is_linkedin(b.source) and not _is_linkedin(a.source):
        primary, secondary = b, a
    elif a.posted_at and b.posted_at and b.posted_at > a.posted_at:
        primary, secondary = b, a

    def pick(attr: str) -> Any:
        pv = getattr(primary, attr)
        sv = getattr(secondary, attr)
        return pv if pv not in (None, "", [], {}) else sv

    return DiscoveredJob(
        title=pick("title"),
        company=pick("company"),
        external_job_id=primary.external_job_id or secondary.external_job_id,
        source=primary.source,
        description=pick("description") or "",
        location=pick("location"),
        remote_status=pick("remote_status"),
        salary_min=pick("salary_min"),
        salary_max=pick("salary_max"),
        salary_currency=pick("salary_currency"),
        source_url=pick("source_url"),
        official_application_url=pick("official_application_url"),
        requirements=pick("requirements") or [],
        responsibilities=pick("responsibilities") or [],
        technologies=pick("technologies") or [],
        closing_date=pick("closing_date"),
        posted_at=pick("posted_at"),
        applicant_count=pick("applicant_count"),
        country_code=pick("country_code"),
        employment_type=pick("employment_type"),
        seniority_label=pick("seniority_label"),
        raw_payload={**(secondary.raw_payload or {}), **(primary.raw_payload or {})},
    )


def rank_qualified(jobs: list[QualifiedJob], *, limit: int = 10) -> list[QualifiedJob]:
    """Recency first, then fit score, then lowest applicants, then soft match strength."""

    def sort_key(q: QualifiedJob) -> tuple:
        posted = q.job.posted_at or datetime.min.replace(tzinfo=UTC)
        applicants = q.job.applicant_count if q.job.applicant_count is not None else 10**9
        return (-posted.timestamp(), -q.fit_score_10, applicants)

    return sorted(jobs, key=sort_key)[:limit]
