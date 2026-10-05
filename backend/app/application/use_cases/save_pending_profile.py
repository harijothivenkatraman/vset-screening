"""Use case: Save a placeholder profile as 'pending_evidence' by explicit operator action.

Implements Requirement 9:
Explicit operator action only for blocked/not-found fetch results or manual placeholders.
Never creates empty rows from failed automated attempts automatically.
"""
from __future__ import annotations

from uuid import uuid4

from app.application.ports.founder_profile_repository import FounderProfileRepository
from app.application.use_cases.add_from_evidence import generate_founder_slug
from app.domain.entities.founder_profile import (
    FounderProfile,
    RetrievalPayload,
)
from app.domain.exceptions import DuplicateProfileException, InvalidEvidenceException


class SavePendingProfileUseCase:
    """Explicitly persists a founder profile with pending_evidence status."""

    def __init__(self, repository: FounderProfileRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        founder_name: str,
        company_name: str | None = None,
        linkedin_url: str | None = None,
        notes: str | None = None,
        verification_reason: str | None = None,
        allow_duplicate: bool = False,
    ) -> FounderProfile:
        name_clean = founder_name.strip()
        if not name_clean:
            raise InvalidEvidenceException("Founder name cannot be empty.")

        company_clean = company_name.strip() if company_name else None

        # Check for existing profile if not allowing duplicate
        existing = await self._repository.find_by_name_and_company(name_clean, company_clean)
        if existing and not allow_duplicate:
            raise DuplicateProfileException(
                founder_name=name_clean,
                company_name=company_clean,
                existing_id=str(existing.id),
                existing_slug=existing.slug,
            )

        slug = generate_founder_slug(name_clean, company_clean)
        slug_candidate = slug
        counter = 1
        while await self._repository.find_by_slug(slug_candidate):
            slug_candidate = f"{slug}-{counter}"
            counter += 1

        reason = (
            verification_reason.strip()
            if verification_reason and verification_reason.strip()
            else "Saved as pending by operator after automated fetch was blocked or uncorroborated."
        )

        retrieval = RetrievalPayload(
            status="pending_evidence",
            source_type="manual_pending",
            source_id=f"pending_{slug_candidate}",
            sections_available=[],
            warnings=["Pending manual text or PDF upload."],
            verification_reason=reason,
            source_label="Pending evidence",
        )

        profile = FounderProfile(
            id=uuid4(),
            slug=slug_candidate,
            founder_name=name_clean,
            company_name=company_clean,
            headline=f"Founder at {company_clean}" if company_clean else "Founder",
            linkedin_url=linkedin_url.strip() if linkedin_url else None,
            retrieval=retrieval,
            identity_status="unverified",
            notes=notes.strip() if notes else None,
        )

        return await self._repository.save(profile)
