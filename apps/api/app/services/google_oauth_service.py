"""Google OAuth 2.0 authorization-code helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthError, ConfigurationError
from app.core.logging import get_logger
from app.core.security import create_access_token, generate_csrf_token
from app.models import CandidateProfile, User, UserSettings

logger = get_logger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

OAUTH_STATE_COOKIE = "jaa_oauth_state"


@dataclass(frozen=True)
class GoogleIdentity:
    sub: str
    email: str
    name: str
    email_verified: bool


class GoogleOAuthService:
    def __init__(self, db: AsyncSession | None = None, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    def authorization_url(self, state: str) -> str:
        if not self.settings.google_oauth_configured:
            raise ConfigurationError(
                "Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
            )
        params = {
            "client_id": self.settings.google_client_id,
            "redirect_uri": self.settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "include_granted_scopes": "true",
            "prompt": "select_account",
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> GoogleIdentity:
        if not self.settings.google_oauth_configured:
            raise ConfigurationError(
                "Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
            )
        async with httpx.AsyncClient(timeout=20.0) as client:
            token_resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "redirect_uri": self.settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if token_resp.status_code >= 400:
                logger.warning(
                    "google_token_exchange_failed",
                    status=token_resp.status_code,
                    body=token_resp.text[:500],
                )
                raise AuthError("Google authentication failed")
            token_data: dict[str, Any] = token_resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise AuthError("Google authentication failed")

            info_resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if info_resp.status_code >= 400:
                logger.warning(
                    "google_userinfo_failed",
                    status=info_resp.status_code,
                    body=info_resp.text[:500],
                )
                raise AuthError("Google authentication failed")
            info: dict[str, Any] = info_resp.json()

        sub = str(info.get("sub") or "").strip()
        email = str(info.get("email") or "").strip().lower()
        name = str(info.get("name") or "").strip() or (email.split("@")[0] if email else "User")
        verified = info.get("email_verified")
        email_verified = verified is True or verified == "true"
        if not sub or not email:
            raise AuthError("Google account is missing required profile fields")
        if not email_verified:
            raise AuthError("Google email is not verified")
        return GoogleIdentity(sub=sub, email=email, name=name, email_verified=email_verified)

    async def login_or_register(self, identity: GoogleIdentity) -> tuple[User, str, str]:
        """Find by google_sub, else link by email, else create Google-only user."""
        if self.db is None:
            raise RuntimeError("Database session required for login_or_register")
        db = self.db
        by_sub = (
            await db.execute(select(User).where(User.google_sub == identity.sub))
        ).scalar_one_or_none()
        if by_sub:
            self._ensure_google_provider(by_sub)
            if by_sub.name != identity.name and identity.name:
                by_sub.name = identity.name
            await db.flush()
            return by_sub, create_access_token(str(by_sub.id)), generate_csrf_token()

        by_email = (
            await db.execute(select(User).where(User.email == identity.email))
        ).scalar_one_or_none()
        if by_email:
            # Link Google identity to existing password (or other) account
            if by_email.google_sub and by_email.google_sub != identity.sub:
                raise AuthError("This email is already linked to a different Google account")
            by_email.google_sub = identity.sub
            self._ensure_google_provider(by_email)
            await db.flush()
            logger.info("google_account_linked", user_id=str(by_email.id))
            return by_email, create_access_token(str(by_email.id)), generate_csrf_token()

        user = User(
            email=identity.email,
            name=identity.name,
            hashed_password=None,
            google_sub=identity.sub,
            auth_providers=["google"],
        )
        db.add(user)
        await db.flush()
        db.add(CandidateProfile(user_id=user.id))
        db.add(UserSettings(user_id=user.id, auto_submit_enabled=False))
        await db.flush()
        logger.info("google_user_created", user_id=str(user.id))
        return user, create_access_token(str(user.id)), generate_csrf_token()

    @staticmethod
    def _ensure_google_provider(user: User) -> None:
        providers = list(user.auth_providers or [])
        if "google" not in providers:
            providers.append("google")
        if user.hashed_password and "password" not in providers:
            providers.append("password")
        user.auth_providers = providers
