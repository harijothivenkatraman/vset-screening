"""Per-host rate limiter for polite and resilient web scraping."""
from __future__ import annotations

import asyncio
import time
import urllib.parse
from typing import Final


class HostRateLimiter:
    """Enforces minimum intervals between consecutive HTTP requests to the same host."""

    def __init__(self, min_interval_seconds: float = 3.0, max_tracked_hosts: int = 1000) -> None:
        self._min_interval = min_interval_seconds
        self._max_tracked_hosts = max_tracked_hosts
        self._last_access: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    def _extract_host(self, url_or_host: str) -> str:
        if "://" in url_or_host:
            parsed = urllib.parse.urlsplit(url_or_host)
            host = parsed.hostname or url_or_host
        else:
            host = url_or_host.split("/")[0]
        return host.strip().lower()

    async def _get_host_lock(self, host: str) -> asyncio.Lock:
        async with self._global_lock:
            if host not in self._locks:
                # Evict oldest if capacity exceeded
                if len(self._locks) >= self._max_tracked_hosts:
                    oldest_host = min(self._last_access, key=lambda h: self._last_access.get(h, 0.0), default=None)
                    if oldest_host:
                        self._last_access.pop(oldest_host, None)
                        self._locks.pop(oldest_host, None)
                self._locks[host] = asyncio.Lock()
            return self._locks[host]

    async def wait(self, url_or_host: str) -> float:
        """Wait if necessary before allowing a request to the target host.

        Returns:
            The number of seconds waited (0.0 if no delay was required).
        """
        host = self._extract_host(url_or_host)
        lock = await self._get_host_lock(host)

        async with lock:
            now = time.monotonic()
            last_time = self._last_access.get(host, 0.0)
            elapsed = now - last_time
            delay = max(0.0, self._min_interval - elapsed)

            if delay > 0.0:
                await asyncio.sleep(delay)
                self._last_access[host] = time.monotonic()
            else:
                self._last_access[host] = now

            return delay
