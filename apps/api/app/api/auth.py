"""Auth routes."""

from __future__ import annotations

from fastapi import APIRouter, Response

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.schemas import LoginRequest, RegisterRequest, UserOut
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


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
