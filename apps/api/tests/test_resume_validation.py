"""Resume validation tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.exceptions import ValidationAppError
from app.integrations.llm.schemas import ResumeChanges
from app.models import CandidateProfile, Resume, User
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


def test_extracts_plain_text_resume() -> None:
    assert ResumeService._extract_resume_text(".txt", b"Python Engineer") == "Python Engineer"


def test_extracts_legacy_doc_using_antiword() -> None:
    with patch("app.services.resume_service.subprocess.run") as run:
        run.return_value.stdout = b"Python Engineer"
        text = ResumeService._extract_resume_text(".doc", b"legacy doc bytes")

    assert text == "Python Engineer"
    assert run.call_args.args[0][0] == "antiword"


@pytest.mark.asyncio
async def test_upload_extracts_resume_and_stores_original() -> None:
    user = User(id=uuid4(), email="resume@example.com", name="Resume User")
    profile = CandidateProfile(id=uuid4(), user_id=user.id, skills=[])
    db = Mock()
    db.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=0)))
    db.flush = AsyncMock()
    db.add = Mock()
    svc = ResumeService(db, Settings(app_env="test", open_router_token=None))
    svc.users.get_profile = AsyncMock(return_value=profile)
    resume_bytes = (
        b"Senior Python Engineer\n"
        b"8 years of professional experience\n"
        b"Python, Django, PostgreSQL"
    )

    uploaded = await svc.upload_original(
        user, filename="resume.txt", content=resume_bytes
    )

    assert uploaded.original_file == resume_bytes
    assert uploaded.content["extracted_profile"]["years_of_experience"] == 8
    assert "Python" in profile.skills
    assert profile.seniority_level == "senior"
    assert any(isinstance(call.args[0], Resume) for call in db.add.call_args_list)
