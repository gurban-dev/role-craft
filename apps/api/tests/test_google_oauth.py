"""Google OAuth flow tests (mocked Google HTTP)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthError
from app.models import User
from app.schemas import RegisterRequest
from app.services.auth_service import AuthService
from app.services.google_oauth_service import (
    OAUTH_STATE_COOKIE,
    GoogleIdentity,
    GoogleOAuthService,
)


@pytest.fixture
def google_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")
    monkeypatch.setenv("WEB_APP_URL", "http://localhost:3000")
    get_settings.cache_clear()
    settings = get_settings()
    yield settings
    get_settings.cache_clear()


def test_authorization_url_includes_state(google_settings: Settings) -> None:
    url = GoogleOAuthService(settings=google_settings).authorization_url("abc123")
    assert "accounts.google.com" in url
    assert "client_id=test-client-id" in url
    assert "state=abc123" in url
    assert "openid" in url


@pytest.mark.asyncio
async def test_login_or_register_creates_google_user(
    db_session: AsyncSession, google_settings: Settings
) -> None:
    identity = GoogleIdentity(
        sub="google-sub-1",
        email="newuser@gmail.com",
        name="New User",
        email_verified=True,
    )
    user, token, csrf = await GoogleOAuthService(db_session, google_settings).login_or_register(
        identity
    )
    assert user.email == "newuser@gmail.com"
    assert user.google_sub == "google-sub-1"
    assert user.hashed_password is None
    assert "google" in (user.auth_providers or [])
    assert token and csrf


@pytest.mark.asyncio
async def test_login_or_register_links_existing_password_user(
    db_session: AsyncSession, google_settings: Settings
) -> None:
    existing, _, _ = await AuthService(db_session).register(
        RegisterRequest(email="linked@example.com", password="password123", name="Linked")
    )
    await db_session.commit()

    identity = GoogleIdentity(
        sub="google-sub-link",
        email="linked@example.com",
        name="Linked",
        email_verified=True,
    )
    user, _, _ = await GoogleOAuthService(db_session, google_settings).login_or_register(identity)
    assert user.id == existing.id
    assert user.google_sub == "google-sub-link"
    assert user.hashed_password is not None
    assert "google" in (user.auth_providers or [])
    assert "password" in (user.auth_providers or [])


@pytest.mark.asyncio
async def test_password_login_rejected_for_google_only_user(
    db_session: AsyncSession, google_settings: Settings
) -> None:
    user = User(
        email="gonly@example.com",
        name="G Only",
        hashed_password=None,
        google_sub="sub-only",
        auth_providers=["google"],
    )
    db_session.add(user)
    await db_session.commit()

    with pytest.raises(AuthError, match="Google sign-in"):
        from app.schemas import LoginRequest

        await AuthService(db_session).login(
            LoginRequest(email="gonly@example.com", password="whatever12")
        )


@pytest.mark.asyncio
async def test_exchange_code_rejects_unverified_email(google_settings: Settings) -> None:
    svc = GoogleOAuthService(settings=google_settings)

    class FakeResp:
        def __init__(self, status_code: int, payload: dict) -> None:
            self.status_code = status_code
            self._payload = payload
            self.text = str(payload)

        def json(self) -> dict:
            return self._payload

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            return FakeResp(200, {"access_token": "tok"})

        async def get(self, *args, **kwargs):
            return FakeResp(
                200,
                {
                    "sub": "sub-x",
                    "email": "u@example.com",
                    "name": "U",
                    "email_verified": False,
                },
            )

    with patch("app.services.google_oauth_service.httpx.AsyncClient", return_value=FakeClient()):
        with pytest.raises(AuthError, match="not verified"):
            await svc.exchange_code("code")


@pytest.mark.asyncio
async def test_callback_invalid_state_redirects(
    client: AsyncClient, google_settings: Settings
) -> None:
    resp = await client.get(
        "/api/auth/google/callback",
        params={"code": "abc", "state": "one"},
        cookies={OAUTH_STATE_COOKIE: "two"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "error=google_auth_failed" in resp.headers["location"]


@pytest.mark.asyncio
async def test_callback_creates_session_cookies(
    client: AsyncClient, db_session: AsyncSession, google_settings: Settings
) -> None:
    identity = GoogleIdentity(
        sub=f"sub-{uuid4().hex[:8]}",
        email=f"oauth-{uuid4().hex[:6]}@gmail.com",
        name="OAuth User",
        email_verified=True,
    )
    state = "valid-state-token"

    with patch.object(
        GoogleOAuthService,
        "exchange_code",
        new=AsyncMock(return_value=identity),
    ):
        resp = await client.get(
            "/api/auth/google/callback",
            params={"code": "auth-code", "state": state},
            cookies={OAUTH_STATE_COOKIE: state},
            follow_redirects=False,
        )

    assert resp.status_code == 302
    assert resp.headers["location"].endswith("/dashboard")
    set_cookies = resp.headers.get_list("set-cookie")
    assert any(c.startswith("jaa_session=") for c in set_cookies)
    assert any(c.startswith("jaa_csrf=") for c in set_cookies)

    # Idempotent second login by google_sub / email
    user, _, _ = await GoogleOAuthService(db_session, google_settings).login_or_register(identity)
    assert user.google_sub == identity.sub
    assert user.email == identity.email


@pytest.mark.asyncio
async def test_google_start_redirects_when_configured(
    client: AsyncClient, google_settings: Settings
) -> None:
    resp = await client.get("/api/auth/google", follow_redirects=False)
    assert resp.status_code == 302
    assert "accounts.google.com" in resp.headers["location"]
    assert any(OAUTH_STATE_COOKIE in c for c in resp.headers.get_list("set-cookie"))
