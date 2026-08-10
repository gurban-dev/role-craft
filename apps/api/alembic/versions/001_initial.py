"""Initial schema — all application tables."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSONType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column("daily_application_limit", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "candidate_profiles",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("personal_info", JSONType, server_default="{}"),
        sa.Column("professional_summary", sa.Text(), server_default=""),
        sa.Column("work_history", JSONType, server_default="[]"),
        sa.Column("education", JSONType, server_default="[]"),
        sa.Column("skills", JSONType, server_default="[]"),
        sa.Column("projects", JSONType, server_default="[]"),
        sa.Column("certifications", JSONType, server_default="[]"),
        sa.Column("achievements", JSONType, server_default="[]"),
        sa.Column("quantified_accomplishments", JSONType, server_default="[]"),
        sa.Column("preferred_locations", JSONType, server_default="[]"),
        sa.Column("remote_preference", sa.String(32), server_default="remote"),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(8), server_default="USD"),
        sa.Column("employment_types", JSONType, server_default="[]"),
        sa.Column("work_authorization", JSONType, server_default="{}"),
        sa.Column("years_experience", sa.Float(), server_default="0"),
        sa.Column("seniority_level", sa.String(32), server_default="mid"),
        sa.Column("answer_bank", JSONType, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "user_settings",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("daily_application_limit", sa.Integer(), server_default="10"),
        sa.Column("min_match_score", sa.Float(), server_default="0.65"),
        sa.Column("min_resume_score", sa.Float(), server_default="0.70"),
        sa.Column("auto_submit_enabled", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("outreach_enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("linkedin_easy_apply_fallback", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("search_criteria", JSONType, server_default="{}"),
        sa.Column("scoring_weights", JSONType, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "jobs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255)),
        sa.Column("remote_status", sa.String(64)),
        sa.Column("salary_min", sa.Integer()),
        sa.Column("salary_max", sa.Integer()),
        sa.Column("salary_currency", sa.String(8)),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("requirements", JSONType, server_default="[]"),
        sa.Column("responsibilities", JSONType, server_default="[]"),
        sa.Column("technologies", JSONType, server_default="[]"),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("official_application_url", sa.String(2048)),
        sa.Column("external_job_id", sa.String(255), nullable=False),
        sa.Column("discovered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("closing_date", sa.Date()),
        sa.Column("status", sa.String(32), server_default="ACTIVE"),
        sa.Column("normalized_key", sa.String(512)),
        sa.Column("raw_payload", JSONType, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("source", "external_job_id", name="uq_jobs_source_external_id"),
    )
    op.create_index("ix_jobs_company", "jobs", ["company"])
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_discovered_at", "jobs", ["discovered_at"])
    op.create_index("ix_jobs_source", "jobs", ["source"])
    op.create_index("ix_jobs_normalized_key", "jobs", ["normalized_key"])

    op.create_table(
        "job_matches",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("job_id", UUID, sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_id", UUID, sa.ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("skill_match", sa.Float(), server_default="0"),
        sa.Column("experience_match", sa.Float(), server_default="0"),
        sa.Column("location_match", sa.Float(), server_default="0"),
        sa.Column("seniority_match", sa.Float(), server_default="0"),
        sa.Column("salary_match", sa.Float(), server_default="0"),
        sa.Column("domain_match", sa.Float(), server_default="0"),
        sa.Column("preference_match", sa.Float(), server_default="0"),
        sa.Column("required_skills", JSONType, server_default="[]"),
        sa.Column("missing_skills", JSONType, server_default="[]"),
        sa.Column("strengths", JSONType, server_default="[]"),
        sa.Column("weaknesses", JSONType, server_default="[]"),
        sa.Column("explanation", sa.Text(), server_default=""),
        sa.Column("score_breakdown", JSONType, server_default="{}"),
        sa.Column("recommendation", sa.String(32), server_default="REVIEW"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("job_id", "candidate_id", name="uq_job_matches_job_candidate"),
    )
    op.create_index("ix_job_matches_overall_score", "job_matches", ["overall_score"])

    op.create_table(
        "resumes",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_id", UUID, sa.ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", UUID, sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("kind", sa.String(32), server_default="TAILORED"),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("content", JSONType, server_default="{}"),
        sa.Column("generation_metadata", JSONType, server_default="{}"),
        sa.Column("ats_analysis", JSONType, server_default="{}"),
        sa.Column("quality_score", sa.Float()),
        sa.Column("file_path", sa.String(1024)),
        sa.Column("checksum", sa.String(128)),
        sa.Column("explainability", JSONType, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"])

    op.create_table(
        "contacts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", UUID, sa.ForeignKey("jobs.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("title", sa.String(255)),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("linkedin_url", sa.String(1024)),
        sa.Column("email", sa.String(320)),
        sa.Column("source", sa.String(128), server_default=""),
        sa.Column("confidence_score", sa.Float(), server_default="0"),
        sa.Column("contact_type", sa.String(32), server_default="OTHER"),
        sa.Column("evidence", JSONType, server_default="[]"),
        sa.Column("why_selected", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_contacts_user_id", "contacts", ["user_id"])

    op.create_table(
        "company_research",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", UUID, sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("problem_summary", sa.Text(), server_default=""),
        sa.Column("evidence", JSONType, server_default="[]"),
        sa.Column("sources", JSONType, server_default="[]"),
        sa.Column("confidence_score", sa.Float(), server_default="0"),
        sa.Column("candidate_value_proposition", sa.Text(), server_default=""),
        sa.Column("raw_analysis", JSONType, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_company_research_user_id", "company_research", ["user_id"])
    op.create_index("ix_company_research_job_id", "company_research", ["job_id"])

    op.create_table(
        "outreach_messages",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", UUID),
        sa.Column("contact_id", UUID, sa.ForeignKey("contacts.id", ondelete="SET NULL")),
        sa.Column("recipient_name", sa.String(255), server_default=""),
        sa.Column("recipient_type", sa.String(32), server_default="RECRUITER"),
        sa.Column("company_problem", sa.Text(), server_default=""),
        sa.Column("evidence", JSONType, server_default="[]"),
        sa.Column("value_proposition", sa.Text(), server_default=""),
        sa.Column("generated_message", sa.Text(), server_default=""),
        sa.Column("status", sa.String(32), server_default="DRAFT"),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("channel", sa.String(64), server_default="email"),
        sa.Column("source", sa.String(128), server_default="ai"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_outreach_messages_user_id", "outreach_messages", ["user_id"])
    op.create_index("ix_outreach_messages_application_id", "outreach_messages", ["application_id"])

    op.create_table(
        "applications",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", UUID, sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_id", UUID, sa.ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tailored_resume_id", UUID, sa.ForeignKey("resumes.id", ondelete="SET NULL")),
        sa.Column("match_id", UUID, sa.ForeignKey("job_matches.id", ondelete="SET NULL")),
        sa.Column("contact_id", UUID, sa.ForeignKey("contacts.id", ondelete="SET NULL")),
        sa.Column("research_id", UUID, sa.ForeignKey("company_research.id", ondelete="SET NULL")),
        sa.Column("outreach_id", UUID, sa.ForeignKey("outreach_messages.id", ondelete="SET NULL")),
        sa.Column("application_url", sa.String(2048)),
        sa.Column("status", sa.String(64), nullable=False, server_default="DISCOVERED"),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("failure_reason", sa.Text()),
        sa.Column("external_application_id", sa.String(255)),
        sa.Column("confirmation_text", sa.Text()),
        sa.Column("confirmation_url", sa.String(2048)),
        sa.Column("screenshot_path", sa.String(1024)),
        sa.Column("browser_automation_run_id", UUID),
        sa.Column("application_answers", JSONType, server_default="{}"),
        sa.Column("quality_gate", JSONType, server_default="{}"),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("approved_by", UUID),
        sa.Column("idempotency_key", sa.String(255), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "job_id", name="uq_applications_user_job"),
    )
    op.create_index("ix_applications_user_id", "applications", ["user_id"])
    op.create_index("ix_applications_job_id", "applications", ["job_id"])
    op.create_index("ix_applications_status", "applications", ["status"])
    op.create_index("ix_applications_submitted_at", "applications", ["submitted_at"])
    op.create_index("ix_applications_application_url", "applications", ["application_url"])

    op.create_table(
        "automation_runs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("application_id", UUID),
        sa.Column("job_id", UUID),
        sa.Column("task_type", sa.String(64), server_default="JOB_DISCOVERY"),
        sa.Column("status", sa.String(32), server_default="QUEUED"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("error", sa.Text()),
        sa.Column("retry_count", sa.Integer(), server_default="0"),
        sa.Column("correlation_id", sa.String(64)),
        sa.Column("celery_task_id", sa.String(255)),
        sa.Column("result", JSONType, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_automation_runs_user_id", "automation_runs", ["user_id"])
    op.create_index("ix_automation_runs_application_id", "automation_runs", ["application_id"])
    op.create_index("ix_automation_runs_job_id", "automation_runs", ["job_id"])
    op.create_index("ix_automation_runs_status", "automation_runs", ["status"])
    op.create_index("ix_automation_runs_task_type", "automation_runs", ["task_type"])
    op.create_index("ix_automation_runs_correlation_id", "automation_runs", ["correlation_id"])
    op.create_index("ix_automation_runs_celery_task_id", "automation_runs", ["celery_task_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column("previous_state", sa.String(64)),
        sa.Column("new_state", sa.String(64)),
        sa.Column("result", sa.String(64), server_default="Success"),
        sa.Column("details", JSONType, server_default="{}"),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    op.create_table(
        "ai_usage",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", UUID),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("operation", sa.String(128), server_default=""),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("estimated_cost_usd", sa.Float()),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("correlation_id", sa.String(64)),
        sa.Column("success", sa.Boolean(), server_default=sa.text("true")),
    )
    op.create_index("ix_ai_usage_created_at", "ai_usage", ["created_at"])
    op.create_index("ix_ai_usage_user_id", "ai_usage", ["user_id"])

    op.create_table(
        "integration_credentials",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("encrypted_payload", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), server_default="active"),
        sa.Column("last_verified_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_integration_credentials_user_id", "integration_credentials", ["user_id"])


def downgrade() -> None:
    op.drop_table("integration_credentials")
    op.drop_table("ai_usage")
    op.drop_table("audit_logs")
    op.drop_table("automation_runs")
    op.drop_table("applications")
    op.drop_table("outreach_messages")
    op.drop_table("company_research")
    op.drop_table("contacts")
    op.drop_table("resumes")
    op.drop_table("job_matches")
    op.drop_table("jobs")
    op.drop_table("user_settings")
    op.drop_table("candidate_profiles")
    op.drop_table("users")
