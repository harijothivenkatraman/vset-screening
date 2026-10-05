"""DuckDuckGo web search adapter implementing WebSearchPort."""
from __future__ import annotations

import asyncio
import logging
import urllib.parse
from app.application.ports.web_search_port import WebSearchPort
from app.domain.entities.discovery import SearchResult

logger = logging.getLogger(__name__)


class DuckDuckGoSearchAdapter(WebSearchPort):
    """Adapter for querying DuckDuckGo public search without API keys."""

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._timeout = timeout_seconds

    async def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        if not query or not query.strip():
            return []

        def _sync_search() -> list[dict[str, str]]:
            try:
                from duckduckgo_search import DDGS

                with DDGS(timeout=int(self._timeout)) as ddgs:
                    raw_results = list(ddgs.text(query.strip(), max_results=max_results))
                    return raw_results
            except Exception as e:
                logger.warning("DuckDuckGo search error for query '%s': %s", query, e)
                raise

        raw_results = await asyncio.to_thread(_sync_search)

        results: list[SearchResult] = []
        for item in raw_results:
            url = item.get("href") or item.get("url") or ""
            title = item.get("title") or ""
            snippet = item.get("body") or item.get("snippet") or ""

            if not url:
                continue

            parsed = urllib.parse.urlsplit(url)
            domain = parsed.hostname or url

            results.append(
                SearchResult(
                    url=url,
                    title=title,
                    snippet=snippet,
                    domain=domain,
                )
            )

        return results
