"""Add Google OAuth fields to users."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_google_oauth"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSONType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(length=255),
        nullable=True,
    )
    op.add_column("users", sa.Column("google_sub", sa.String(length=255), nullable=True))
    op.add_column(
        "users",
        sa.Column("auth_providers", JSONType, server_default="[]", nullable=False),
    )
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)

    # Existing password users
    op.execute(
        sa.text(
            "UPDATE users SET auth_providers = '[\"password\"]' "
            "WHERE hashed_password IS NOT NULL AND "
            "(auth_providers IS NULL OR auth_providers = '[]' OR auth_providers = 'null')"
        )
    )


def downgrade() -> None:
    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_column("users", "auth_providers")
    op.drop_column("users", "google_sub")
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(length=255),
        nullable=False,
    )
