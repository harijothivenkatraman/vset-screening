"""SearXNG search adapter implementing WebSearchPort."""
from __future__ import annotations

import logging
import urllib.parse
from typing import Any
import httpx

from app.application.ports.web_search_port import WebSearchPort
from app.domain.entities.discovery import SearchResult

logger = logging.getLogger(__name__)


class SearXNGSearchAdapter(WebSearchPort):
    """Adapter for querying self-hosted SearXNG JSON API via Tailscale or local network."""

    def __init__(self, base_url: str | None = None, timeout_seconds: float = 10.0) -> None:
        self._base_url = (base_url or "").rstrip("/")
        self._timeout = timeout_seconds

    async def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        if not self._base_url:
            raise ValueError("SearXNG base URL is not configured")

        if not query or not query.strip():
            return []

        search_url = f"{self._base_url}/search"
        params: dict[str, Any] = {
            "q": query.strip(),
            "format": "json",
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(search_url, params=params)
            resp.raise_for_status()
            data = resp.json()

        raw_results: list[dict[str, Any]] = data.get("results", [])
        results: list[SearchResult] = []

        for item in raw_results[:max_results]:
            url = item.get("url") or ""
            title = item.get("title") or ""
            snippet = item.get("content") or ""

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
