"""Port interface for founder profile persistence."""
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.founder_profile import FounderProfile


class FounderProfileRepository(ABC):
    """Abstract storage port for FounderProfile aggregates."""

    @abstractmethod
    async def save(self, profile: FounderProfile) -> FounderProfile:
        """Persist or update a founder profile."""
        ...

    @abstractmethod
    async def find_by_id(self, profile_id: UUID) -> FounderProfile | None:
        """Look up a profile by its primary UUID."""
        ...

    @abstractmethod
    async def find_by_slug(self, slug: str) -> FounderProfile | None:
        """Look up a profile by its unique URL slug."""
        ...

    @abstractmethod
    async def find_by_name_and_company(
        self, founder_name: str, company_name: str | None
    ) -> FounderProfile | None:
        """Look up an existing profile with matching name and company (case-insensitive)."""
        ...

    @abstractmethod
    async def list_all(
        self,
        search: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[FounderProfile]:
        """List profiles ordered by updated_at descending with optional search/status filters."""
        ...

    @abstractmethod
    async def count(
        self,
        search: str | None = None,
        status: str | None = None,
    ) -> int:
        """Count total profiles matching the search/status filters."""
        ...

    @abstractmethod
    async def delete(self, profile_id: UUID) -> bool:
        """Permanently delete a founder profile by its ID."""
        ...
