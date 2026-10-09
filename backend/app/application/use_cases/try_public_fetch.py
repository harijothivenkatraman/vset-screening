"""Use case: Best-effort public LinkedIn profile fetch with identity verification.

Secondary ingestion path.
CRITICAL RULE (Amendment 3):
Do NOT persist blocked or not_found results automatically.
Return the result to the client/UI; persist only if the operator explicitly chooses
"Save as pending" (status pending_evidence). Never create empty rows from failed attempts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from app.application.ports.founder_profile_repository import FounderProfileRepository
from app.application.ports.profile_scraper_port import ProfileScraperPort
from app.application.services.founder_cross_check import FounderCrossCheckService
from app.application.services.identity_verifier import FounderIdentityVerifier
from app.application.use_cases.add_from_evidence import generate_founder_slug
from app.domain.entities.discovery import SourceDiagnostic
from app.domain.entities.founder_profile import (
    EducationItem,
    ExperienceTimelineItem,
    FounderProfile,
    IdentityStatusType,
    RetrievalPayload,
    RetrievalStatusType,
)
from app.domain.exceptions import DuplicateProfileException, InvalidEvidenceException
import urllib.parse


def _normalize_linkedin_url(url: str) -> str:
    cleaned = url.strip()
    if not cleaned.startswith(("http://", "https://")):
        cleaned = "https://" + cleaned
    parsed = urllib.parse.urlparse(cleaned)
    clean_path = parsed.path.rstrip("/")
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc.lower(), clean_path, "", "", ""))


def _validate_safe_profile_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise InvalidEvidenceException("Invalid URL scheme: must be http or https.")
    host = (parsed.hostname or "").lower()
    if not host:
        raise InvalidEvidenceException("Invalid URL: missing hostname.")
    if host in ("localhost", "127.0.0.1", "::1", "0.0.0.0") or host.startswith(("10.", "192.168.", "172.16.", "169.254.")):
        raise InvalidEvidenceException("Access to internal/loopback IP addresses is disallowed.")
    if "linkedin.com" not in host:
        raise InvalidEvidenceException(f"URL must be a LinkedIn profile (got {host}).")


@dataclass(frozen=True)
class TryPublicFetchResult:
    """Result returned to presentation layer. Not automatically persisted if blocked."""
    candidate: FounderProfile | None
    diagnostic: SourceDiagnostic
    is_blocked: bool
    is_verified: bool
    persisted: bool
    message: str


class TryPublicFetchUseCase:
    """Performs best-effort public LinkedIn scraping and identity verification."""

    def __init__(
        self,
        repository: FounderProfileRepository,
        scraper: ProfileScraperPort,
    ) -> None:
        self._repository = repository
        self._scraper = scraper


    async def execute(
        self,
        founder_name: str,
        linkedin_url: str,
        company_name: str | None = None,
        company_domain: str | None = None,
        save_as_pending: bool = False,
        allow_duplicate: bool = False,
    ) -> TryPublicFetchResult:
        name_clean = founder_name.strip()
        if not name_clean:
            raise InvalidEvidenceException("Founder name cannot be empty.")

        url_clean = linkedin_url.strip()
        if not url_clean:
            raise InvalidEvidenceException("LinkedIn profile URL cannot be empty.")

        # Normalize and validate SSRF safety
        normalized_url = _normalize_linkedin_url(url_clean)
        _validate_safe_profile_url(normalized_url)

        # Check existing profile collision if saving
        company_clean = company_name.strip() if company_name else None
        if save_as_pending:
            existing = await self._repository.find_by_name_and_company(name_clean, company_clean)
            if existing and not allow_duplicate:
                raise DuplicateProfileException(
                    founder_name=name_clean,
                    company_name=company_clean,
                    existing_id=str(existing.id),
                    existing_slug=existing.slug,
                )

        # Scrape with diagnostics
        profile_dto, diag = await self._scraper.fetch_person_with_diagnostic(normalized_url)

        is_blocked = diag.outcome in ("blocked_by_bot_protection", "circuit_breaker_open", "auth_wall")
        has_data = bool(profile_dto and (profile_dto.headline or profile_dto.summary or profile_dto.experience))

        # Identity Verification
        verify_res = None
        is_verified = False
        if profile_dto and has_data:
            verify_res = FounderIdentityVerifier.verify(
                candidate_name=profile_dto.name,
                target_founder_name=name_clean,
                company_name=company_clean or "",
                company_domain=company_domain or "",
                candidate_profile=profile_dto,
                url_source_type="search_discovery",
                candidate_url=normalized_url,
            )
            is_verified = verify_res.is_auto_attach

        # Handle Blocked or Failed Scrape
        if is_blocked or not has_data:
            if save_as_pending:
                # Operator chose "Save as pending"
                slug = generate_founder_slug(name_clean, company_clean)
                slug_candidate = slug
                counter = 1
                while await self._repository.find_by_slug(slug_candidate):
                    slug_candidate = f"{slug}-{counter}"
                    counter += 1

                retrieval = RetrievalPayload(
                    status="pending_evidence",
                    source_type="linkedin_public",
                    source_id=f"pending_{slug_candidate}",
                    sections_available=[],
                    warnings=["Fetch blocked by bot protection; pending manual text/PDF upload."],
                    verification_reason="Saved as pending by operator after automated fetch was blocked.",
                    source_label="Pending evidence",
                )

                pending_profile = FounderProfile(
                    id=uuid4(),
                    slug=slug_candidate,
                    founder_name=name_clean,
                    company_name=company_clean,
                    headline=f"Founder at {company_clean}" if company_clean else "Founder",
                    linkedin_url=normalized_url,
                    retrieval=retrieval,
                    identity_status="unverified",
                )
                saved = await self._repository.save(pending_profile)
                return TryPublicFetchResult(
                    candidate=saved,
                    diagnostic=diag,
                    is_blocked=is_blocked,
                    is_verified=False,
                    persisted=True,
                    message="Automated fetch was blocked. Profile created with status 'pending_evidence'.",
                )

            # Not saved: return diagnostic to UI for operator review without persisting empty rows
            return TryPublicFetchResult(
                candidate=None,
                diagnostic=diag,
                is_blocked=is_blocked,
                is_verified=False,
                persisted=False,
                message="Automated fetch was blocked by bot protection. Please paste profile text or upload a PDF.",
            )

        # Scrape succeeded with candidate data
        assert profile_dto is not None
        exp_items = [
            ExperienceTimelineItem(
                title=str(e.get("title") or ""),
                company=str(e.get("company") or ""),
                start=str(e.get("start") or ""),
                end=str(e.get("end") or ""),
                duration=str(e.get("duration") or ""),
                description=str(e.get("description") or ""),
                is_current=bool(e.get("is_current", False)),
            )
            for e in (profile_dto.experience or [])
        ]

        edu_items = [
            EducationItem(
                school=str(ed.get("school") or ed.get("institution") or ed.get("title") or ""),
                degree=str(ed.get("degree") or ed.get("subtitle") or ""),
                field=str(ed.get("field") or ed.get("field_of_study") or ""),
                start_year=str(ed.get("start_year") or ed.get("year") or ""),
                end_year=str(ed.get("end_year") or ""),
            )
            for ed in (profile_dto.education or [])
        ]

        status_val: RetrievalStatusType = "retrieved" if is_verified else "identity_unverified"
        id_status: IdentityStatusType = "verified" if is_verified else "likely_match"

        retrieval = RetrievalPayload(
            status=status_val,
            source_type="linkedin_public",
            source_id=f"fetch_{normalized_url}",
            sections_available=[k for k, v in [("headline", profile_dto.headline), ("experience", exp_items), ("education", edu_items)] if v],
            warnings=[] if is_verified else ["Identity unverified — candidate lacks domain corroboration."],
            verification_reason=verify_res.reason if verify_res else None,
            source_label=f"LinkedIn public · retrieved {profile_dto.retrieved_at[:10]}" if is_verified else "Unverified candidate",
        )

        slug = generate_founder_slug(name_clean, company_clean)
        slug_candidate = slug
        counter = 1
        while await self._repository.find_by_slug(slug_candidate):
            slug_candidate = f"{slug}-{counter}"
            counter += 1

        candidate_entity = FounderProfile(
            id=uuid4(),
            slug=slug_candidate,
            founder_name=profile_dto.name or name_clean,
            company_name=company_clean,
            headline=profile_dto.headline,
            location=profile_dto.location,
            about=profile_dto.summary,
            linkedin_url=normalized_url,
            experience_timeline=exp_items,
            education=edu_items,
            skills=list(getattr(profile_dto, "skills", []) or []),
            certifications=list(getattr(profile_dto, "certifications", []) or []),
            languages=list(getattr(profile_dto, "languages", []) or []),
            retrieval=retrieval,
            identity_status=id_status,
        )

        persisted_entity = None
        if is_verified or save_as_pending:
            persisted_entity = await self._repository.save(candidate_entity)

        return TryPublicFetchResult(
            candidate=persisted_entity or candidate_entity,
            diagnostic=diag,
            is_blocked=False,
            is_verified=is_verified,
            persisted=persisted_entity is not None,
            message="Public profile fetched successfully." if is_verified else "Candidate profile fetched but requires confirmation.",
        )
