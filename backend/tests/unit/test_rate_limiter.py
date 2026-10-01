"""Unit tests for host rate limiter."""
from __future__ import annotations

import asyncio
import time
import pytest

from app.infrastructure.discovery.http.rate_limiter import HostRateLimiter


class TestHostRateLimiter:
    async def test_first_call_no_delay(self) -> None:
        limiter = HostRateLimiter(min_interval_seconds=0.1)
        delay = await limiter.wait("https://example.com/page1")
        assert delay == 0.0

    async def test_second_call_same_host_delayed(self) -> None:
        limiter = HostRateLimiter(min_interval_seconds=0.1)
        await limiter.wait("https://example.com/page1")
        t0 = time.monotonic()
        delay = await limiter.wait("https://example.com/page2")
        elapsed = time.monotonic() - t0
        assert delay > 0.0
        assert elapsed >= 0.08  # Account for timer resolution

    async def test_different_hosts_not_delayed(self) -> None:
        limiter = HostRateLimiter(min_interval_seconds=0.5)
        await limiter.wait("https://host-a.com/page")
        t0 = time.monotonic()
        delay = await limiter.wait("https://host-b.com/page")
        elapsed = time.monotonic() - t0
        assert delay == 0.0
        assert elapsed < 0.2
