"""Tests for EEA hard filters, dedupe, and fit scoring."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.integrations.job_sources.apify_linkedin import linkedin_search_urls
from app.integrations.job_sources.base import DiscoveredJob
from app.models import CandidateProfile, Job
from app.schemas import EEAJobSearchRequest
from app.services.eea_filters import (
    applicant_count_ok,
    classify_job_seniority,
    classify_work_arrangement,
    is_eea_location,
    is_europe_location,
    job_eligible_regions,
    matches_region_work_arrangements,
    posted_within_hours,
    title_looks_senior,
    visa_sponsorship_blocked,
)
from app.services.eea_pipeline import dedupe_discovered, validate_hard_requirements
from app.services.scoring_service import ScoringService


def test_linkedin_search_urls_follow_selected_regions() -> None:
    urls = linkedin_search_urls(
        "software engineer",
        ["Asia", "Africa"],
    )
    assert len(urls) == 2
    assert any("location=Asia" in url and "f_TPR=r86400" in url for url in urls)
    assert any("location=Africa" in url and "f_TPR=r86400" in url for url in urls)
    assert all("f_WT" not in url for url in urls)
    assert all("linkedin.com/jobs/search" in url for url in urls)


def test_eea_location_accepts_amsterdam() -> None:
    assert is_eea_location("Amsterdam, Netherlands")
    assert is_eea_location("Berlin, Germany")
    assert not is_eea_location("London, United Kingdom")
    assert not is_eea_location("San Francisco, USA")


def test_seniority_excludes_senior_titles() -> None:
    assert title_looks_senior("Senior Software Engineer")
    assert title_looks_senior("Staff Engineer")
    assert title_looks_senior("Engineering Manager")
    assert not title_looks_senior("Software Engineer")
    assert title_looks_senior(
        "Software Engineer",
        "You will manage a team of 8 engineers with direct reports",
    )


def test_seniority_classifier_requires_clear_evidence() -> None:
    def job(title: str, description: str = "", *, label: str | None = None) -> DiscoveredJob:
        return DiscoveredJob(
            title=title,
            company="Acme",
            external_job_id=title,
            source="test",
            description=description,
            seniority_label=label,
        )

    assert classify_job_seniority(job("Senior Software Engineer")) == "senior"
    assert classify_job_seniority(
        job("Software Engineer", "At least 8 years of experience.")
    ) == "senior"
    assert classify_job_seniority(job("Junior Software Engineer")) == "non_senior"
    assert classify_job_seniority(
        job("Software Engineer", "3 years of experience required.")
    ) == "non_senior"
    assert classify_job_seniority(
        job("Software Engineer", "5 years of experience required.")
    ) == "unknown"
    assert classify_job_seniority(job("Software Engineer")) == "unknown"
    assert classify_job_seniority(job("Senior Engineer", "Entry-level role.")) == "unknown"
    assert classify_job_seniority(job("Software Engineer", label="mid-senior")) == "senior"
    raw_seniority = job("Software Engineer")
    raw_seniority.raw_payload = {"experienceLevel": "Entry level"}
    assert classify_job_seniority(raw_seniority) == "non_senior"


def test_work_arrangement_and_geography_are_conservative_and_region_specific() -> None:
    remote = DiscoveredJob(
        title="Software Engineer",
        company="Acme",
        external_job_id="remote-eu",
        source="test",
        location="Remote",
        remote_status="remote",
        raw_payload={"eligibleCountries": ["DE", "NL"]},
    )
    assert classify_work_arrangement(remote) == "remote"
    assert job_eligible_regions(remote, "remote") == {"Europe"}
    assert matches_region_work_arrangements(
        remote,
        regions=["Europe", "Asia"],
        work_arrangements={"Europe": ["remote"], "Asia": ["in_person"]},
    ) == (True, "Europe", "remote")

    generic_remote = DiscoveredJob(
        title="Software Engineer",
        company="Acme",
        external_job_id="remote-generic",
        source="test",
        location="Remote",
        remote_status="remote",
    )
    assert job_eligible_regions(generic_remote, "remote") == set()
    assert matches_region_work_arrangements(
        generic_remote,
        regions=["Europe"],
        work_arrangements={"Europe": ["remote"]},
    ) == (False, None, "remote")

    hybrid_asia = DiscoveredJob(
        title="Software Engineer",
        company="Acme",
        external_job_id="hybrid-asia",
        source="test",
        location="Singapore",
        raw_payload={"workplaceType": "HYBRID"},
    )
    onsite_africa = DiscoveredJob(
        title="Software Engineer",
        company="Acme",
        external_job_id="onsite-africa",
        source="test",
        location="Cape Town, South Africa",
        raw_payload={"workplaceType": "On-site"},
    )
    assert matches_region_work_arrangements(
        hybrid_asia,
        regions=["Europe", "Asia"],
        work_arrangements={"Europe": ["hybrid"], "Asia": ["hybrid"]},
    ) == (True, "Asia", "hybrid")
    assert matches_region_work_arrangements(
        onsite_africa,
        regions=["Africa"],
        work_arrangements={"Africa": ["in_person"]},
    ) == (True, "Africa", "in_person")

    ambiguous = DiscoveredJob(
        title="Software Engineer",
        company="Acme",
        external_job_id="ambiguous",
        source="test",
        location="Berlin, Germany",
        description="Remote or on-site depending on preference.",
    )
    assert classify_work_arrangement(ambiguous) == "unknown"
    ambiguous.description = "The position can be remote or hybrid."
    assert classify_work_arrangement(ambiguous) == "unknown"


def test_search_schema_requires_a_work_arrangement_in_a_selected_region() -> None:
    valid = EEAJobSearchRequest(
        regions=["Europe", "North America", "Africa"],
        include_non_senior=True,
        include_senior=True,
        region_work_arrangements={
            "Europe": ["remote", "hybrid"],
            "North America": ["in_person"],
            "Africa": [],
        },
    )
    assert valid.regions == ["Europe", "North America", "Africa"]

    try:
        EEAJobSearchRequest(
            regions=["Europe"],
            region_work_arrangements={"Europe": []},
        )
    except ValueError as exc:
        assert "Select at least one work arrangement" in str(exc)
    else:
        raise AssertionError("request with no active region arrangement should be rejected")


def test_hard_filters_apply_seniority_and_region_arrangements_together() -> None:
    now = datetime.now(UTC)
    job = DiscoveredJob(
        title="Senior Software Engineer",
        company="Acme",
        external_job_id="senior-eu-remote",
        source="linkedin_apify",
        description="English is the working language. We sponsor visas. 8 years of experience.",
        location="Remote",
        remote_status="remote",
        source_url="https://www.linkedin.com/jobs/view/senior-eu-remote",
        official_application_url="https://careers.acme.example/jobs/senior-eu-remote",
        posted_at=now - timedelta(hours=2),
        applicant_count=45,
        raw_payload={"eligibleCountries": ["Germany", "Netherlands"]},
    )
    common = {
        "now": now,
        "hours": 24,
        "regions": ["Europe", "Asia"],
        "region_work_arrangements": {
            "Europe": ["remote"],
            "Asia": ["hybrid"],
        },
    }
    ok, evidence, meta = validate_hard_requirements(
        job, include_senior=True, include_non_senior=False, **common
    )
    assert ok, evidence.reasons_rejected
    assert meta["market"] == "Europe"
    assert meta["work_arrangement"] == "remote"

    ok, evidence, _ = validate_hard_requirements(
        job, include_senior=True, include_non_senior=True, **common
    )
    assert ok, evidence.reasons_rejected

    ok, evidence, _ = validate_hard_requirements(
        job, include_senior=False, include_non_senior=True, **common
    )
    assert not ok
    assert "seniority_filter_mismatch" in evidence.reasons_rejected

    ok, evidence, _ = validate_hard_requirements(
        job, include_senior=False, include_non_senior=False, **common
    )
    assert not ok
    assert "seniority_filter_mismatch" in evidence.reasons_rejected

    job.seniority_label = None
    job.title = "Software Engineer"
    job.description = "English is the working language. We sponsor visas."
    for selected in (
        {"include_senior": False, "include_non_senior": True},
        {"include_senior": True, "include_non_senior": False},
        {"include_senior": True, "include_non_senior": True},
        {"include_senior": False, "include_non_senior": False},
    ):
        ok, evidence, _ = validate_hard_requirements(job, **selected, **common)
        assert ok, evidence.reasons_rejected
        assert evidence.seniority == "unknown_included"

    job.title = "Junior Software Engineer"
    job.description = "English is the working language. We sponsor visas. 2 years of experience."
    job.location = "Berlin, Germany"
    job.remote_status = None
    job.raw_payload = {"workplaceType": "Hybrid"}
    common["region_work_arrangements"] = {"Europe": ["hybrid"], "Asia": ["remote"]}
    ok, evidence, meta = validate_hard_requirements(
        job, include_senior=False, include_non_senior=True, **common
    )
    assert ok, evidence.reasons_rejected
    assert meta["market"] == "Europe"
    assert meta["work_arrangement"] == "hybrid"

    ok, evidence, _ = validate_hard_requirements(
        job, include_senior=False, include_non_senior=False, **common
    )
    assert ok, evidence.reasons_rejected

    asia_remote = DiscoveredJob(
        title="Senior Software Engineer",
        company="Acme",
        external_job_id="asia-remote",
        source="test",
        location="Remote",
        remote_status="remote",
        raw_payload={"eligibleCountries": ["Japan"]},
    )
    africa_hybrid = DiscoveredJob(
        title="Junior Software Engineer",
        company="Acme",
        external_job_id="africa-hybrid",
        source="test",
        location="Nairobi, Kenya",
        raw_payload={"workplaceType": "Hybrid"},
    )
    selected = {
        "Asia": ["remote"],
        "Africa": ["hybrid"],
    }
    assert matches_region_work_arrangements(
        asia_remote,
        regions=["Asia", "Africa"],
        work_arrangements=selected,
    ) == (True, "Asia", "remote")
    assert matches_region_work_arrangements(
        africa_hybrid,
        regions=["Asia", "Africa"],
        work_arrangements=selected,
    ) == (True, "Africa", "hybrid")


def test_visa_block_patterns() -> None:
    assert visa_sponsorship_blocked("We cannot sponsor visas for this role.")
    assert visa_sponsorship_blocked("Candidates must already have work authorization.")
    assert visa_sponsorship_blocked(
        "The company is unable to provide a work permit for the Netherlands."
    )
    assert not visa_sponsorship_blocked("We offer relocation support and visa sponsorship.")
    assert not visa_sponsorship_blocked("Join our Amsterdam engineering team.")


def test_europe_includes_uk_and_eea_stays_narrow() -> None:
    assert is_europe_location("London, United Kingdom")
    assert is_europe_location("Zurich, Switzerland")
    assert not is_eea_location("London, United Kingdom")
    assert not is_europe_location("San Francisco, USA")


def test_applicant_count_linkedin_hard() -> None:
    assert applicant_count_ok(99, linkedin_source=True)
    assert not applicant_count_ok(100, linkedin_source=True)
    assert not applicant_count_ok(None, linkedin_source=True)
    assert not applicant_count_ok(None, linkedin_source=False)
    assert not applicant_count_ok(100, linkedin_source=False)
    assert applicant_count_ok(12, linkedin_source=False)


def test_recency_requires_timestamp() -> None:
    now = datetime.now(UTC)
    assert posted_within_hours(now - timedelta(hours=12), hours=24, now=now)
    assert not posted_within_hours(now - timedelta(hours=25), hours=24, now=now)
    assert not posted_within_hours(None, hours=24, now=now)


def test_validate_hard_requirements_happy_path() -> None:
    now = datetime.now(UTC)
    job = DiscoveredJob(
        title="Software Engineer",
        company="Acme",
        external_job_id="1",
        source="arbeitnow",
        description="English required. Python and FastAPI. We sponsor visas.",
        location="Amsterdam, Netherlands",
        source_url="https://example.com/jobs/1",
        official_application_url="https://boards.greenhouse.io/acme/jobs/1",
        posted_at=now - timedelta(hours=3),
        applicant_count=20,
    )
    ok, evidence, meta = validate_hard_requirements(job, now=now, hours=24)
    assert ok, evidence.reasons_rejected
    assert meta["country_code"] == "nl"


def test_validate_accepts_london_and_us_remote() -> None:
    now = datetime.now(UTC)
    london = DiscoveredJob(
        title="Software Engineer",
        company="Acme",
        external_job_id="uk-1",
        source="chatgpt_google",
        description="English is the working language. Python and React.",
        location="London, United Kingdom",
        source_url="https://careers.acme.example/jobs/uk-1",
        official_application_url="https://careers.acme.example/jobs/uk-1",
        posted_at=now - timedelta(hours=4),
        applicant_count=20,
    )
    ok, evidence, meta = validate_hard_requirements(
        london, now=now, hours=24, regions=["Europe"]
    )
    assert ok, evidence.reasons_rejected
    assert meta["market"] == "Europe"

    us_remote = DiscoveredJob(
        title="Software Engineer",
        company="Northwind",
        external_job_id="us-1",
        source="linkedin_apify",
        description="Fully remote. English only. TypeScript.",
        location="United States",
        remote_status="remote",
        source_url="https://www.linkedin.com/jobs/view/us-1",
        official_application_url="https://jobs.lever.co/northwind/us-1",
        posted_at=now - timedelta(hours=1),
        applicant_count=40,
    )
    ok, evidence, meta = validate_hard_requirements(
        us_remote, now=now, hours=24, regions=["North America"]
    )
    assert ok, evidence.reasons_rejected
    assert meta["market"] == "North America"


def test_validate_rejects_us_onsite_extra_language_and_aggregator_link() -> None:
    now = datetime.now(UTC)
    onsite = DiscoveredJob(
        title="Software Engineer",
        company="Office",
        external_job_id="us-2",
        source="chatgpt_google",
        description="On-site in San Francisco. English.",
        location="San Francisco, USA",
        source_url="https://careers.office.example/jobs/2",
        official_application_url="https://careers.office.example/jobs/2",
        posted_at=now - timedelta(hours=1),
    )
    ok, evidence, _ = validate_hard_requirements(onsite, now=now, hours=24, regions=["Europe"])
    assert not ok
    assert "location_not_in_scope" in evidence.reasons_rejected

    singapore = DiscoveredJob(
        title="Software Engineer",
        company="Harbor",
        external_job_id="sg-1",
        source="chatgpt_google",
        description="English only. On-site in Singapore.",
        location="Singapore",
        source_url="https://careers.harbor.example/jobs/sg-1",
        official_application_url="https://careers.harbor.example/jobs/sg-1",
        posted_at=now - timedelta(hours=2),
        applicant_count=20,
    )
    ok, evidence, meta = validate_hard_requirements(
        singapore, now=now, hours=24, regions=["Asia"]
    )
    assert ok, evidence.reasons_rejected
    assert meta["market"] == "Asia"

    dutch = DiscoveredJob(
        title="Software Engineer",
        company="Acme",
        external_job_id="nl-2",
        source="arbeitnow",
        description="English required. Dutch language required.",
        location="Amsterdam, Netherlands",
        source_url="https://careers.acme.example/jobs/nl-2",
        official_application_url="https://careers.acme.example/jobs/nl-2",
        posted_at=now - timedelta(hours=1),
    )
    ok, evidence, _ = validate_hard_requirements(dutch, now=now, hours=24)
    assert not ok
    assert "english_not_ok" in evidence.reasons_rejected

    linkedin_only = DiscoveredJob(
        title="Software Engineer",
        company="Acme",
        external_job_id="li-only",
        source="linkedin_apify",
        description="English. Python.",
        location="Berlin, Germany",
        source_url="https://www.linkedin.com/jobs/view/li-only",
        official_application_url="https://www.linkedin.com/jobs/view/li-only",
        posted_at=now - timedelta(hours=1),
        applicant_count=10,
    )
    ok, evidence, _ = validate_hard_requirements(linkedin_only, now=now, hours=24)
    assert not ok
    assert "no_company_website_apply_link" in evidence.reasons_rejected


def test_validate_rejects_linkedin_without_applicants() -> None:
    now = datetime.now(UTC)
    job = DiscoveredJob(
        title="Software Engineer",
        company="Acme",
        external_job_id="99",
        source="linkedin_apify",
        description="English. Python.",
        location="Berlin, Germany",
        source_url="https://linkedin.com/jobs/view/99",
        posted_at=now - timedelta(hours=2),
        applicant_count=None,
    )
    ok, evidence, _ = validate_hard_requirements(job, now=now, hours=24)
    assert not ok
    assert "applicant_count_fail" in evidence.reasons_rejected


def test_dedupe_by_apply_url() -> None:
    now = datetime.now(UTC)
    a = DiscoveredJob(
        title="Software Engineer",
        company="Acme",
        external_job_id="li-1",
        source="linkedin_apify",
        location="Amsterdam",
        official_application_url="https://boards.greenhouse.io/acme/jobs/1",
        source_url="https://linkedin.com/jobs/view/1",
        posted_at=now,
        applicant_count=12,
    )
    b = DiscoveredJob(
        title="Software Engineer",
        company="Acme",
        external_job_id="gh-1",
        source="google_jobs",
        location="Amsterdam",
        official_application_url="https://boards.greenhouse.io/acme/jobs/1",
        source_url="https://boards.greenhouse.io/acme/jobs/1",
        posted_at=now,
    )
    merged = dedupe_discovered([a, b])
    assert len(merged) == 1
    assert merged[0].applicant_count == 12


def test_fit_score_10_strict() -> None:
    profile = CandidateProfile(
        id=uuid4(),
        user_id=uuid4(),
        skills=["python", "fastapi", "postgresql", "docker"],
        years_experience=3.0,
        seniority_level="mid",
        preferred_locations=["Amsterdam"],
        remote_preference="hybrid",
    )
    strong = Job(
        id=uuid4(),
        title="Software Engineer",
        company="Acme",
        location="Amsterdam, Netherlands",
        description="Python FastAPI PostgreSQL Docker. 3 years experience.",
        technologies=["python", "fastapi", "postgresql", "docker"],
        requirements=["python", "fastapi"],
        source="test",
        external_job_id="s1",
    )
    weak = Job(
        id=uuid4(),
        title="Software Engineer",
        company="Other",
        location="Amsterdam, Netherlands",
        description="Need Rust, Kotlin, and 10 years of JVM experience.",
        technologies=["rust", "kotlin", "jvm"],
        requirements=["rust", "kotlin", "jvm"],
        source="test",
        external_job_id="w1",
    )
    scoring = ScoringService()
    strong_score = scoring.score(strong, profile)
    weak_score = scoring.score(weak, profile)
    assert strong_score.fit_score_10 >= 7.0
    assert weak_score.fit_score_10 < 7.0
