"""OpenAI structured-output provider."""

from __future__ import annotations

import time
from typing import TypeVar
from uuid import UUID

from openai import AsyncOpenAI
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError
from app.core.logging import correlation_id_var, get_logger
from app.models import AiUsage

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

# Approximate USD per 1M tokens for common models (input, output)
_MODEL_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
}


def _estimate_cost(model: str, input_tokens: int | None, output_tokens: int | None) -> float | None:
    if input_tokens is None and output_tokens is None:
        return None
    pricing = _MODEL_PRICING.get(model)
    if not pricing:
        # Fallback heuristic
        pricing = (1.0, 3.0)
    inp, out = pricing
    return round(
        ((input_tokens or 0) * inp + (output_tokens or 0) * out) / 1_000_000,
        6,
    )


class OpenAIProvider:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        db: AsyncSession | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.db = db
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        if not self.settings.openai_api_key:
            raise ConfigurationError(
                "OPENAI_API_KEY is not configured. Set it in the environment to use AI features."
            )
        if self._client is None:
            kwargs: dict = {"api_key": self.settings.openai_api_key}
            if self.settings.openai_base_url:
                kwargs["base_url"] = self.settings.openai_base_url
            self._client = AsyncOpenAI(**kwargs, timeout=self.settings.llm_timeout_seconds)
        return self._client

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
        client = self._get_client()
        model_name = model or self.settings.openai_model
        started = time.perf_counter()
        success = False
        input_tokens: int | None = None
        output_tokens: int | None = None
        try:
            response = await client.beta.chat.completions.parse(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a careful assistant for job applications. "
                            "Never invent facts about a candidate. "
                            "Return only data matching the requested schema."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format=schema,
            )
            parsed = response.choices[0].message.parsed
            if parsed is None:
                refusal = response.choices[0].message.refusal
                raise RuntimeError(refusal or "OpenAI returned empty structured response")
            usage = response.usage
            if usage:
                input_tokens = usage.prompt_tokens
                output_tokens = usage.completion_tokens
            success = True
            return parsed
        finally:
            latency_ms = int((time.perf_counter() - started) * 1000)
            cost = _estimate_cost(model_name, input_tokens, output_tokens)
            logger.info(
                "llm_generate",
                provider="openai",
                model=model_name,
                operation=operation or schema.__name__,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost_usd=cost,
                success=success,
            )
            if self.db is not None:
                uid: UUID | None = None
                if user_id:
                    try:
                        uid = UUID(user_id)
                    except ValueError:
                        uid = None
                self.db.add(
                    AiUsage(
                        user_id=uid,
                        provider="openai",
                        model=model_name,
                        operation=operation or schema.__name__,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        estimated_cost_usd=cost,
                        latency_ms=latency_ms,
                        correlation_id=correlation_id or correlation_id_var.get() or None,
                        success=success,
                    )
                )
                await self.db.flush()
