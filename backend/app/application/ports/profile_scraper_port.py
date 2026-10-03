"""Port for public LinkedIn profile scraping."""
from __future__ import annotations
from abc import ABC, abstractmethod
from app.domain.entities.discovery import CompanyProfile, PersonProfile, SourceDiagnostic


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

    async def fetch_company_with_diagnostic(self, url: str) -> tuple[CompanyProfile | None, SourceDiagnostic]:
        """Fetch company profile and return diagnostic metadata."""
        profile = await self.fetch_company(url)
        if not profile:
            return None, SourceDiagnostic(url=url, outcome="empty_text", bytes_fetched=0)
        if profile.is_auth_walled:
            return profile, SourceDiagnostic(url=url, outcome="auth_wall", bytes_fetched=0)
        fields = [k for k in ("name", "description", "industry", "headquarters", "website", "founded_year") if getattr(profile, k, None)]
        return profile, SourceDiagnostic(url=url, outcome="ok", bytes_fetched=0, fields_extracted=fields)

    async def fetch_person_with_diagnostic(self, url: str) -> tuple[PersonProfile | None, SourceDiagnostic]:
        """Fetch person profile and return diagnostic metadata."""
        profile = await self.fetch_person(url)
        if not profile:
            return None, SourceDiagnostic(url=url, outcome="empty_text", bytes_fetched=0)
        if profile.is_auth_walled:
            return profile, SourceDiagnostic(url=url, outcome="auth_wall", bytes_fetched=0)
        fields = [k for k in ("name", "headline", "location", "summary") if getattr(profile, k, None)]
        return profile, SourceDiagnostic(url=url, outcome="ok", bytes_fetched=0, fields_extracted=fields)
