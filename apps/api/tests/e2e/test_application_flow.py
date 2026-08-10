"""End-to-end style API flow with profile + settings."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_profile_and_settings(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/auth/register",
        json={"email": "e2e@example.com", "password": "password123", "name": "E2E User"},
    )
    assert reg.status_code == 200
    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    profile = await client.patch(
        "/api/profile",
        json={
            "professional_summary": "Engineer",
            "skills": ["Python", "FastAPI"],
            "years_experience": 5,
            "seniority_level": "senior",
        },
    )
    assert profile.status_code == 200
    settings = await client.get("/api/settings")
    assert settings.status_code == 200
    assert settings.json()["auto_submit_enabled"] is False
