"""Async database engine and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine, _session_factory
    if _engine is None:
        settings = get_settings()
        kwargs: dict = {"pool_pre_ping": True, "echo": settings.debug}
        if settings.database_url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        else:
            kwargs["pool_size"] = 10
            kwargs["max_overflow"] = 20
        _engine = create_async_engine(settings.database_url, **kwargs)
        _session_factory = async_sessionmaker(
            _engine, class_=AsyncSession, expire_on_commit=False
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    get_engine()
    assert _session_factory is not None
    return _session_factory


class _EngineProxy:
    """Lazy proxy so importing this module does not require a live DB."""

    def connect(self):  # type: ignore[no-untyped-def]
        return get_engine().connect()

    def begin(self):  # type: ignore[no-untyped-def]
        return get_engine().begin()

    async def dispose(self) -> None:
        eng = get_engine()
        await eng.dispose()
        reset_engine()


engine = _EngineProxy()
AsyncSessionLocal = get_session_factory  # callable factory for callers expecting a maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def reset_engine() -> None:
    """Reset cached engine (for tests)."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None
