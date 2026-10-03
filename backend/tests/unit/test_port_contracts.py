"""Contract tests verifying that all real adapters and test fakes fulfill their respective port ABC contracts."""
from __future__ import annotations

import inspect
import pytest

from app.application.ports.cache_port import CachePort
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

from tests.fakes.fake_ports import (
    FakeCache,
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

