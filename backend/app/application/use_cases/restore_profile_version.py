"""Use case: Restore a founder profile to its previous version snapshot."""
from __future__ import annotations

from uuid import UUID

from app.application.ports.founder_profile_repository import FounderProfileRepository
from app.domain.entities.founder_profile import FounderProfile
from app.domain.exceptions import NoPreviousVersionException, ProfileNotFoundException


class RestoreProfileVersionUseCase:
    """Restores the single previous version saved before an explicit user update."""

    def __init__(self, repository: FounderProfileRepository) -> None:
        self._repository = repository

    async def execute(self, identifier: str) -> FounderProfile:
        clean_id = identifier.strip()
        profile: FounderProfile | None = None

        try:
            val_uuid = UUID(clean_id)
            profile = await self._repository.find_by_id(val_uuid)
        except ValueError:
            pass

        if not profile:
            profile = await self._repository.find_by_slug(clean_id)

        if not profile:
            raise ProfileNotFoundException(clean_id)

        if not profile.previous_version:
            raise NoPreviousVersionException(clean_id)

        # Restore from snapshot
        profile.restore_from_snapshot(profile.previous_version)
        return await self._repository.save(profile)
