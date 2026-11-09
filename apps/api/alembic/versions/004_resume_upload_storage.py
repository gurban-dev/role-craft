"""Store uploaded original resume files in PostgreSQL."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "004_resume_upload_storage"
down_revision: str | None = "003_eea_job_discovery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("resumes", sa.Column("original_filename", sa.String(length=255), nullable=True))
    op.add_column(
        "resumes",
        sa.Column("original_content_type", sa.String(length=128), nullable=True),
    )
    op.add_column("resumes", sa.Column("original_file", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column("resumes", "original_file")
    op.drop_column("resumes", "original_content_type")
    op.drop_column("resumes", "original_filename")
