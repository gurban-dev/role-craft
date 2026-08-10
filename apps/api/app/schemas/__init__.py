"""Pydantic v2 API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# Auth
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(ORMModel):
    id: UUID
    email: EmailStr
    name: str
    timezone: str
    daily_application_limit: int
    created_at: datetime


# Profile
class CandidateProfileUpdate(BaseModel):
    personal_info: dict[str, Any] | None = None
    professional_summary: str | None = None
    work_history: list[dict[str, Any]] | None = None
    education: list[dict[str, Any]] | None = None
    skills: list[Any] | None = None
    projects: list[dict[str, Any]] | None = None
    certifications: list[dict[str, Any]] | None = None
    achievements: list[Any] | None = None
    quantified_accomplishments: list[Any] | None = None
    preferred_locations: list[Any] | None = None
    remote_preference: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    employment_types: list[Any] | None = None
    work_authorization: dict[str, Any] | None = None
    years_experience: float | None = None
    seniority_level: str | None = None
    answer_bank: dict[str, Any] | None = None


class CandidateProfileOut(ORMModel):
    id: UUID
    user_id: UUID
    personal_info: dict[str, Any]
    professional_summary: str
    work_history: list[Any]
    education: list[Any]
    skills: list[Any]
    projects: list[Any]
    certifications: list[Any]
    achievements: list[Any]
    quantified_accomplishments: list[Any]
    preferred_locations: list[Any]
    remote_preference: str
    salary_min: int | None
    salary_max: int | None
    salary_currency: str
    employment_types: list[Any]
    work_authorization: dict[str, Any]
    years_experience: float
    seniority_level: str
    answer_bank: dict[str, Any]
    updated_at: datetime


# Settings
class SettingsUpdate(BaseModel):
    daily_application_limit: int | None = Field(default=None, ge=1, le=50)
    min_match_score: float | None = Field(default=None, ge=0, le=1)
    min_resume_score: float | None = Field(default=None, ge=0, le=1)
    auto_submit_enabled: bool | None = None
    outreach_enabled: bool | None = None
    linkedin_easy_apply_fallback: bool | None = None
    search_criteria: dict[str, Any] | None = None
    scoring_weights: dict[str, Any] | None = None


class SettingsOut(ORMModel):
    daily_application_limit: int
    min_match_score: float
    min_resume_score: float
    auto_submit_enabled: bool
    outreach_enabled: bool
    linkedin_easy_apply_fallback: bool
    search_criteria: dict[str, Any]
    scoring_weights: dict[str, Any]


# Jobs
class JobSearchRequest(BaseModel):
    query: str = "software engineer"
    location: str | None = None
    remote_only: bool = False
    sources: list[str] | None = None
    limit: int = Field(default=25, ge=1, le=100)


class JobOut(ORMModel):
    id: UUID
    title: str
    company: str
    location: str | None
    remote_status: str | None
    salary_min: int | None
    salary_max: int | None
    salary_currency: str | None
    description: str
    requirements: list[Any]
    technologies: list[Any]
    source: str
    source_url: str | None
    official_application_url: str | None
    external_job_id: str
    discovered_at: datetime
    status: str


class JobMatchOut(ORMModel):
    id: UUID
    job_id: UUID
    overall_score: float
    skill_match: float
    experience_match: float
    location_match: float
    seniority_match: float
    salary_match: float
    domain_match: float
    preference_match: float
    required_skills: list[Any]
    missing_skills: list[Any]
    strengths: list[Any]
    weaknesses: list[Any]
    explanation: str
    score_breakdown: dict[str, Any]
    recommendation: str


# Applications
class ApplicationOut(ORMModel):
    id: UUID
    user_id: UUID
    job_id: UUID
    status: str
    application_url: str | None
    submitted_at: datetime | None
    failure_reason: str | None
    confirmation_text: str | None
    confirmation_url: str | None
    quality_gate: dict[str, Any]
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ApplicationDetailOut(ApplicationOut):
    application_answers: dict[str, Any]
    tailored_resume_id: UUID | None
    match_id: UUID | None
    contact_id: UUID | None
    research_id: UUID | None
    outreach_id: UUID | None
    screenshot_path: str | None
    browser_automation_run_id: UUID | None


# Dashboard
class DashboardStats(BaseModel):
    daily_target: int
    submitted_today: int
    in_progress: int
    needs_human_action: int
    rejected_by_quality: int
    remaining: int
    submitted_this_week: int
    average_match_score: float | None
    response_rate: float | None
    interview_rate: float | None
    by_source: dict[str, int]
    by_company: dict[str, int]
    pipeline: dict[str, int]


# Runs
class AutomationRunOut(ORMModel):
    id: UUID
    task_type: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    error: str | None
    retry_count: int
    correlation_id: str | None
    celery_task_id: str | None
    result: dict[str, Any]
    created_at: datetime


class TaskEnqueueResponse(BaseModel):
    task_id: str
    run_id: UUID
    status: str = "queued"


class HealthOut(BaseModel):
    status: str
    version: str


class ReadyOut(BaseModel):
    status: str
    database: bool
    redis: bool
    details: dict[str, str] = Field(default_factory=dict)


class ContactOut(ORMModel):
    id: UUID
    name: str
    title: str | None
    company: str
    linkedin_url: str | None
    email: str | None
    source: str
    confidence_score: float
    contact_type: str
    evidence: list[Any]
    why_selected: str


class ResearchOut(ORMModel):
    id: UUID
    job_id: UUID
    company: str
    problem_summary: str
    evidence: list[Any]
    sources: list[Any]
    confidence_score: float
    candidate_value_proposition: str


class ResumeOut(ORMModel):
    id: UUID
    job_id: UUID | None
    kind: str
    version: int
    quality_score: float | None
    file_path: str | None
    ats_analysis: dict[str, Any]
    explainability: list[Any]
    created_at: datetime


class OutreachOut(ORMModel):
    id: UUID
    recipient_name: str
    recipient_type: str
    company_problem: str
    evidence: list[Any]
    value_proposition: str
    generated_message: str
    status: str
    channel: str
