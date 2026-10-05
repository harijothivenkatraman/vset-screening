"""Use case: Add founder profile from manual text or uploaded PDF evidence.

Primary ingestion path in the standalone Founder Profiles application.
Enforces PII stripping, contact info discarding, and slug generation.
Sets identity_status="user_asserted" per architectural requirements.
"""
from __future__ import annotations

import base64
import re
from typing import Any
from uuid import UUID, uuid4

from app.application.ports.founder_profile_repository import FounderProfileRepository
from app.application.services.pdf_extractor import (
    MAX_PDF_BYTES,
    MAX_TEXT_CHARS,
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
from app.domain.exceptions import DuplicateProfileException, InvalidEvidenceException


def generate_founder_slug(name: str, company: str | None = None, suffix: str | None = None) -> str:
    """Generate a clean, URL-safe slug from founder name and optional company."""
    parts = [name]
    if company:
        parts.append(company)
    if suffix:
        parts.append(suffix)
    combined = " ".join(parts).lower().strip()
    clean = re.sub(r"[^\w\s-]", "", combined)
    slug = re.sub(r"[\s_-]+", "-", clean).strip("-")
    return slug or "founder"


class AddFromEvidenceUseCase:
    """Ingests text or PDF evidence to create a new FounderProfile."""

    def __init__(self, repository: FounderProfileRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        founder_name: str,
        company_name: str | None = None,
        notes: str | None = None,
        text: str | None = None,
        pdf_bytes: bytes | None = None,
        pdf_filename: str | None = None,
        allow_duplicate: bool = False,
    ) -> FounderProfile:
        name_clean = founder_name.strip()
        if not name_clean:
            raise InvalidEvidenceException("Founder name cannot be empty.")

        company_clean = company_name.strip() if company_name else None

        # Check for existing profile with matching name and company
        existing = await self._repository.find_by_name_and_company(name_clean, company_clean)
        if existing and not allow_duplicate:
            raise DuplicateProfileException(
                founder_name=name_clean,
                company_name=company_clean,
                existing_id=str(existing.id),
                existing_slug=existing.slug,
            )

        # Extract text from PDF if provided
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

        # Combine text and PDF extracted text
        raw_combined = f"{text or ''}\n{pdf_extracted_text}".strip()
        if not raw_combined:
            raise InvalidEvidenceException("Please provide profile text or upload a PDF document.")

        sanitized_text = sanitize_text(raw_combined)
        if not sanitized_text:
            raise InvalidEvidenceException("Provided evidence contained no readable profile text after sanitization.")

        # Discard contact blocks, personal emails, phone numbers, and messaging links
        privacy_cleaned = discard_contact_info(sanitized_text)

        # Parse structured fields
        parsed = parse_manual_profile_text(privacy_cleaned)

        # Build experience items
        experience_items: list[ExperienceTimelineItem] = []
        for exp in parsed.get("experience", []):
            experience_items.append(
                ExperienceTimelineItem(
                    title=str(exp.get("title") or exp.get("role") or ""),
                    company=str(exp.get("company") or ""),
                    start=str(exp.get("start") or ""),
                    end=str(exp.get("end") or ""),
                    duration=str(exp.get("duration") or ""),
                    description=str(exp.get("description") or ""),
                    is_current=bool(exp.get("is_current", False)),
                    location=str(exp.get("location") or ""),
                )
            )

        # Build education items
        education_items: list[EducationItem] = []
        for edu in parsed.get("education", []):
            education_items.append(
                EducationItem(
                    school=str(edu.get("school") or edu.get("institution") or ""),
                    degree=str(edu.get("degree") or ""),
                    field=str(edu.get("field") or ""),
                    start_year=str(edu.get("start_year") or ""),
                    end_year=str(edu.get("end_year") or ""),
                )
            )

        # Determine slug (append short uuid suffix if creating as a confirmed duplicate)
        suffix = uuid4().hex[:6] if allow_duplicate and existing else None
        slug = generate_founder_slug(name_clean, company_clean, suffix=suffix)

        # Ensure slug uniqueness in database
        slug_candidate = slug
        counter = 1
        while await self._repository.find_by_slug(slug_candidate):
            slug_candidate = f"{slug}-{counter}"
            counter += 1
        slug = slug_candidate

        source_title = pdf_filename if pdf_bytes else "Pasted profile text"
        sections_avail = [k for k, v in parsed.items() if v]

        retrieval = RetrievalPayload(
            status="user_provided",
            source_type="user_supplied",
            source_id=f"manual_{slug}",
            sections_available=sections_avail,
            warnings=[],
            verification_reason="Supplied by operator via text/PDF upload",
            source_label="Provided by user (unverified)",
        )

        profile = FounderProfile(
            id=uuid4(),
            slug=slug,
            founder_name=name_clean,
            company_name=company_clean,
            headline=parsed.get("headline"),
            location=parsed.get("location"),
            about=parsed.get("summary"),
            linkedin_url=None,
            experience_timeline=experience_items,
            education=education_items,
            skills=list(parsed.get("skills", [])),
            certifications=list(parsed.get("certifications", [])),
            languages=list(parsed.get("languages", [])),
            retrieval=retrieval,
            identity_status="user_asserted",
            notes=notes.strip() if notes else None,
        )

        return await self._repository.save(profile)
