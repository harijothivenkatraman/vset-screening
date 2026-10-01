"""Port for public LinkedIn profile scraping."""
from __future__ import annotations
from abc import ABC, abstractmethod
from app.domain.entities.discovery import CompanyProfile, PersonProfile


class ProfileScraperPort(ABC):
    """Scrape public LinkedIn profiles (no login, no cookies)."""
    
    @abstractmethod
    async def fetch_company(self, url: str) -> CompanyProfile | None:
        """Fetch public company profile. Returns None if auth-walled or not found."""
        ...
    
    @abstractmethod
    async def fetch_person(self, url: str) -> PersonProfile | None:
        """Fetch public person profile. Returns None if auth-walled or not found."""
        ...
