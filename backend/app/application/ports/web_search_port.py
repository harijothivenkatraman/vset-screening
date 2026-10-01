"""Port for web search."""
from __future__ import annotations
from abc import ABC, abstractmethod
from app.domain.entities.discovery import SearchResult


class WebSearchPort(ABC):
    """Search the web for a query. Returns ranked results."""
    
    @abstractmethod
    async def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        """Search and return results. Raises SearchUnavailableError if all providers fail."""
        ...
