"""Structured LLM output schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class JobAnalysis(BaseModel):
    """Parsed job description analysis."""

    title: str = ""
    company: str = ""
    summary: str = ""
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    seniority: str = "mid"
    years_experience_min: float | None = None
    remote_status: str | None = None
    location: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    red_flags: list[str] = Field(default_factory=list)
    application_tips: list[str] = Field(default_factory=list)


class ResumeChanges(BaseModel):
    """Truthful resume tailoring suggestions grounded in the candidate profile."""

    summary: str = ""
    highlighted_skills: list[str] = Field(default_factory=list)
    reordered_experience: list[dict[str, Any]] = Field(default_factory=list)
    selected_projects: list[dict[str, Any]] = Field(default_factory=list)
    selected_accomplishments: list[str] = Field(default_factory=list)
    keyword_alignments: list[str] = Field(default_factory=list)
    explainability: list[str] = Field(default_factory=list)
    invented_claims: list[str] = Field(
        default_factory=list,
        description="Must be empty; any fabricated claims are validation failures",
    )


class EvidenceItem(BaseModel):
    claim: str
    source_url: str | None = None
    source_title: str | None = None
    confidence: float = Field(ge=0, le=1, default=0.5)


class CompanyResearchResult(BaseModel):
    company: str = ""
    problem_summary: str = ""
    evidence: list[EvidenceItem] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0, le=1, default=0.0)
    candidate_value_proposition: str = ""
    notes: str = ""


class ContactRecommendation(BaseModel):
    name: str = ""
    title: str | None = None
    company: str = ""
    linkedin_url: str | None = None
    email: str | None = None
    contact_type: str = "RECRUITER"
    confidence_score: float = Field(ge=0, le=1, default=0.0)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    why_selected: str = ""
    source: str = "llm"


class OutreachDraft(BaseModel):
    recipient_name: str = ""
    recipient_type: str = "RECRUITER"
    company_problem: str = ""
    evidence: list[EvidenceItem] = Field(default_factory=list)
    value_proposition: str = ""
    message: str = ""
    channel: str = "email"
    skip_reason: str | None = None
    confidence_score: float = Field(ge=0, le=1, default=0.0)


class ApplicationAnswerDraft(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)
    confidence_by_question: dict[str, float] = Field(default_factory=dict)
    unanswered: list[str] = Field(default_factory=list)
    notes: str = ""
