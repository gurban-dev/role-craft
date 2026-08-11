"""Simple rate limiting (Redis when available, in-memory fallback)."""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError
from app.core.logging import get_logger

logger = get_logger(__name__)

_memory_buckets: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


class RateLimitService:
    """Sliding-window rate limiter keyed by scope + identity."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._redis = None

    def _get_redis(self):  # type: ignore[no-untyped-def]
        if self._redis is not None:
            return self._redis
        try:
            import redis

            client = redis.from_url(self.settings.redis_url, socket_connect_timeout=0.5)
            client.ping()
            self._redis = client
            return client
        except Exception:
            self._redis = False
            return None

    def check(self, *, scope: str, identity: str, limit: int, window_seconds: int = 3600) -> None:
        if limit <= 0:
            return
        key = f"rl:{scope}:{identity}"
        now = time.time()
        client = self._get_redis()
        if client:
            try:
                pipe = client.pipeline()
                pipe.zremrangebyscore(key, 0, now - window_seconds)
                pipe.zcard(key)
                pipe.zadd(key, {str(now): now})
                pipe.expire(key, window_seconds)
                results = pipe.execute()
                count = int(results[1])
                if count >= limit:
                    raise ConflictError(f"Rate limit exceeded for {scope} ({limit}/{window_seconds}s)")
                return
            except ConflictError:
                raise
            except Exception as exc:
                logger.warning("rate_limit_redis_fallback", error=str(exc))

        with _lock:
            bucket = _memory_buckets[key]
            cutoff = now - window_seconds
            _memory_buckets[key] = [t for t in bucket if t >= cutoff]
            if len(_memory_buckets[key]) >= limit:
                raise ConflictError(f"Rate limit exceeded for {scope} ({limit}/{window_seconds}s)")
            _memory_buckets[key].append(now)

    def check_job_discovery(self, user_id: str) -> None:
        self.check(
            scope="job_discovery",
            identity=user_id,
            limit=self.settings.rate_limit_job_discovery_per_hour,
        )

    def check_llm(self, user_id: str) -> None:
        self.check(
            scope="llm",
            identity=user_id,
            limit=self.settings.rate_limit_llm_per_hour,
        )

    def check_browser(self, user_id: str) -> None:
        self.check(
            scope="browser",
            identity=user_id,
            limit=self.settings.rate_limit_browser_per_hour,
        )

    def check_research(self, user_id: str) -> None:
        self.check(
            scope="research",
            identity=user_id,
            limit=self.settings.rate_limit_research_per_hour,
        )


def reset_memory_rate_limits() -> None:
    with _lock:
        _memory_buckets.clear()
