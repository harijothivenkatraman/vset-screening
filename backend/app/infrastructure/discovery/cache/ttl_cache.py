"""In-memory TTL cache implementation of CachePort."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from app.application.ports.cache_port import CachePort


class InMemoryTtlCache(CachePort):
    """In-memory key-value cache with per-key TTL and maximum capacity eviction."""

    def __init__(self, default_ttl_seconds: int = 3600, max_size: int = 500) -> None:
        self._default_ttl = default_ttl_seconds
        self._max_size = max_size
        self._store: dict[str, tuple[Any, float]] = {}  # key -> (value, expires_at)
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                self._store.pop(key, None)
                return None
            return value

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        expires_at = time.monotonic() + ttl

        async with self._lock:
            # Purge expired or evict oldest if at capacity
            if len(self._store) >= self._max_size and key not in self._store:
                self._evict_expired_or_oldest()
            self._store[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    def _evict_expired_or_oldest(self) -> None:
        now = time.monotonic()
        expired = [k for k, (_, exp) in self._store.items() if now > exp]
        for k in expired:
            self._store.pop(k, None)

        if len(self._store) >= self._max_size:
            # Evict earliest expiring item
            oldest = min(self._store.keys(), key=lambda k: self._store[k][1])
            self._store.pop(oldest, None)
