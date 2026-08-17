"""Add EEA discovery metadata to jobs."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_eea_job_discovery"
down_revision: Union[str, None] = "002_google_oauth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSONType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column("jobs", sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("applicant_count", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("country_code", sa.String(length=8), nullable=True))
    op.add_column(
        "jobs",
        sa.Column("is_eea", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "english_required",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "jobs",
        sa.Column("visa_sponsorship", sa.String(length=32), server_default="unknown", nullable=False),
    )
    op.add_column(
        "jobs",
        sa.Column("fit_score_10", sa.Float(), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("structured_profile", JSONType, server_default="{}", nullable=False),
    )
    op.create_index("ix_jobs_posted_at", "jobs", ["posted_at"])
    op.create_index("ix_jobs_is_eea", "jobs", ["is_eea"])
    op.create_index("ix_jobs_applicant_count", "jobs", ["applicant_count"])


def downgrade() -> None:
    op.drop_column("candidate_profiles", "structured_profile")
    op.drop_index("ix_jobs_applicant_count", table_name="jobs")
    op.drop_index("ix_jobs_is_eea", table_name="jobs")
    op.drop_index("ix_jobs_posted_at", table_name="jobs")
    op.drop_column("jobs", "fit_score_10")
    op.drop_column("jobs", "visa_sponsorship")
    op.drop_column("jobs", "english_required")
    op.drop_column("jobs", "is_eea")
    op.drop_column("jobs", "country_code")
    op.drop_column("jobs", "applicant_count")
    op.drop_column("jobs", "posted_at")
