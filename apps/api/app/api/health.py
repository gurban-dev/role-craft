"""Health and readiness probes."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine
from app.schemas import HealthOut, ReadyOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
async def health() -> HealthOut:
    return HealthOut(status="ok", version="1.0.0")


@router.get("/ready", response_model=ReadyOut)
async def ready() -> ReadyOut:
    settings = get_settings()
    details: dict[str, str] = {}
    db_ok = False
    redis_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
        details["database"] = "ok"
    except Exception as exc:
        details["database"] = str(exc)

    try:
        import redis.asyncio as redis

        client = redis.from_url(settings.redis_url)
        await client.ping()
        await client.aclose()
        redis_ok = True
        details["redis"] = "ok"
    except Exception as exc:
        details["redis"] = str(exc)

    status = "ready" if db_ok else "degraded"
    return ReadyOut(status=status, database=db_ok, redis=redis_ok, details=details)
