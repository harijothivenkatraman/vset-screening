from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.action_item_repository import ActionItemRepository
from app.application.ports.company_repository import CompanyRepository
from app.application.ports.report_repository import ReportRepository
from app.application.ports.section_repository import SectionRepository
from app.application.ports.source_repository import SourceRepository
from app.application.services.delete_company import DeleteCompanyService
from app.application.services.get_actions import GetActionsService
from app.application.services.get_report_header import GetReportHeaderService
from app.application.services.get_section import GetSectionService
from app.application.services.get_section_nav import GetSectionNavService
from app.application.services.get_sources import GetSourcesService
from app.application.services.list_companies import ListCompaniesService
from app.infrastructure.ingestion.import_service import ReportImportService
from app.infrastructure.persistence.action_item_repo import SqlAlchemyActionItemRepository
from app.infrastructure.persistence.company_repo import SqlAlchemyCompanyRepository
from app.infrastructure.persistence.database import get_db_session
from app.infrastructure.persistence.report_repo import SqlAlchemyReportRepository
from app.infrastructure.persistence.section_repo import SqlAlchemySectionRepository
from app.infrastructure.persistence.source_repo import SqlAlchemySourceRepository


def get_company_repository(session: AsyncSession = Depends(get_db_session)) -> CompanyRepository:
    return SqlAlchemyCompanyRepository(session)


def get_report_repository(session: AsyncSession = Depends(get_db_session)) -> ReportRepository:
    return SqlAlchemyReportRepository(session)


def get_section_repository(session: AsyncSession = Depends(get_db_session)) -> SectionRepository:
    return SqlAlchemySectionRepository(session)


def get_action_item_repository(session: AsyncSession = Depends(get_db_session)) -> ActionItemRepository:
    return SqlAlchemyActionItemRepository(session)


def get_source_repository(session: AsyncSession = Depends(get_db_session)) -> SourceRepository:
    return SqlAlchemySourceRepository(session)


def get_list_companies_service(
    company_repo: CompanyRepository = Depends(get_company_repository),
    report_repo: ReportRepository = Depends(get_report_repository),
) -> ListCompaniesService:
    return ListCompaniesService(company_repo, report_repo)


def get_delete_company_service(
    company_repo: CompanyRepository = Depends(get_company_repository),
) -> DeleteCompanyService:
    return DeleteCompanyService(company_repo)


def get_report_header_service(
    company_repo: CompanyRepository = Depends(get_company_repository),
    report_repo: ReportRepository = Depends(get_report_repository),
) -> GetReportHeaderService:
    return GetReportHeaderService(company_repo, report_repo)


def get_section_nav_service(
    company_repo: CompanyRepository = Depends(get_company_repository),
    report_repo: ReportRepository = Depends(get_report_repository),
    section_repo: SectionRepository = Depends(get_section_repository),
) -> GetSectionNavService:
    return GetSectionNavService(company_repo, report_repo, section_repo)


def get_section_service(
    company_repo: CompanyRepository = Depends(get_company_repository),
    report_repo: ReportRepository = Depends(get_report_repository),
    section_repo: SectionRepository = Depends(get_section_repository),
    action_item_repo: ActionItemRepository = Depends(get_action_item_repository),
) -> GetSectionService:
    return GetSectionService(company_repo, report_repo, section_repo, action_item_repo)


def get_actions_service(
    company_repo: CompanyRepository = Depends(get_company_repository),
    report_repo: ReportRepository = Depends(get_report_repository),
    action_item_repo: ActionItemRepository = Depends(get_action_item_repository),
) -> GetActionsService:
    return GetActionsService(company_repo, report_repo, action_item_repo)


def get_sources_service(
    company_repo: CompanyRepository = Depends(get_company_repository),
    report_repo: ReportRepository = Depends(get_report_repository),
    source_repo: SourceRepository = Depends(get_source_repository),
) -> GetSourcesService:
    return GetSourcesService(company_repo, report_repo, source_repo)


def get_import_service(session: AsyncSession = Depends(get_db_session)) -> ReportImportService:
    return ReportImportService(session)


# ── Discovery Singletons & Factories ──
from functools import lru_cache

from app.config import get_settings
from app.application.ports.cache_port import CachePort
from app.application.ports.job_store_port import JobStorePort
from app.application.ports.llm_port import LlmPort
from app.application.ports.page_fetcher_port import PageFetcherPort
from app.application.ports.profile_scraper_port import ProfileScraperPort
from app.application.ports.report_extractor_port import ReportExtractorPort
from app.application.ports.report_import_port import ReportImportPort
from app.application.ports.web_search_port import WebSearchPort

from app.application.services.build_report import BuildReportService
from app.application.services.get_discovery_job import GetDiscoveryJobService
from app.application.services.resolve_candidates import ResolveCandidatesService
from app.application.services.start_discovery_job import StartDiscoveryJobService

from app.infrastructure.discovery.cache.ttl_cache import InMemoryTtlCache
from app.infrastructure.discovery.http.rate_limiter import HostRateLimiter
from app.infrastructure.discovery.jobs.in_memory_job_store import InMemoryJobStore
from app.infrastructure.discovery.llm.openai_compatible import OpenAICompatibleLlmAdapter
from app.infrastructure.discovery.llm.report_extractor import SectionBySectionExtractor
from app.infrastructure.discovery.report_import_adapter import ReportImportAdapter
from app.infrastructure.discovery.scrapers.linkedin_public import LinkedInPublicScraper
from app.infrastructure.discovery.scrapers.website_fetcher import WebsiteFetcherAdapter
from app.infrastructure.discovery.search.duckduckgo_search import DuckDuckGoSearchAdapter
from app.infrastructure.discovery.search.fallback_search import FallbackSearchAdapter
from app.infrastructure.discovery.search.searxng_search import SearXNGSearchAdapter


@lru_cache
def get_cache_port() -> CachePort:
    settings = get_settings()
    return InMemoryTtlCache(default_ttl_seconds=settings.CACHE_TTL, max_size=500)


@lru_cache
def get_job_store_port() -> JobStorePort:
    settings = get_settings()
    return InMemoryJobStore(max_jobs=settings.DISCOVERY_MAX_JOBS_STORED)


@lru_cache
def get_rate_limiter() -> HostRateLimiter:
    settings = get_settings()
    return HostRateLimiter(min_interval_seconds=settings.SCRAPER_MIN_INTERVAL)


def get_web_search_port() -> WebSearchPort:
    settings = get_settings()
    providers: list[tuple[str, WebSearchPort]] = []

    for name in settings.SEARCH_PROVIDERS:
        name_clean = name.strip().lower()
        if name_clean == "searxng":
            if settings.SEARXNG_BASE_URL:
                providers.append(("searxng", SearXNGSearchAdapter(base_url=settings.SEARXNG_BASE_URL)))
        elif name_clean == "duckduckgo":
            providers.append(("duckduckgo", DuckDuckGoSearchAdapter()))

    if not providers:
        providers.append(("duckduckgo", DuckDuckGoSearchAdapter()))

    return FallbackSearchAdapter(providers)


def get_profile_scraper_port(
    rate_limiter: HostRateLimiter = Depends(get_rate_limiter),
) -> ProfileScraperPort:
    return LinkedInPublicScraper(rate_limiter=rate_limiter)


def get_page_fetcher_port(
    rate_limiter: HostRateLimiter = Depends(get_rate_limiter),
) -> PageFetcherPort:
    return WebsiteFetcherAdapter(rate_limiter=rate_limiter)


def get_llm_port() -> LlmPort:
    settings = get_settings()
    return OpenAICompatibleLlmAdapter(
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_MODEL,
        timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
    )


def get_report_extractor_port(
    llm: LlmPort = Depends(get_llm_port),
) -> ReportExtractorPort:
    settings = get_settings()
    return SectionBySectionExtractor(llm=llm, profile=settings.LLM_PROFILE)


def get_report_import_port(
    session: AsyncSession = Depends(get_db_session),
) -> ReportImportPort:
    return ReportImportAdapter(session=session)


def get_resolve_candidates_service(
    web_search: WebSearchPort = Depends(get_web_search_port),
    cache: CachePort = Depends(get_cache_port),
) -> ResolveCandidatesService:
    return ResolveCandidatesService(web_search=web_search, cache=cache)


def get_start_discovery_job_service(
    job_store: JobStorePort = Depends(get_job_store_port),
) -> StartDiscoveryJobService:
    settings = get_settings()
    return StartDiscoveryJobService(
        job_store=job_store,
        discovery_enabled=settings.DISCOVERY_ENABLED,
    )


def get_discovery_job_service(
    job_store: JobStorePort = Depends(get_job_store_port),
) -> GetDiscoveryJobService:
    return GetDiscoveryJobService(job_store=job_store)


from app.application.ports.evidence_source_port import EvidenceRegistryPort
from app.infrastructure.discovery.sources.registry import EvidenceSourceRegistry


def get_evidence_registry_port() -> EvidenceRegistryPort:
    return EvidenceSourceRegistry()


def get_build_report_service(
    job_store: JobStorePort = Depends(get_job_store_port),
    profile_scraper: ProfileScraperPort = Depends(get_profile_scraper_port),
    page_fetcher: PageFetcherPort = Depends(get_page_fetcher_port),
    report_extractor: ReportExtractorPort = Depends(get_report_extractor_port),
    report_import: ReportImportPort = Depends(get_report_import_port),
    source_registry: EvidenceRegistryPort = Depends(get_evidence_registry_port),
) -> BuildReportService:
    return BuildReportService(
        job_store=job_store,
        profile_scraper=profile_scraper,
        page_fetcher=page_fetcher,
        report_extractor=report_extractor,
        report_import=report_import,
        source_registry=source_registry,
    )


# ── Founder Profiles Standalone Dependencies ──
from app.application.ports.founder_profile_repository import FounderProfileRepository
from app.infrastructure.persistence.sqlite_founder_repository import SqliteFounderProfileRepository
from app.application.use_cases.add_from_evidence import AddFromEvidenceUseCase
from app.application.use_cases.delete_profile import DeleteProfileUseCase
from app.application.use_cases.export_profile import ExportProfileUseCase
from app.application.use_cases.get_profile import GetProfileUseCase
from app.application.use_cases.list_profiles import ListProfilesUseCase
from app.application.use_cases.restore_profile_version import RestoreProfileVersionUseCase
from app.application.use_cases.try_public_fetch import TryPublicFetchUseCase
from app.application.use_cases.update_profile import UpdateProfileUseCase


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


