from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job


@pytest.mark.asyncio
async def test_list_jobs_filters_by_posted_date_and_ignores_missing_dates(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    now = datetime.now(UTC)
    recent = Job(
        title="Recent", company="Example", source="test", external_job_id=str(uuid4()),
        posted_at=now - timedelta(hours=20),
    )
    old = Job(
        title="Old", company="Example", source="test", external_job_id=str(uuid4()),
        posted_at=now - timedelta(hours=30),
    )
    unknown = Job(
        title="Unknown", company="Example", source="test", external_job_id=str(uuid4()),
    )
    db_session.add_all([recent, old, unknown])
    await db_session.commit()

    response = await client.get(
        "/api/jobs?posted_within_hours=24", headers=auth_headers
    )

    assert response.status_code == 200
    assert [job["title"] for job in response.json()] == ["Recent"]


@pytest.mark.asyncio
async def test_list_jobs_rejects_unsupported_posted_range(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.get(
        "/api/jobs?posted_within_hours=48", headers=auth_headers
    )

    assert response.status_code == 422
