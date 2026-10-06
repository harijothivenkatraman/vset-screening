"""Presentation layer dependencies and dependency injection factories."""
from __future__ import annotations

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.founder_profile_repository import FounderProfileRepository
from app.application.ports.page_fetcher_port import PageFetcherPort
from app.application.ports.profile_scraper_port import ProfileScraperPort
from app.application.ports.web_search_port import WebSearchPort
from app.application.use_cases.add_from_evidence import AddFromEvidenceUseCase
from app.application.use_cases.auto_discover_founder import AutoDiscoverFounderUseCase
from app.application.use_cases.delete_profile import DeleteProfileUseCase
from app.application.use_cases.export_profile import ExportProfileUseCase
from app.application.use_cases.get_profile import GetProfileUseCase
from app.application.use_cases.list_profiles import ListProfilesUseCase
from app.application.use_cases.restore_profile_version import RestoreProfileVersionUseCase
from app.application.use_cases.save_pending_profile import SavePendingProfileUseCase
from app.application.use_cases.try_public_fetch import TryPublicFetchUseCase
from app.application.use_cases.update_profile import UpdateProfileUseCase
from app.config import get_settings
from app.infrastructure.discovery.http.rate_limiter import HostRateLimiter
from app.infrastructure.discovery.scrapers.apify_linkedin import ApifyLinkedInScraper
from app.infrastructure.discovery.scrapers.linkedin_public import LinkedInPublicScraper
from app.infrastructure.discovery.scrapers.website_fetcher import WebsiteFetcher
from app.infrastructure.discovery.search.duckduckgo_search import DuckDuckGoSearchAdapter
from app.infrastructure.discovery.search.fallback_search import FallbackSearchAdapter
from app.infrastructure.discovery.search.searxng_search import SearXNGSearchAdapter
from app.infrastructure.persistence.database import get_db_session
from app.infrastructure.persistence.sqlite_founder_repository import (
    SqliteFounderProfileRepository,
)


@lru_cache
def get_rate_limiter() -> HostRateLimiter:
    settings = get_settings()
    return HostRateLimiter(min_interval_seconds=settings.SCRAPER_MIN_INTERVAL)


def get_profile_scraper_port(
    rate_limiter: HostRateLimiter = Depends(get_rate_limiter),
) -> ProfileScraperPort:
    settings = get_settings()
    fallback = LinkedInPublicScraper(rate_limiter=rate_limiter)
    return ApifyLinkedInScraper(
        token=settings.APIFY_TOKEN,
        fallback_scraper=fallback,
    )


def get_founder_profile_repository(
    session: AsyncSession = Depends(get_db_session),
) -> FounderProfileRepository:
    return SqliteFounderProfileRepository(session)


def get_add_from_evidence_use_case(
    repo: FounderProfileRepository = Depends(get_founder_profile_repository),
) -> AddFromEvidenceUseCase:
    return AddFromEvidenceUseCase(repo)


def get_try_public_fetch_use_case(
    repo: FounderProfileRepository = Depends(get_founder_profile_repository),
    scraper: ProfileScraperPort = Depends(get_profile_scraper_port),
) -> TryPublicFetchUseCase:
    return TryPublicFetchUseCase(
        repository=repo,
        scraper=scraper,
    )


def get_save_pending_profile_use_case(
    repo: FounderProfileRepository = Depends(get_founder_profile_repository),
) -> SavePendingProfileUseCase:
    return SavePendingProfileUseCase(repo)


def get_list_profiles_use_case(
    repo: FounderProfileRepository = Depends(get_founder_profile_repository),
) -> ListProfilesUseCase:
    return ListProfilesUseCase(repo)


def get_get_profile_use_case(
    repo: FounderProfileRepository = Depends(get_founder_profile_repository),
) -> GetProfileUseCase:
    return GetProfileUseCase(repo)


def get_update_profile_use_case(
    repo: FounderProfileRepository = Depends(get_founder_profile_repository),
) -> UpdateProfileUseCase:
    return UpdateProfileUseCase(repo)


def get_restore_profile_version_use_case(
    repo: FounderProfileRepository = Depends(get_founder_profile_repository),
) -> RestoreProfileVersionUseCase:
    return RestoreProfileVersionUseCase(repo)


def get_delete_profile_use_case(
    repo: FounderProfileRepository = Depends(get_founder_profile_repository),
) -> DeleteProfileUseCase:
    return DeleteProfileUseCase(repo)


def get_export_profile_use_case(
    repo: FounderProfileRepository = Depends(get_founder_profile_repository),
) -> ExportProfileUseCase:
    return ExportProfileUseCase(repo)


def get_page_fetcher_port(
    rate_limiter: HostRateLimiter = Depends(get_rate_limiter),
) -> PageFetcherPort:
    return WebsiteFetcher(rate_limiter=rate_limiter)


def get_web_search_port() -> WebSearchPort:
    settings = get_settings()
    providers: list[tuple[str, WebSearchPort]] = []
    if settings.SEARXNG_BASE_URL:
        providers.append(("searxng", SearXNGSearchAdapter(base_url=settings.SEARXNG_BASE_URL)))
    providers.append(("duckduckgo", DuckDuckGoSearchAdapter()))
    return FallbackSearchAdapter(providers=providers)


def get_auto_discover_founder_use_case(
    repo: FounderProfileRepository = Depends(get_founder_profile_repository),
    scraper: ProfileScraperPort = Depends(get_profile_scraper_port),
    page_fetcher: PageFetcherPort = Depends(get_page_fetcher_port),
    search_adapter: WebSearchPort = Depends(get_web_search_port),
) -> AutoDiscoverFounderUseCase:
    return AutoDiscoverFounderUseCase(
        repository=repo,
        scraper=scraper,
        page_fetcher=page_fetcher,
        search_adapter=search_adapter,
    )
