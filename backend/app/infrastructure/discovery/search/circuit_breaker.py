"""Circuit breaker with jittered exponential backoff for external search providers."""
from __future__ import annotations

import asyncio
import logging
import random
import time
from enum import Enum
from typing import Any, Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Manages failure detection and temporary circuit opening for an external adapter."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout_seconds: float = 300.0,
        max_retries: int = 2,
        base_delay_seconds: float = 0.5,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout_seconds
        self.max_retries = max_retries
        self.base_delay = base_delay_seconds

        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.last_failure_time: float = 0.0
        self._lock = asyncio.Lock()

    async def can_execute(self) -> bool:
        """Check whether execution is currently allowed through the circuit breaker."""
        async with self._lock:
            now = time.monotonic()
            if self.state == CircuitState.OPEN:
                if now - self.last_failure_time >= self.recovery_timeout:
                    logger.info("Circuit breaker '%s' entering HALF_OPEN state for trial.", self.name)
                    self.state = CircuitState.HALF_OPEN
                    return True
                return False
            return True

    async def record_success(self) -> None:
        async with self._lock:
            if self.state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
                logger.info("Circuit breaker '%s' recovered to CLOSED state.", self.name)
            self.state = CircuitState.CLOSED
            self.consecutive_failures = 0

    async def record_failure(self) -> None:
        async with self._lock:
            self.consecutive_failures += 1
            self.last_failure_time = time.monotonic()
            if self.consecutive_failures >= self.failure_threshold:
                if self.state != CircuitState.OPEN:
                    logger.warning(
                        "Circuit breaker '%s' opened after %d failures. Skipping calls for %.1fs.",
                        self.name,
                        self.consecutive_failures,
                        self.recovery_timeout,
                    )
                self.state = CircuitState.OPEN

    async def execute_with_retry(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute async function with circuit breaker check and jittered retries."""
        if not await self.can_execute():
            raise RuntimeError(f"Circuit breaker for provider '{self.name}' is OPEN")

        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                await self.record_success()
                return result
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "Provider '%s' failed attempt %d/%d: %s",
                    self.name,
                    attempt + 1,
                    self.max_retries + 1,
                    exc,
                )
                if attempt < self.max_retries:
                    jitter = random.uniform(0.0, 1.0)
                    delay = (self.base_delay * (2 ** attempt)) + jitter
                    await asyncio.sleep(delay)

        await self.record_failure()
        raise last_exc or RuntimeError(f"Provider '{self.name}' failed after retries")
