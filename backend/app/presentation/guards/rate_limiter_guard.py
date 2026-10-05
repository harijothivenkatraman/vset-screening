"""Rate limiter guard for sensitive/expensive endpoints (/fetch and /upload-pdf).

Enforces:
- Sliding-window rate limiting per client IP (default: 10 req/min).
- Global sliding-window rate limiting across all clients (default: 30 req/min).
- Early 429 rejection with Retry-After header.
- Test inspection and reset utilities.
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import DefaultDict

from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    """Sliding-window rate limiter enforcing per-IP and global thresholds."""

    def __init__(
        self,
        ip_limit: int = 10,
        global_limit: int = 30,
        window_seconds: float = 60.0,
    ) -> None:
        self.ip_limit = ip_limit
        self.global_limit = global_limit
        self.window_seconds = window_seconds
        self._ip_history: DefaultDict[str, list[float]] = defaultdict(list)
        self._global_history: list[float] = []

    def reset(self) -> None:
        """Clear all rate limit history (useful for test isolation)."""
        self._ip_history.clear()
        self._global_history.clear()

    def check(self, request: Request) -> None:
        now = time.monotonic()
        cutoff = now - self.window_seconds

        # 1. Check Global Limit
        self._global_history = [t for t in self._global_history if t > cutoff]
        if len(self._global_history) >= self.global_limit:
            oldest = self._global_history[0]
            retry_after = max(1, int(self.window_seconds - (now - oldest)))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Global rate limit exceeded for sensitive endpoints. Please wait before retrying.",
                headers={"Retry-After": str(retry_after)},
            )

        # 2. Extract Client IP
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        elif request.client and request.client.host:
            client_ip = request.client.host.strip()
        else:
            client_ip = "unknown"

        # 3. Check Per-IP Limit
        ip_records = [t for t in self._ip_history[client_ip] if t > cutoff]
        if len(ip_records) >= self.ip_limit:
            oldest = ip_records[0]
            retry_after = max(1, int(self.window_seconds - (now - oldest)))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for IP {client_ip}. Please wait before retrying.",
                headers={"Retry-After": str(retry_after)},
            )

        # Record this request
        ip_records.append(now)
        self._ip_history[client_ip] = ip_records
        self._global_history.append(now)


# Module-level default rate limiter
founder_action_limiter = SlidingWindowRateLimiter(ip_limit=10, global_limit=30, window_seconds=60.0)


async def rate_limit_founder_action(request: Request) -> None:
    """FastAPI dependency to rate-limit /fetch and /upload-pdf."""
    founder_action_limiter.check(request)
