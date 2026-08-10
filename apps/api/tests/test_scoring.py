"""Scoring service unit tests."""

from __future__ import annotations

from app.models import CandidateProfile, Job
from app.services.scoring_service import ScoringService


def _job(**kwargs) -> Job:
    defaults = {
        "title": "Senior Python Engineer",
        "company": "ExampleCo",
        "description": "Looking for 5 years python fastapi postgresql docker experience. Remote.",
        "technologies": ["python", "fastapi", "postgresql"],
        "requirements": ["python", "fastapi"],
        "remote_status": "remote",
        "location": "Remote",
        "source": "test",
        "external_job_id": "1",
    }
    defaults.update(kwargs)
    return Job(**defaults)


def _profile(**kwargs) -> CandidateProfile:
    defaults = {
        "user_id": None,  # not persisted
        "professional_summary": "Python FastAPI engineer",
        "skills": ["python", "fastapi", "postgresql", "redis"],
        "work_history": [{"company": "Acme", "title": "Engineer"}],
        "years_experience": 6.0,
        "seniority_level": "senior",
        "remote_preference": "remote",
        "preferred_locations": ["Remote"],
        "salary_min": 100000,
    }
    defaults.update(kwargs)
    # CandidateProfile requires user_id UUID — use a dummy for in-memory
    from uuid import uuid4

    if defaults.get("user_id") is None:
        defaults["user_id"] = uuid4()
    return CandidateProfile(**defaults)


def test_high_match_score() -> None:
    score = ScoringService().score(_job(), _profile())
    assert score.overall_score >= 0.65
    assert score.skill_match >= 0.5
    assert "python" in score.required_skills or score.skill_match > 0


def test_low_match_missing_skills() -> None:
    job = _job(
        title="Rust Systems Engineer",
        description="Need 8 years rust kubernetes experience",
        technologies=["rust", "kubernetes"],
        requirements=["rust"],
    )
    profile = _profile(skills=["python"], years_experience=2.0, seniority_level="junior")
    score = ScoringService().score(job, profile)
    assert score.overall_score < 0.65
    assert "rust" in score.missing_skills


def test_salary_and_location_components() -> None:
    job = _job(salary_max=90000, remote_status="onsite", location="New York")
    profile = _profile(
        salary_min=150000,
        remote_preference="remote",
        preferred_locations=["Seattle"],
    )
    score = ScoringService().score(job, profile)
    assert 0.0 <= score.salary_match <= 1.0
    assert 0.0 <= score.location_match <= 1.0
