"""LLM provider protocol."""

from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(Protocol):
    """Async structured-output LLM interface."""

    async def generate(
        self,
        prompt: str,
        schema: type[T],
        model: str | None = None,
        *,
        operation: str = "",
        user_id: str | None = None,
        correlation_id: str | None = None,
    ) -> T:
        """Generate a structured response matching ``schema``."""
        ...
