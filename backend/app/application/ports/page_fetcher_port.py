"""Port for fetching web page content."""
from __future__ import annotations

from abc import ABC, abstractmethod
from app.domain.entities.discovery import PageContent, SourceDiagnostic


class PageFetcherPort(ABC):
    """Fetch and extract content from web pages."""

    @abstractmethod
    async def fetch(self, url: str) -> PageContent | None:
        """Fetch page, extract text and links. Returns None on failure."""
        ...

    async def fetch_with_diagnostic(self, url: str) -> tuple[PageContent | None, SourceDiagnostic]:
        """Fetch page and return both content and diagnostic metadata."""
        content = await self.fetch(url)
        if content:
            fields: list[str] = []
            if content.title:
                fields.append("title")
            if content.description:
                fields.append("description")
            if content.text:
                fields.append("text")
            if content.links:
                fields.append("links")
            return content, SourceDiagnostic(
                url=url,
                outcome="ok",
                bytes_fetched=len(content.text.encode("utf-8")),
                fields_extracted=fields,
            )
        return None, SourceDiagnostic(url=url, outcome="empty_text", bytes_fetched=0)
