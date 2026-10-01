"""Port for fetching and extracting web page content."""
from __future__ import annotations
from abc import ABC, abstractmethod
from app.domain.entities.discovery import PageContent


class PageFetcherPort(ABC):
    """Fetch and extract text from web pages."""
    
    @abstractmethod
    async def fetch(self, url: str) -> PageContent | None:
        """Fetch page, extract text. Returns None on failure. Respects robots.txt."""
        ...
