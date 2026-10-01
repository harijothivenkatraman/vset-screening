"""Unit tests for CircuitBreaker."""
from __future__ import annotations

import asyncio
import pytest

from app.infrastructure.discovery.search.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitBreaker:
    async def test_successful_execution(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=2)

        async def _success() -> str:
            return "ok"

        res = await cb.execute_with_retry(_success)
        assert res == "ok"
        assert cb.state == CircuitState.CLOSED
        assert cb.consecutive_failures == 0

    async def test_opens_after_consecutive_failures(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=2, max_retries=0)

        async def _failing() -> str:
            raise RuntimeError("provider down")

        # Failure 1
        with pytest.raises(RuntimeError):
            await cb.execute_with_retry(_failing)
        assert cb.consecutive_failures == 1
        assert cb.state == CircuitState.CLOSED

        # Failure 2 -> Threshold reached -> OPEN
        with pytest.raises(RuntimeError):
            await cb.execute_with_retry(_failing)
        assert cb.consecutive_failures == 2
        assert cb.state == CircuitState.OPEN

        # Call rejected immediately when OPEN
        assert not await cb.can_execute()
        with pytest.raises(RuntimeError, match="is OPEN"):
            await cb.execute_with_retry(_failing)

    async def test_recovery_to_half_open_then_closed(self) -> None:
        cb = CircuitBreaker(
            name="test",
            failure_threshold=1,
            recovery_timeout_seconds=0.05,
            max_retries=0,
        )

        async def _fail() -> str:
            raise RuntimeError("fail")

        async def _succeed() -> str:
            return "recovered"

        with pytest.raises(RuntimeError):
            await cb.execute_with_retry(_fail)
        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.06)
        assert await cb.can_execute()
        assert cb.state == CircuitState.HALF_OPEN

        # Next successful call resets to CLOSED
        res = await cb.execute_with_retry(_succeed)
        assert res == "recovered"
        assert cb.state == CircuitState.CLOSED
        assert cb.consecutive_failures == 0
