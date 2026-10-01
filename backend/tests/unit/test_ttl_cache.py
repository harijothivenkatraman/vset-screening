"""Unit tests for InMemoryTtlCache."""
from __future__ import annotations

import asyncio
import pytest

from app.infrastructure.discovery.cache.ttl_cache import InMemoryTtlCache


class TestInMemoryTtlCache:
    async def test_set_and_get(self) -> None:
        cache = InMemoryTtlCache(default_ttl_seconds=60)
        await cache.set("k1", "v1")
        val = await cache.get("k1")
        assert val == "v1"

    async def test_missing_key_returns_none(self) -> None:
        cache = InMemoryTtlCache()
        assert await cache.get("missing") is None

    async def test_expiry(self) -> None:
        cache = InMemoryTtlCache(default_ttl_seconds=0)  # expires immediately
        await cache.set("k2", "v2", ttl_seconds=0)
        await asyncio.sleep(0.01)
        assert await cache.get("k2") is None

    async def test_delete(self) -> None:
        cache = InMemoryTtlCache()
        await cache.set("k3", "v3")
        await cache.delete("k3")
        assert await cache.get("k3") is None

    async def test_max_size_eviction(self) -> None:
        cache = InMemoryTtlCache(default_ttl_seconds=60, max_size=2)
        await cache.set("k1", "v1")
        await cache.set("k2", "v2")
        await cache.set("k3", "v3")  # should evict one item

        remaining = [
            k for k in ["k1", "k2", "k3"]
            if await cache.get(k) is not None
        ]
        assert len(remaining) <= 2
