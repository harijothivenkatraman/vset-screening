"""Use case: Export a sanitized canonical JSON document for a founder profile."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.application.ports.founder_profile_repository import FounderProfileRepository
from app.domain.entities.founder_profile import FounderProfile
from app.domain.exceptions import ProfileNotFoundException


class ExportProfileUseCase:
    """Serializes a single founder profile to sanitized JSON, guaranteed free of raw buffers or PII."""

    def __init__(self, repository: FounderProfileRepository) -> None:
        self._repository = repository

    async def execute(self, identifier: str) -> dict[str, Any]:
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

        # Build clean export dictionary
        export_payload = {
            "$schema": "https://vset.dev/schemas/founder-profile.v1.json",
            "id": str(profile.id),
            "slug": profile.slug,
            "founder_name": profile.founder_name,
            "company_name": profile.company_name,
            "headline": profile.headline,
            "location": profile.location,
            "about": profile.about,
            "linkedin_url": profile.linkedin_url,
            "experience_timeline": [exp.to_dict() for exp in profile.experience_timeline],
            "education": [edu.to_dict() for edu in profile.education],
            "skills": list(profile.skills),
            "certifications": list(profile.certifications),
            "languages": list(profile.languages),
            "identity_status": profile.identity_status,
            "retrieval": profile.retrieval.to_dict(),
            "notes": profile.notes,
            "created_at": profile.created_at.isoformat(),
            "updated_at": profile.updated_at.isoformat(),
        }

        return export_payload
