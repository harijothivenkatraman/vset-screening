"""Use case: Primary automated founder profile discovery and verification.

Pipeline:
1. URL Discovery:
   Priority 1: User-supplied profile URL
   Priority 2: Company website team/about page near founder name
   Priority 3: Search discovery fallback (SearXNG -> DuckDuckGo)
2. Fetch via ProfileScraperPort (rate limiter, circuit breaker, SSRF guard).
3. Parse via robust public profile normalizer.
4. Identity Verification:
   - Verified -> Saved and returned (status: verified).
   - Likely match -> Saved as 'Needs confirmation' (status: likely_match).
   - Blocked or Not found -> NOT saved automatically.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import urllib.parse
from uuid import uuid4

from app.application.ports.founder_profile_repository import FounderProfileRepository
from app.application.ports.page_fetcher_port import PageFetcherPort
from app.application.ports.profile_scraper_port import ProfileScraperPort
from app.application.ports.web_search_port import WebSearchPort
from app.application.services.founder_url_discovery import FounderUrlDiscoveryService
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
from app.domain.exceptions import InvalidEvidenceException


def _normalize_profile_url(url: str) -> str:
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
    if host in ("localhost", "127.0.0.1", "::1", "0.0.0.0") or host.startswith(
        ("10.", "192.168.", "172.16.", "169.254.")
    ):
        raise InvalidEvidenceException("Access to internal/loopback IP addresses is disallowed.")
    if "linkedin.com" not in host:
        raise InvalidEvidenceException(f"URL must be a public profile on linkedin.com (got {host}).")


@dataclass(frozen=True)
class AutoDiscoverResult:
    """Outcome of auto-discovery pipeline."""
    outcome: str  # "verified" | "likely_match" | "blocked" | "not_found"
    candidate: FounderProfile | None
    persisted: bool
    message: str
    discovered_url: str | None = None
    diagnostic: SourceDiagnostic | None = None


class AutoDiscoverFounderUseCase:
    """Orchestrates end-to-end URL discovery, fetch, parse, and identity verification."""

    def __init__(
        self,
        repository: FounderProfileRepository,
        scraper: ProfileScraperPort,
        page_fetcher: PageFetcherPort | None = None,
        search_adapter: WebSearchPort | None = None,
    ) -> None:
        self._repository = repository
        self._scraper = scraper
        self._page_fetcher = page_fetcher
        self._search_adapter = search_adapter

    async def execute(
        self,
        founder_name: str,
        company_name: str | None = None,
        profile_url: str | None = None,
        company_website: str | None = None,
    ) -> AutoDiscoverResult:
        name_clean = founder_name.strip()
        if not name_clean:
            raise InvalidEvidenceException("Founder name cannot be empty.")

        company_clean = company_name.strip() if company_name else None
        website_clean = company_website.strip() if company_website else None

        # 1. URL Discovery across priority tiers
        discovered = await FounderUrlDiscoveryService.discover(
            founder_name=name_clean,
            company_name=company_clean,
            profile_url=profile_url,
            company_website=website_clean,
            page_fetcher=self._page_fetcher,
            search_adapter=self._search_adapter,
        )

        if not discovered.url:
            return AutoDiscoverResult(
                outcome="not_found",
                candidate=None,
                persisted=False,
                message="We couldn't find a public profile URL for this founder.",
                discovered_url=None,
            )

        # 2. Fetch and SSRF safety check
        target_url = _normalize_profile_url(discovered.url)
        _validate_safe_profile_url(target_url)

        profile_dto, diag = await self._scraper.fetch_person_with_diagnostic(target_url)

        is_blocked = diag.outcome in ("blocked_by_bot_protection", "circuit_breaker_open", "auth_wall")
        has_data = bool(profile_dto and (profile_dto.headline or profile_dto.summary or profile_dto.experience))

        # Handle Blocked or Failed Scrape (CRITICAL: Do NOT persist automatically)
        if is_blocked or not has_data:
            return AutoDiscoverResult(
                outcome="blocked",
                candidate=None,
                persisted=False,
                message="Automated fetch was blocked by bot protection.",
                discovered_url=target_url,
                diagnostic=diag,
            )

        # 3. Identity Verification
        assert profile_dto is not None
        verify_res = FounderIdentityVerifier.verify(
            candidate_name=profile_dto.name,
            target_founder_name=name_clean,
            company_name=company_clean or "",
            company_domain=website_clean or "",
            candidate_profile=profile_dto,
            url_source_type=discovered.source_type,
            candidate_url=target_url,
        )

        # Format Timeline Items
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

        today_iso = datetime.now(timezone.utc).strftime("%d %b %Y")

        if verify_res.is_auto_attach:
            # OUTCOME 1: Verified -> Save and return
            slug = generate_founder_slug(name_clean, company_clean)
            slug_candidate = slug
            counter = 1
            while await self._repository.find_by_slug(slug_candidate):
                slug_candidate = f"{slug}-{counter}"
                counter += 1

            retrieval = RetrievalPayload(
                status="retrieved",
                source_type="linkedin_public",
                source_id=f"fetch_{target_url}",
                sections_available=[k for k, v in [("headline", profile_dto.headline), ("experience", exp_items), ("education", edu_items)] if v],
                warnings=[],
                verification_reason=verify_res.reason,
                source_label=f"Public profile · retrieved {today_iso}",
            )

            profile_entity = FounderProfile(
                id=uuid4(),
                slug=slug_candidate,
                founder_name=profile_dto.name or name_clean,
                company_name=company_clean,
                headline=profile_dto.headline,
                location=profile_dto.location,
                about=profile_dto.summary,
                linkedin_url=target_url,
                experience_timeline=exp_items,
                education=edu_items,
                skills=list(getattr(profile_dto, "skills", []) or []),
                certifications=list(getattr(profile_dto, "certifications", []) or []),
                languages=list(getattr(profile_dto, "languages", []) or []),
                retrieval=retrieval,
                identity_status="verified",
            )
            saved = await self._repository.save(profile_entity)
            return AutoDiscoverResult(
                outcome="verified",
                candidate=saved,
                persisted=True,
                message="Profile verified against company and saved.",
                discovered_url=target_url,
                diagnostic=diag,
            )

        elif verify_res.identity_status == "likely_match":
            # OUTCOME 2: Likely match -> Save as "Needs confirmation"
            slug = generate_founder_slug(name_clean, company_clean)
            slug_candidate = slug
            counter = 1
            while await self._repository.find_by_slug(slug_candidate):
                slug_candidate = f"{slug}-{counter}"
                counter += 1

            retrieval = RetrievalPayload(
                status="identity_unverified",
                source_type="linkedin_public",
                source_id=f"fetch_{target_url}",
                sections_available=[k for k, v in [("headline", profile_dto.headline), ("experience", exp_items), ("education", edu_items)] if v],
                warnings=["Candidate mentions company but lacks domain corroboration."],
                verification_reason=verify_res.reason,
                source_label="Needs confirmation",
            )

            profile_entity = FounderProfile(
                id=uuid4(),
                slug=slug_candidate,
                founder_name=profile_dto.name or name_clean,
                company_name=company_clean,
                headline=profile_dto.headline,
                location=profile_dto.location,
                about=profile_dto.summary,
                linkedin_url=target_url,
                experience_timeline=exp_items,
                education=edu_items,
                skills=list(getattr(profile_dto, "skills", []) or []),
                certifications=list(getattr(profile_dto, "certifications", []) or []),
                languages=list(getattr(profile_dto, "languages", []) or []),
                retrieval=retrieval,
                identity_status="likely_match",
            )
            saved = await self._repository.save(profile_entity)
            return AutoDiscoverResult(
                outcome="likely_match",
                candidate=saved,
                persisted=True,
                message="Candidate profile found but requires confirmation.",
                discovered_url=target_url,
                diagnostic=diag,
            )

        else:
            # OUTCOME 3: Unverified / Name mismatch / Different company
            # CRITICAL: Must NEVER auto-attach or save!
            return AutoDiscoverResult(
                outcome="not_found",
                candidate=None,
                persisted=False,
                message=verify_res.reason,
                discovered_url=target_url,
                diagnostic=diag,
            )
