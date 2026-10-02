"""Single shared Redis fixed-window rate-limit helper (ADR-0006, NFR-SEC-016).

One `RateLimiter` implementation is used by every rate-limited endpoint
(login, invitation consumption, password-reset consumption). Limits and
window lengths always come from `app.core.config.settings`, never
hard-coded per call site.

`RateLimiter` depends only on an object exposing `incr`/`expire` (the
subset of the `redis.Redis` API it needs), so tests can inject a small
in-memory fake instead of a live Redis server without adding a new
dependency (see `backend/tests/unit/test_rate_limit.py`).
"""

from __future__ import annotations

from typing import Protocol

from app.core.config import settings


class RedisLike(Protocol):
    def incr(self, name: str) -> int: ...

    def expire(self, name: str, seconds: int) -> bool: ...


class RateLimiter:
    def __init__(self, client: RedisLike) -> None:
        self._client = client

    def hit(self, key: str, *, limit: int, window_seconds: int) -> bool:
        """Increments the fixed-window counter for `key`.

        Returns True if this request is within the limit for the current
        window, False if the limit has already been reached.
        """
        current = self._client.incr(key)
        if current == 1:
            self._client.expire(key, window_seconds)
        return current <= limit


_client: RedisLike | None = None


def get_redis_client() -> RedisLike:
    global _client
    if _client is None:
        import redis

        _client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _client


def get_rate_limiter() -> RateLimiter:
    return RateLimiter(get_redis_client())
