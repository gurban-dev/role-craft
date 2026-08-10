"""Browser automation data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ApplicationQuestion:
    label: str
    input_type: str = "text"
    required: bool = True
    options: list[str] = field(default_factory=list)
    name: str | None = None


@dataclass
class ApplicationData:
    job_title: str
    company: str
    candidate_name: str
    candidate_email: str
    resume_path: str | None = None
    answers: dict[str, Any] = field(default_factory=dict)
    phone: str | None = None
    linkedin_url: str | None = None


@dataclass
class SubmissionResult:
    success: bool
    needs_human: bool = False
    message: str | None = None
    confirmation_text: str | None = None
    confirmation_url: str | None = None
    external_id: str | None = None
    screenshot_path: str | None = None
