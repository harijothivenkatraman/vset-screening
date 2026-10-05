"""Use case: Get a single founder profile by UUID or slug."""
from __future__ import annotations

from uuid import UUID

from app.application.ports.founder_profile_repository import FounderProfileRepository
from app.domain.entities.founder_profile import FounderProfile
from app.domain.exceptions import ProfileNotFoundException


class GetProfileUseCase:
    """Retrieves a single founder profile with zero network calls."""

    def __init__(self, repository: FounderProfileRepository) -> None:
        self._repository = repository

    async def execute(self, identifier: str) -> FounderProfile:
        clean_id = identifier.strip()
        profile: FounderProfile | None = None

        # Try parsing as UUID
        try:
            val_uuid = UUID(clean_id)
            profile = await self._repository.find_by_id(val_uuid)
        except ValueError:
            pass

        # If not found by UUID, try by slug
        if not profile:
            profile = await self._repository.find_by_slug(clean_id)

        if not profile:
            raise ProfileNotFoundException(clean_id)

        return profile
