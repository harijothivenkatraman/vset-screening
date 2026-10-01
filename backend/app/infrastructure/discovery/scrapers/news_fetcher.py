"""News and press release fetcher implementing PageFetcherPort."""
from __future__ import annotations

import logging
from app.application.ports.page_fetcher_port import PageFetcherPort
from app.domain.entities.discovery import PageContent
from app.infrastructure.discovery.http.rate_limiter import HostRateLimiter
from app.infrastructure.discovery.scrapers.website_fetcher import WebsiteFetcherAdapter

logger = logging.getLogger(__name__)


class NewsFetcherAdapter(PageFetcherPort):
    """Fetches and cleans news articles and press coverage."""

    def __init__(
        self,
        rate_limiter: HostRateLimiter | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._delegate = WebsiteFetcherAdapter(
            rate_limiter=rate_limiter,
            timeout_seconds=timeout_seconds,
            check_robots=True,
        )

    async def fetch(self, url: str) -> PageContent | None:
        """Fetch news article page, ensuring article body is prioritized."""
        page = await self._delegate.fetch(url)
        if page is None:
            return None

        return page
