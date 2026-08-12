"""SQLAlchemy ORM models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.session import Base
from app.models.enums import (
    ApplicationStatus,
    AutomationStatus,
    AutomationTaskType,
    ContactType,
    JobStatus,
    MatchRecommendation,
    OutreachStatus,
    ResumeKind,
)

# Use JSONB on Postgres, JSON elsewhere (sqlite tests)
JSONType = JSON().with_variant(JSONB(), "postgresql")


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    auth_providers: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    daily_application_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    profile: Mapped[CandidateProfile | None] = relationship(back_populates="user", uselist=False)
    settings: Mapped[UserSettings | None] = relationship(back_populates="user", uselist=False)
    applications: Mapped[list[Application]] = relationship(back_populates="user")


class CandidateProfile(Base, TimestampMixin):
    __tablename__ = "candidate_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    personal_info: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    professional_summary: Mapped[str] = mapped_column(Text, default="")
    work_history: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    education: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    skills: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    projects: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    certifications: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    achievements: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    quantified_accomplishments: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    preferred_locations: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    remote_preference: Mapped[str] = mapped_column(String(32), default="remote")
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[str] = mapped_column(String(8), default="USD")
    employment_types: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    work_authorization: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    years_experience: Mapped[float] = mapped_column(Float, default=0.0)
    seniority_level: Mapped[str] = mapped_column(String(32), default="mid")
    answer_bank: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)

    user: Mapped[User] = relationship(back_populates="profile")


class UserSettings(Base, TimestampMixin):
    __tablename__ = "user_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    daily_application_limit: Mapped[int] = mapped_column(Integer, default=10)
    min_match_score: Mapped[float] = mapped_column(Float, default=0.65)
    min_resume_score: Mapped[float] = mapped_column(Float, default=0.70)
    auto_submit_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    outreach_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    linkedin_easy_apply_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    search_criteria: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    scoring_weights: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)

    user: Mapped[User] = relationship(back_populates="settings")


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source", "external_job_id", name="uq_jobs_source_external_id"),
        Index("ix_jobs_company", "company"),
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_discovered_at", "discovered_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    remote_status: Mapped[str | None] = mapped_column(String(64))
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    salary_currency: Mapped[str | None] = mapped_column(String(8))
    description: Mapped[str] = mapped_column(Text, default="")
    requirements: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    responsibilities: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    technologies: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048))
    official_application_url: Mapped[str | None] = mapped_column(String(2048))
    external_job_id: Mapped[str] = mapped_column(String(255), nullable=False)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    closing_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(32), default=JobStatus.ACTIVE.value)
    normalized_key: Mapped[str | None] = mapped_column(String(512))
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)


class JobMatch(Base, TimestampMixin):
    __tablename__ = "job_matches"
    __table_args__ = (
        UniqueConstraint("job_id", "candidate_id", name="uq_job_matches_job_candidate"),
        Index("ix_job_matches_overall_score", "overall_score"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    skill_match: Mapped[float] = mapped_column(Float, default=0.0)
    experience_match: Mapped[float] = mapped_column(Float, default=0.0)
    location_match: Mapped[float] = mapped_column(Float, default=0.0)
    seniority_match: Mapped[float] = mapped_column(Float, default=0.0)
    salary_match: Mapped[float] = mapped_column(Float, default=0.0)
    domain_match: Mapped[float] = mapped_column(Float, default=0.0)
    preference_match: Mapped[float] = mapped_column(Float, default=0.0)
    required_skills: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    missing_skills: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    strengths: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    weaknesses: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    explanation: Mapped[str] = mapped_column(Text, default="")
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    recommendation: Mapped[str] = mapped_column(
        String(32), default=MatchRecommendation.REVIEW.value
    )


class Resume(Base, TimestampMixin):
    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String(32), default=ResumeKind.TAILORED.value)
    version: Mapped[int] = mapped_column(Integer, default=1)
    content: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    generation_metadata: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    ats_analysis: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    quality_score: Mapped[float | None] = mapped_column(Float)
    file_path: Mapped[str | None] = mapped_column(String(1024))
    checksum: Mapped[str | None] = mapped_column(String(128))
    explainability: Mapped[list[Any]] = mapped_column(JSONType, default=list)


class Application(Base, TimestampMixin):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_applications_user_job"),
        Index("ix_applications_status", "status"),
        Index("ix_applications_submitted_at", "submitted_at"),
        Index("ix_applications_application_url", "application_url"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False
    )
    tailored_resume_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="SET NULL")
    )
    match_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_matches.id", ondelete="SET NULL")
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL")
    )
    research_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company_research.id", ondelete="SET NULL")
    )
    outreach_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("outreach_messages.id", ondelete="SET NULL")
    )
    application_url: Mapped[str | None] = mapped_column(String(2048))
    status: Mapped[str] = mapped_column(
        String(64), default=ApplicationStatus.DISCOVERED.value, nullable=False
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    external_application_id: Mapped[str | None] = mapped_column(String(255))
    confirmation_text: Mapped[str | None] = mapped_column(Text)
    confirmation_url: Mapped[str | None] = mapped_column(String(2048))
    screenshot_path: Mapped[str | None] = mapped_column(String(1024))
    browser_automation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    application_answers: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    quality_gate: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    idempotency_key: Mapped[str | None] = mapped_column(String(255), unique=True)

    user: Mapped[User] = relationship(back_populates="applications")
    job: Mapped[Job] = relationship()


class Contact(Base, TimestampMixin):
    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    linkedin_url: Mapped[str | None] = mapped_column(String(1024))
    email: Mapped[str | None] = mapped_column(String(320))
    source: Mapped[str] = mapped_column(String(128), default="")
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    contact_type: Mapped[str] = mapped_column(String(32), default=ContactType.OTHER.value)
    evidence: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    why_selected: Mapped[str] = mapped_column(Text, default="")


class CompanyResearch(Base, TimestampMixin):
    __tablename__ = "company_research"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    problem_summary: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    sources: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    candidate_value_proposition: Mapped[str] = mapped_column(Text, default="")
    raw_analysis: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)


class OutreachMessage(Base, TimestampMixin):
    __tablename__ = "outreach_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL")
    )
    recipient_name: Mapped[str] = mapped_column(String(255), default="")
    recipient_type: Mapped[str] = mapped_column(String(32), default=ContactType.RECRUITER.value)
    company_problem: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    value_proposition: Mapped[str] = mapped_column(Text, default="")
    generated_message: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default=OutreachStatus.DRAFT.value)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    channel: Mapped[str] = mapped_column(String(64), default="email")
    source: Mapped[str] = mapped_column(String(128), default="ai")


class AutomationRun(Base, TimestampMixin):
    __tablename__ = "automation_runs"
    __table_args__ = (
        Index("ix_automation_runs_status", "status"),
        Index("ix_automation_runs_task_type", "task_type"),
        Index("ix_automation_runs_correlation_id", "correlation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    task_type: Mapped[str] = mapped_column(
        String(64), default=AutomationTaskType.JOB_DISCOVERY.value
    )
    status: Mapped[str] = mapped_column(String(32), default=AutomationStatus.QUEUED.value)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    correlation_id: Mapped[str | None] = mapped_column(String(64))
    celery_task_id: Mapped[str | None] = mapped_column(String(255), index=True)
    result: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_created_at", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_state: Mapped[str | None] = mapped_column(String(64))
    new_state: Mapped[str | None] = mapped_column(String(64))
    result: Mapped[str] = mapped_column(String(64), default="Success")
    details: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)


class AiUsage(Base):
    __tablename__ = "ai_usage"
    __table_args__ = (Index("ix_ai_usage_created_at", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    operation: Mapped[str] = mapped_column(String(128), default="")
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    correlation_id: Mapped[str | None] = mapped_column(String(64))
    success: Mapped[bool] = mapped_column(Boolean, default=True)


class IntegrationCredential(Base, TimestampMixin):
    __tablename__ = "integration_credentials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    encrypted_payload: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active")
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
