"""Auth routes."""

from __future__ import annotations

import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, Query, Response
from fastapi.responses import RedirectResponse

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.exceptions import AppError, ConfigurationError
from app.core.logging import get_logger
from app.schemas import LoginRequest, RegisterRequest, UserOut
from app.services.auth_service import AuthService
from app.services.google_oauth_service import OAUTH_STATE_COOKIE, GoogleOAuthService

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)


def _set_auth_cookies(response: Response, token: str, csrf: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )


def _clear_oauth_state_cookie(response: Response) -> None:
    response.delete_cookie(OAUTH_STATE_COOKIE, path="/")


def _login_error_redirect(reason: str = "google_auth_failed") -> RedirectResponse:
    settings = get_settings()
    url = f"{settings.web_app_url.rstrip('/')}/login?{urlencode({'error': reason})}"
    response = RedirectResponse(url=url, status_code=302)
    _clear_oauth_state_cookie(response)
    return response


@router.post("/register", response_model=UserOut)
async def register(data: RegisterRequest, db: DbSession, response: Response) -> UserOut:
    user, token, csrf = await AuthService(db).register(data)
    _set_auth_cookies(response, token, csrf)
    return UserOut.model_validate(user)


@router.post("/login", response_model=UserOut)
async def login(data: LoginRequest, db: DbSession, response: Response) -> UserOut:
    user, token, csrf = await AuthService(db).login(data)
    _set_auth_cookies(response, token, csrf)
    return UserOut.model_validate(user)


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    settings = get_settings()
    response.delete_cookie(settings.cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")
    return {"status": "ok"}


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.get("/google")
async def google_oauth_start() -> RedirectResponse:
    settings = get_settings()
    state = secrets.token_urlsafe(32)
    try:
        auth_url = GoogleOAuthService(settings=settings).authorization_url(state)
    except ConfigurationError:
        return _login_error_redirect("google_not_configured")
    except Exception as exc:
        logger.warning("google_oauth_start_failed", error=str(exc))
        return _login_error_redirect()

    response = RedirectResponse(url=auth_url, status_code=302)
    response.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=state,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=600,
        path="/",
    )
    return response


@router.get("/google/callback")
async def google_oauth_callback(
    db: DbSession,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    oauth_state: str | None = Cookie(default=None, alias=OAUTH_STATE_COOKIE),
) -> RedirectResponse:
    settings = get_settings()
    if error:
        logger.info("google_oauth_denied", error=error)
        return _login_error_redirect()
    if not code or not state or not oauth_state or state != oauth_state:
        return _login_error_redirect()

    try:
        svc = GoogleOAuthService(db, settings)
        identity = await svc.exchange_code(code)
        _user, token, csrf = await svc.login_or_register(identity)
    except ConfigurationError:
        return _login_error_redirect("google_not_configured")
    except AppError as exc:
        logger.info("google_oauth_failed", error=exc.message, code=exc.code)
        return _login_error_redirect()
    except Exception as exc:
        logger.warning("google_oauth_unexpected", error=str(exc))
        return _login_error_redirect()

    redirect = RedirectResponse(
        url=f"{settings.web_app_url.rstrip('/')}/dashboard",
        status_code=302,
    )
    _set_auth_cookies(redirect, token, csrf)
    _clear_oauth_state_cookie(redirect)
    return redirect
