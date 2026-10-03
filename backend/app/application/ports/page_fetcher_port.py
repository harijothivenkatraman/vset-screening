"""Port for fetching and extracting web page content."""
from __future__ import annotations
from abc import ABC, abstractmethod
from app.domain.entities.discovery import PageContent, SourceDiagnostic


class PageFetcherPort(ABC):
    """Fetch and extract text from web pages."""
    
    @abstractmethod
    async def fetch(self, url: str) -> PageContent | None:
        """Fetch page, extract text. Returns None on failure. Respects robots.txt."""
        ...

    async def fetch_with_diagnostic(self, url: str) -> tuple[PageContent | None, SourceDiagnostic]:
        """Fetch page and return both content and diagnostic metadata."""
        content = await self.fetch(url)
        if content:
            fields = []
            if content.title:
                fields.append("title")
            if content.description:
                fields.append("description")
            if content.text:
                fields.append("text")
            if content.og_tags:
                fields.append("og_tags")
            return content, SourceDiagnostic(
                url=url,
                outcome="ok",
                bytes_fetched=len(content.text.encode("utf-8")),
                fields_extracted=fields,
            )
        return None, SourceDiagnostic(url=url, outcome="empty_text", bytes_fetched=0)

    async def fetch_sitemap_urls(self, base_url: str) -> list[str]:
        """Fetch candidate URLs from sitemap.xml. Default returns empty list."""
        return []

    async def is_allowed(self, url: str) -> bool:
        """Check if URL is permitted by robots.txt before fetching."""
        return True
