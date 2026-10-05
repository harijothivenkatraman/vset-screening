"""Use case: Update an existing founder profile.

Implements Amendment 5:
- Explicit user re-upload replaces an existing profile after a confirm step.
- Keeps one previous version (restorable via previous_version snapshot).
- Non-downgrade applies to automated fetch/refresh only, not explicit user re-upload.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.application.ports.founder_profile_repository import FounderProfileRepository
from app.application.services.pdf_extractor import (
    MAX_PDF_BYTES,
    discard_contact_info,
    extract_pdf_text,
    parse_manual_profile_text,
    sanitize_text,
)
from app.domain.entities.founder_profile import (
    EducationItem,
    ExperienceTimelineItem,
    FounderProfile,
    RetrievalPayload,
)
from app.domain.exceptions import InvalidEvidenceException, ProfileNotFoundException

STATUS_RANK: dict[str, int] = {
    "reference_screen": 4,
    "user_provided": 4,
    "retrieved": 4,
    "identity_unverified": 2,
    "pending_evidence": 1,
    "blocked_by_bot_protection": 1,
    "not_found": 0,
}


class UpdateProfileUseCase:
    """Updates an existing profile with new evidence, notes, or confirmed status."""

    def __init__(self, repository: FounderProfileRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        identifier: str,
        notes: str | None = None,
        text: str | None = None,
        pdf_bytes: bytes | None = None,
        screening_assessment: str | None = None,
        confirm_identity: bool = False,
        is_user_override: bool = True,
    ) -> FounderProfile:
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

        has_new_evidence = bool(text or pdf_bytes)

        # 1. Handle explicit confirmation of unverified candidate
        if confirm_identity and profile.identity_status in ("likely_match", "unverified"):
            profile.identity_status = "verified"
            profile.retrieval = RetrievalPayload(
                status="retrieved",
                source_type=profile.retrieval.source_type,
                retrieved_at=profile.retrieval.retrieved_at,
                source_id=profile.retrieval.source_id,
                sections_available=profile.retrieval.sections_available,
                warnings=[],
                verification_reason="Confirmed by operator",
                source_label=profile.retrieval.source_label or "Operator confirmed",
            )
            profile.updated_at = datetime.now(timezone.utc)
            return await self._repository.save(profile)

        # 2. Handle evidence re-upload
        if has_new_evidence:
            pdf_extracted_text = ""
            if pdf_bytes:
                if len(pdf_bytes) > MAX_PDF_BYTES:
                    raise InvalidEvidenceException(
                        f"Uploaded PDF exceeds the {MAX_PDF_BYTES // (1024 * 1024)} MB limit."
                    )
                try:
                    pdf_extracted_text = extract_pdf_text(pdf_bytes)
                except Exception as exc:
                    raise InvalidEvidenceException(f"Could not extract text from PDF: {exc}") from exc

            raw_combined = f"{text or ''}\n{pdf_extracted_text}".strip()
            sanitized = sanitize_text(raw_combined)
            if not sanitized:
                raise InvalidEvidenceException("Provided evidence contained no readable profile text.")

            privacy_cleaned = discard_contact_info(sanitized)
            parsed = parse_manual_profile_text(privacy_cleaned)

            # Check non-downgrade only for automated updates
            if not is_user_override:
                new_status = "user_provided"
                old_status = profile.retrieval.status
                if STATUS_RANK.get(old_status, 0) > STATUS_RANK.get(new_status, 0):
                    return profile

            # Save previous version snapshot before replacing (Amendment 5)
            profile.previous_version = profile.create_version_snapshot()

            # Map experience
            exp_items = [
                ExperienceTimelineItem(
                    title=str(e.get("title") or e.get("role") or ""),
                    company=str(e.get("company") or ""),
                    start=str(e.get("start") or ""),
                    end=str(e.get("end") or ""),
                    duration=str(e.get("duration") or ""),
                    description=str(e.get("description") or ""),
                    is_current=bool(e.get("is_current", False)),
                    location=str(e.get("location") or ""),
                )
                for e in parsed.get("experience", [])
            ]

            # Map education
            edu_items = [
                EducationItem(
                    school=str(ed.get("school") or ed.get("institution") or ""),
                    degree=str(ed.get("degree") or ""),
                    field=str(ed.get("field") or ""),
                    start_year=str(ed.get("start_year") or ""),
                    end_year=str(ed.get("end_year") or ""),
                )
                for ed in parsed.get("education", [])
            ]

            # Update fields
            if parsed.get("headline"):
                profile.headline = parsed["headline"]
            if parsed.get("location"):
                profile.location = parsed["location"]
            if parsed.get("summary"):
                profile.about = parsed["summary"]
            if exp_items:
                profile.experience_timeline = exp_items
            if edu_items:
                profile.education = edu_items
            if parsed.get("skills"):
                profile.skills = list(parsed["skills"])
            if parsed.get("certifications"):
                profile.certifications = list(parsed["certifications"])
            if parsed.get("languages"):
                profile.languages = list(parsed["languages"])

            profile.retrieval = RetrievalPayload(
                status="user_provided",
                source_type="user_supplied",
                source_id=f"update_{profile.slug}",
                sections_available=[k for k, v in parsed.items() if v],
                warnings=[],
                verification_reason="Re-uploaded by operator via text/PDF upload",
                source_label="Provided by user (unverified)",
            )
            profile.identity_status = "user_asserted"

        # 3. Handle notes and screening assessment update
        if notes is not None:
            profile.notes = notes.strip() if notes.strip() else None

        if screening_assessment is not None:
            profile.screening_assessment = screening_assessment.strip() if screening_assessment.strip() else None

        profile.updated_at = datetime.now(timezone.utc)
        return await self._repository.save(profile)
