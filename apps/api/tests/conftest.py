"""Pytest fixtures — in-memory SQLite via aiosqlite."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

# Ensure test env before importing app modules that read settings.
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-for-unit-tests-only"
os.environ["JWT_SECRET"] = "test-jwt-secret-for-unit-tests-only"

from app.core.config import get_settings

get_settings.cache_clear()

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.security import create_access_token  # noqa: E402
from app.db.session import Base, get_db, reset_engine  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import CandidateProfile, User  # noqa: E402
from app.schemas import RegisterRequest  # noqa: E402
from app.services.auth_service import AuthService  # noqa: E402

reset_engine()
get_settings.cache_clear()


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def app(engine):
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    application = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    application.dependency_overrides[get_db] = override_get_db
    yield application
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def user(db_session: AsyncSession) -> User:
    svc = AuthService(db_session)
    u, _, _ = await svc.register(
        RegisterRequest(email="tester@example.com", password="password123", name="Test User")
    )
    await db_session.commit()
    return u


@pytest_asyncio.fixture
async def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def profile(db_session: AsyncSession, user: User) -> CandidateProfile:
    profile = (
        await db_session.execute(
            select(CandidateProfile).where(CandidateProfile.user_id == user.id)
        )
    ).scalar_one()
    profile.professional_summary = "Backend engineer with Python and FastAPI experience."
    profile.skills = ["python", "fastapi", "postgresql", "redis", "docker"]
    profile.work_history = [
        {
            "company": "Acme",
            "title": "Software Engineer",
            "start": "2020",
            "end": "2024",
            "highlights": ["Built APIs in Python"],
        }
    ]
    profile.years_experience = 5.0
    profile.seniority_level = "mid"
    profile.remote_preference = "remote"
    profile.preferred_locations = ["Remote"]
    profile.quantified_accomplishments = ["Reduced API latency by 40%"]
    await db_session.commit()
    await db_session.refresh(profile)
    return profile
