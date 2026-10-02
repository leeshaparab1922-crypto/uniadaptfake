"""ADR-0006, NFR-SEC-016: fixed-window rate limiting."""

from __future__ import annotations

from app.core.rate_limit import RateLimiter


class _FakeRedis:
    def __init__(self) -> None:
        self.counters: dict[str, int] = {}
        self.expired_with: dict[str, int] = {}

    def incr(self, name: str) -> int:
        self.counters[name] = self.counters.get(name, 0) + 1
        return self.counters[name]

    def expire(self, name: str, seconds: int) -> bool:
        self.expired_with[name] = seconds
        return True


def test_hit_allows_under_limit():
    fake = _FakeRedis()
    limiter = RateLimiter(fake)
    for _ in range(3):
        assert limiter.hit("k", limit=3, window_seconds=60) is True


def test_hit_blocks_over_limit():
    fake = _FakeRedis()
    limiter = RateLimiter(fake)
    for _ in range(3):
        limiter.hit("k", limit=3, window_seconds=60)
    assert limiter.hit("k", limit=3, window_seconds=60) is False


def test_expire_set_only_on_first_hit():
    fake = _FakeRedis()
    limiter = RateLimiter(fake)
    limiter.hit("k", limit=5, window_seconds=123)
    limiter.hit("k", limit=5, window_seconds=999)
    assert fake.expired_with["k"] == 123


def test_independent_keys_do_not_share_counters():
    fake = _FakeRedis()
    limiter = RateLimiter(fake)
    limiter.hit("a", limit=1, window_seconds=60)
    assert limiter.hit("b", limit=1, window_seconds=60) is True
