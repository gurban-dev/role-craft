"""Security helpers: password hashing, JWT, CSRF, encryption."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from cryptography.fernet import Fernet
from passlib.context import CryptContext

from app.core.config import Settings, get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(
    subject: str,
    *,
    settings: Settings | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    settings = settings or get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "exp": expire, "iat": datetime.now(UTC)}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, *, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def _fernet(settings: Settings | None = None) -> Fernet:
    settings = settings or get_settings()
    if settings.encryption_key:
        key = settings.encryption_key
        if isinstance(key, str):
            key = key.encode()
        return Fernet(key)
    # Derive a stable Fernet key from secret_key (32 url-safe base64-encoded bytes)
    digest = hashlib.sha256(settings.secret_key.encode()).digest()
    import base64

    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_value(value: str, *, settings: Settings | None = None) -> str:
    return _fernet(settings).encrypt(value.encode()).decode()


def decrypt_value(token: str, *, settings: Settings | None = None) -> str:
    return _fernet(settings).decrypt(token.encode()).decode()
