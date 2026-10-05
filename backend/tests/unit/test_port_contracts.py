"""Contract tests verifying that all real adapters and test fakes fulfill their respective port ABC contracts."""
from __future__ import annotations

import inspect
import pytest

from app.application.ports.cache_port import CachePort
from app.application.ports.company_repository import CompanyRepository
from app.application.ports.evidence_source_port import EvidenceSourcePort
from app.application.ports.job_store_port import JobStorePort
from app.application.ports.llm_port import LlmPort
from app.application.ports.page_fetcher_port import PageFetcherPort
from app.application.ports.profile_scraper_port import ProfileScraperPort
from app.application.ports.report_extractor_port import ReportExtractorPort
from app.application.ports.report_import_port import ReportImportPort
from app.application.ports.web_search_port import WebSearchPort
from app.infrastructure.discovery.sources.news import NewsSource
from app.infrastructure.discovery.sources.rdap import RdapSource
from app.infrastructure.discovery.sources.wayback import WaybackSource
from app.infrastructure.discovery.sources.wikidata import WikidataSource

from app.infrastructure.discovery.cache.ttl_cache import InMemoryTtlCache
from app.infrastructure.discovery.jobs.in_memory_job_store import InMemoryJobStore
from app.infrastructure.discovery.llm.openai_compatible import OpenAICompatibleLlmAdapter
from app.infrastructure.discovery.llm.report_extractor import SectionBySectionExtractor
from app.infrastructure.discovery.report_import_adapter import ReportImportAdapter
from app.infrastructure.discovery.scrapers.linkedin_public import LinkedInPublicScraper
from app.infrastructure.discovery.scrapers.news_fetcher import NewsFetcherAdapter
from app.infrastructure.discovery.scrapers.website_fetcher import WebsiteFetcherAdapter
from app.infrastructure.discovery.search.duckduckgo_search import DuckDuckGoSearchAdapter
from app.infrastructure.discovery.search.fallback_search import FallbackSearchAdapter
from app.infrastructure.discovery.search.searxng_search import SearXNGSearchAdapter
from app.infrastructure.persistence.company_repo import SqlAlchemyCompanyRepository

from tests.fakes.fake_ports import (
    FakeCache,
    FakeCompanyRepository,
    FakeJobStore,
    FakeLlm,
    FakePageFetcher,
    FakeProfileScraper,
    FakeReportExtractor,
    FakeReportImport,
    FakeWebSearch,
)


def _assert_implements_interface(cls: type, port_cls: type) -> None:
    assert issubclass(cls, port_cls), f"{cls.__name__} must inherit from {port_cls.__name__}"
    for method_name, method_obj in inspect.getmembers(port_cls, predicate=inspect.isfunction):
        if getattr(method_obj, "__isabstractmethod__", False):
            impl_method = getattr(cls, method_name, None)
            assert impl_method is not None, f"{cls.__name__} missing abstract method {method_name}"
            assert callable(impl_method), f"{cls.__name__}.{method_name} must be callable"


class TestPortContracts:
    @pytest.mark.parametrize(
        "adapter_cls",
        [
            FakeWebSearch,
            DuckDuckGoSearchAdapter,
            SearXNGSearchAdapter,
            FallbackSearchAdapter,
        ],
    )
    def test_web_search_port_contract(self, adapter_cls: type) -> None:
        _assert_implements_interface(adapter_cls, WebSearchPort)

    @pytest.mark.parametrize(
        "adapter_cls",
        [
            FakeProfileScraper,
            LinkedInPublicScraper,
        ],
    )
    def test_profile_scraper_port_contract(self, adapter_cls: type) -> None:
        _assert_implements_interface(adapter_cls, ProfileScraperPort)

    @pytest.mark.parametrize(
        "adapter_cls",
        [
            FakePageFetcher,
            WebsiteFetcherAdapter,
            NewsFetcherAdapter,
        ],
    )
    def test_page_fetcher_port_contract(self, adapter_cls: type) -> None:
        _assert_implements_interface(adapter_cls, PageFetcherPort)

    @pytest.mark.parametrize(
        "adapter_cls",
        [
            FakeLlm,
            OpenAICompatibleLlmAdapter,
        ],
    )
    def test_llm_port_contract(self, adapter_cls: type) -> None:
        _assert_implements_interface(adapter_cls, LlmPort)

    @pytest.mark.parametrize(
        "adapter_cls",
        [
            FakeReportExtractor,
            SectionBySectionExtractor,
        ],
    )
    def test_report_extractor_port_contract(self, adapter_cls: type) -> None:
        _assert_implements_interface(adapter_cls, ReportExtractorPort)

    @pytest.mark.parametrize(
        "adapter_cls",
        [
            FakeCache,
            InMemoryTtlCache,
        ],
    )
    def test_cache_port_contract(self, adapter_cls: type) -> None:
        _assert_implements_interface(adapter_cls, CachePort)

    @pytest.mark.parametrize(
        "adapter_cls",
        [
            FakeJobStore,
            InMemoryJobStore,
        ],
    )
    def test_job_store_port_contract(self, adapter_cls: type) -> None:
        _assert_implements_interface(adapter_cls, JobStorePort)

    @pytest.mark.parametrize(
        "adapter_cls",
        [
            FakeReportImport,
            ReportImportAdapter,
        ],
    )
    def test_report_import_port_contract(self, adapter_cls: type) -> None:
        _assert_implements_interface(adapter_cls, ReportImportPort)

    @pytest.mark.parametrize(
        "adapter_cls",
        [
            RdapSource,
            WikidataSource,
            NewsSource,
            WaybackSource,
        ],
    )
    def test_evidence_source_port_contract(self, adapter_cls: type) -> None:
        _assert_implements_interface(adapter_cls, EvidenceSourcePort)

    @pytest.mark.parametrize(
        "adapter_cls",
        [
            FakeCompanyRepository,
            SqlAlchemyCompanyRepository,
        ],
    )
    def test_company_repository_contract(self, adapter_cls: type) -> None:
        _assert_implements_interface(adapter_cls, CompanyRepository)


import uuid
from datetime import datetime, timezone
from app.domain.entities.company import Company


@pytest.mark.asyncio
async def test_fake_company_repository_crud_contract() -> None:
    repo = FakeCompanyRepository()
    cid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    comp = Company(
        id=cid,
        slug="test-co",
        name="Test Company",
        website="https://test.co",
        created_at=now,
        updated_at=now,
    )
    await repo.save(comp)

    # find_by_slug
    found = await repo.find_by_slug("test-co")
    assert found is not None
    assert found.id == cid
    assert found.name == "Test Company"

    # find_by_id
    found_id = await repo.find_by_id(cid)
    assert found_id is not None
    assert found_id.slug == "test-co"

    # find_by_name
    found_name = await repo.find_by_name("test company")
    assert found_name is not None

    # find_all
    all_comps = await repo.find_all()
    assert len(all_comps) == 1

    # delete_by_slug
    assert await repo.delete_by_slug("test-co") is True
    assert await repo.delete_by_slug("test-co") is False
    assert await repo.find_by_slug("test-co") is None


@pytest.mark.asyncio
async def test_sqlalchemy_company_repository_crud_contract(db_session) -> None:
    repo = SqlAlchemyCompanyRepository(db_session)
    cid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    comp = Company(
        id=cid,
        slug="test-co-sql",
        name="Test Company SQL",
        website="https://test-sql.co",
        created_at=now,
        updated_at=now,
    )
    await repo.save(comp)

    # find_by_slug
    found = await repo.find_by_slug("test-co-sql")
    assert found is not None
    assert found.id == cid
    assert found.name == "Test Company SQL"

    # find_by_id
    found_id = await repo.find_by_id(cid)
    assert found_id is not None
    assert found_id.slug == "test-co-sql"

    # find_by_name
    found_name = await repo.find_by_name("Test Company SQL")
    assert found_name is not None

    # find_all
    all_comps = await repo.find_all()
    assert any(c.slug == "test-co-sql" for c in all_comps)

    # delete_by_slug
    assert await repo.delete_by_slug("test-co-sql") is True
    assert await repo.delete_by_slug("test-co-sql") is False
    assert await repo.find_by_slug("test-co-sql") is None



