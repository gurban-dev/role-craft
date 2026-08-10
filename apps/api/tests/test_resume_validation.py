"""Resume validation tests."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.exceptions import ValidationAppError
from app.integrations.llm.schemas import ResumeChanges
from app.models import CandidateProfile
from app.services.resume_service import ResumeService


def _profile() -> CandidateProfile:
    return CandidateProfile(
        user_id=uuid4(),
        professional_summary="Python engineer",
        skills=["python", "fastapi", "postgresql"],
        work_history=[{"company": "Acme", "title": "Engineer"}],
        projects=[{"name": "API Gateway"}],
        quantified_accomplishments=["Cut latency 40%"],
    )


def test_validate_truthful_ok() -> None:
    svc = ResumeService.__new__(ResumeService)
    changes = ResumeChanges(
        summary="Python engineer",
        highlighted_skills=["python", "fastapi"],
        invented_claims=[],
    )
    svc.validate_truthful(_profile(), changes)


def test_validate_rejects_invented_claims() -> None:
    svc = ResumeService.__new__(ResumeService)
    changes = ResumeChanges(
        summary="x",
        highlighted_skills=["python"],
        invented_claims=["Won Nobel Prize"],
    )
    with pytest.raises(ValidationAppError):
        svc.validate_truthful(_profile(), changes)


def test_validate_rejects_unknown_skill() -> None:
    svc = ResumeService.__new__(ResumeService)
    changes = ResumeChanges(
        summary="x",
        highlighted_skills=["quantum-computing-xyz"],
        invented_claims=[],
    )
    with pytest.raises(ValidationAppError):
        svc.validate_truthful(_profile(), changes)


def test_score_quality_increases_with_content() -> None:
    from app.models import Job

    svc = ResumeService.__new__(ResumeService)
    job = Job(
        title="Python Engineer",
        company="Co",
        description="python fastapi postgresql",
        source="t",
        external_job_id="1",
    )
    low = svc.score_quality({}, job)
    high = svc.score_quality(
        {
            "summary": "Engineer",
            "skills": ["python", "fastapi", "postgresql"],
            "experience": [{"title": "Eng"}],
        },
        job,
    )
    assert high > low
