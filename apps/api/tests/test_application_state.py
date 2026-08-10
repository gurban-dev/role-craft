"""Application state transition tests."""

from __future__ import annotations

import pytest

from app.core.exceptions import ValidationAppError
from app.models.enums import ApplicationStatus
from app.services.application_state import can_transition, transition


def test_valid_happy_path() -> None:
    assert can_transition(ApplicationStatus.DISCOVERED, ApplicationStatus.ANALYZING)
    assert transition(ApplicationStatus.DISCOVERED, ApplicationStatus.ANALYZING) == (
        ApplicationStatus.ANALYZING
    )
    assert transition(ApplicationStatus.ANALYZING, ApplicationStatus.MATCHED) == (
        ApplicationStatus.MATCHED
    )
    assert transition(ApplicationStatus.MATCHED, ApplicationStatus.RESUME_GENERATING)
    assert transition(ApplicationStatus.RESUME_GENERATING, ApplicationStatus.RESUME_READY)
    assert transition(ApplicationStatus.RESUME_READY, ApplicationStatus.READY_FOR_REVIEW)
    assert transition(ApplicationStatus.READY_FOR_REVIEW, ApplicationStatus.APPLYING)
    assert transition(ApplicationStatus.APPLYING, ApplicationStatus.SUBMITTED)


def test_illegal_transition() -> None:
    with pytest.raises(ValidationAppError):
        transition(ApplicationStatus.DISCOVERED, ApplicationStatus.SUBMITTED)
    with pytest.raises(ValidationAppError):
        transition(ApplicationStatus.SUBMITTED, ApplicationStatus.APPLYING)


def test_same_status_allowed() -> None:
    assert transition(ApplicationStatus.MATCHED, ApplicationStatus.MATCHED) == (
        ApplicationStatus.MATCHED
    )


def test_needs_human_recovery() -> None:
    assert can_transition(
        ApplicationStatus.NEEDS_HUMAN_ACTION, ApplicationStatus.READY_FOR_REVIEW
    )
    assert can_transition(ApplicationStatus.FAILED, ApplicationStatus.APPLYING)
