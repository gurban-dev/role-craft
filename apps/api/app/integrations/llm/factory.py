"""LLM provider factory."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError
from app.integrations.llm.openai_provider import OpenAIProvider


def get_llm_provider(
    settings: Settings | None = None,
    *,
    db: AsyncSession | None = None,
) -> OpenAIProvider:
    settings = settings or get_settings()
    if settings.llm_provider == "openai":
        return OpenAIProvider(settings=settings, db=db)
    raise ConfigurationError(f"Unsupported LLM provider: {settings.llm_provider}")
