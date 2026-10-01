"""Fallback composite search adapter implementing WebSearchPort."""
from __future__ import annotations

import logging
from typing import Sequence

from app.application.ports.web_search_port import WebSearchPort
from app.domain.entities.discovery import SearchResult
from app.domain.exceptions import SearchUnavailableError
from app.infrastructure.discovery.search.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class FallbackSearchAdapter(WebSearchPort):
    """Composite adapter that executes search queries across an ordered sequence of search providers.

    Each provider is protected by its own CircuitBreaker and jittered retry logic.
    If all configured providers fail or are unavailable, raises SearchUnavailableError.
    """

    def __init__(
        self,
        providers: Sequence[tuple[str, WebSearchPort]],
        circuit_breakers: dict[str, CircuitBreaker] | None = None,
    ) -> None:
        self._providers = list(providers)
        self._circuit_breakers = circuit_breakers or {
            name: CircuitBreaker(name=name) for name, _ in self._providers
        }

    async def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        if not self._providers:
            raise SearchUnavailableError([])

        providers_tried: list[str] = []
        last_error: Exception | None = None

        for name, provider in self._providers:
            cb = self._circuit_breakers.get(name)
            if cb is None:
                cb = CircuitBreaker(name=name)
                self._circuit_breakers[name] = cb

            providers_tried.append(name)

            if not await cb.can_execute():
                logger.warning("Provider '%s' skipped because circuit is OPEN.", name)
                continue

            try:
                results = await cb.execute_with_retry(
                    provider.search,
                    query,
                    max_results=max_results,
                )
                return results
            except Exception as exc:
                last_error = exc
                logger.warning("Provider '%s' failed for query '%s': %s", name, query, exc)

        logger.error(
            "All search providers failed for query '%s'. Providers tried: %s. Last error: %s",
            query,
            providers_tried,
            last_error,
        )
        raise SearchUnavailableError(providers_tried)
