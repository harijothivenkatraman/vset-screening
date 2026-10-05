"""Use case: Guarded deletion of a founder profile."""
from __future__ import annotations

from uuid import UUID

from app.application.ports.founder_profile_repository import FounderProfileRepository
from app.domain.entities.founder_profile import FounderProfile
from app.domain.exceptions import InvalidEvidenceException, ProfileNotFoundException


class DeleteProfileUseCase:
    """Guarded deletion requiring slug confirmation."""

    def __init__(self, repository: FounderProfileRepository) -> None:
        self._repository = repository

    async def execute(self, identifier: str, confirm: str) -> bool:
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

        if confirm.strip().lower() != profile.slug.lower():
            raise InvalidEvidenceException(
                f"Confirmation slug '{confirm}' does not match target profile slug '{profile.slug}'."
            )

        return await self._repository.delete(profile.id)
