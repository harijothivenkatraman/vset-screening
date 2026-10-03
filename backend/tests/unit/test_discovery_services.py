"""Tests for discovery use cases with fake ports."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from app.application.services.resolve_candidates import (
    ResolveCandidatesService,
    ResolveInput,
)
from app.application.services.start_discovery_job import (
    StartDiscoveryJobService,
    StartJobInput,
)
from app.application.services.get_discovery_job import GetDiscoveryJobService
from app.application.services.build_report import BuildReportService
from app.domain.entities.discovery import (
    CompanyProfile,
    DiscoveryJob,
    Evidence,
    EvidenceSource,
    JobState,
    PageContent,
    PersonProfile,
    SearchResult,
)
from app.domain.exceptions import (
    DiscoveryDisabledError,
    JobNotFoundError,
)
from tests.fakes.fake_ports import (
    FakeCache,
    FakeJobStore,
    FakePageFetcher,
    FakeProfileScraper,
    FakeReportExtractor,
    FakeReportImport,
    FakeWebSearch,
)


# ── ResolveCandidatesService ───────────────────────────────────────────

class TestResolveCandidatesService:
    async def test_resolve_with_search_results(self) -> None:
        search = FakeWebSearch(results=[
            SearchResult(
                url="https://linkedin.com/company/acme",
                title="Acme Corp | LinkedIn",
                snippet="Acme Corp on LinkedIn",
                domain="linkedin.com",
            ),
        ])
        cache = FakeCache()
        service = ResolveCandidatesService(search, cache)

        result = await service.execute(ResolveInput(
            company_name="Acme",
            founder_names=["Alice Smith"],
        ))

        assert not result.search_unavailable
        assert "company_linkedin" in result.candidates
        assert len(result.candidates["company_linkedin"]) == 1

    async def test_resolve_with_overrides_skips_search(self) -> None:
        search = FakeWebSearch(results=[])
        cache = FakeCache()
        service = ResolveCandidatesService(search, cache)

        result = await service.execute(ResolveInput(
            company_name="Acme",
            founder_names=["Alice"],
            company_linkedin_override="https://linkedin.com/company/acme",
        ))

        # Override should produce confidence=1.0 candidate
        assert len(result.candidates["company_linkedin"]) == 1
        assert result.candidates["company_linkedin"][0].confidence == 1.0
        # Search should still be called for founders (no override)
        assert len(search.queries) > 0

    async def test_resolve_caches_search_results(self) -> None:
        search = FakeWebSearch(results=[
            SearchResult(url="https://x.com", title="X", snippet="s", domain="x.com"),
        ])
        cache = FakeCache()
        service = ResolveCandidatesService(search, cache)

        # First call
        await service.execute(ResolveInput(company_name="Acme", founder_names=[]))
        first_call_count = len(search.queries)

        # Second call should use cache
        await service.execute(ResolveInput(company_name="Acme", founder_names=[]))
        assert len(search.queries) == first_call_count  # No new queries

    async def test_resolve_search_failure_sets_unavailable(self) -> None:
        """When search raises, search_unavailable should be True."""
        class FailingSearch(FakeWebSearch):
            async def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
                raise RuntimeError("Search down")

        search = FailingSearch()
        cache = FakeCache()
        service = ResolveCandidatesService(search, cache)

        result = await service.execute(ResolveInput(
            company_name="Acme",
            founder_names=["Alice"],
        ))

        assert result.search_unavailable
        assert result.error_message is not None


# ── StartDiscoveryJobService ──────────────────────────────────────────

class TestStartDiscoveryJobService:
    async def test_start_job_creates_job(self) -> None:
        store = FakeJobStore()
        service = StartDiscoveryJobService(store)

        result = await service.execute(StartJobInput(
            company_name="Acme",
            founder_names=["Alice"],
            confirmed_urls={"company_linkedin": "https://linkedin.com/company/acme"},
        ))

        assert result.state == "queued"
        assert result.job_id

        # Verify job in store
        job = await store.get(result.job_id)
        assert job is not None
        assert job.company_name == "Acme"
        assert job.state == JobState.QUEUED

    async def test_start_job_trims_names(self) -> None:
        store = FakeJobStore()
        service = StartDiscoveryJobService(store)

        result = await service.execute(StartJobInput(
            company_name="  Acme  ",
            founder_names=["  Alice  ", "", "  Bob  "],
            confirmed_urls={},
        ))

        job = await store.get(result.job_id)
        assert job is not None
        assert job.company_name == "Acme"
        assert job.founder_names == ["Alice", "Bob"]

    async def test_start_job_disabled_raises(self) -> None:
        store = FakeJobStore()
        service = StartDiscoveryJobService(store, discovery_enabled=False)

        with pytest.raises(DiscoveryDisabledError):
            await service.execute(StartJobInput(
                company_name="Acme",
                founder_names=["Alice"],
                confirmed_urls={},
            ))

    async def test_start_job_empty_name_raises(self) -> None:
        store = FakeJobStore()
        service = StartDiscoveryJobService(store)

        with pytest.raises(ValueError, match="Company name"):
            await service.execute(StartJobInput(
                company_name="   ",
                founder_names=["Alice"],
                confirmed_urls={},
            ))

    async def test_start_job_no_founders_raises(self) -> None:
        store = FakeJobStore()
        service = StartDiscoveryJobService(store)

        with pytest.raises(ValueError, match="founder"):
            await service.execute(StartJobInput(
                company_name="Acme",
                founder_names=[],
                confirmed_urls={},
            ))


# ── GetDiscoveryJobService ────────────────────────────────────────────

class TestGetDiscoveryJobService:
    async def test_get_existing_job(self) -> None:
        store = FakeJobStore()
        job = _make_job("test-1")
        await store.create(job)

        service = GetDiscoveryJobService(store)
        result = await service.execute("test-1")

        assert result.job_id == "test-1"
        assert result.company_name == "TestCo"
        assert result.state == "queued"

    async def test_get_missing_job_raises(self) -> None:
        store = FakeJobStore()
        service = GetDiscoveryJobService(store)

        with pytest.raises(JobNotFoundError):
            await service.execute("nonexistent")


# ── BuildReportService ────────────────────────────────────────────────

class TestBuildReportService:
    async def test_build_report_happy_path(self) -> None:
        store = FakeJobStore()
        scraper = FakeProfileScraper()
        scraper.company_profiles["https://linkedin.com/company/acme"] = CompanyProfile(
            name="Acme", description="A company",
        )
        fetcher = FakePageFetcher()
        fetcher.pages["https://www.acme.com"] = PageContent(
            url="https://www.acme.com",
            title="Acme",
            description="",
            text="About Acme Corp.",
        )
        extractor = FakeReportExtractor()
        importer = FakeReportImport()

        service = BuildReportService(store, scraper, fetcher, extractor, importer)

        job = _make_job("job-1")
        job.confirmed_urls = {
            "company_linkedin": "https://linkedin.com/company/acme",
            "website": "https://www.acme.com",
        }
        await store.create(job)

        await service.execute(job)

        assert job.state in (JobState.SUCCEEDED, JobState.PARTIAL)
        assert job.result_slug is not None
        assert len(importer.imported) == 1

    async def test_build_report_partial_on_source_failure(self) -> None:
        store = FakeJobStore()
        scraper = FakeProfileScraper()  # No profiles configured → will fail
        fetcher = FakePageFetcher()
        extractor = FakeReportExtractor()
        importer = FakeReportImport()

        service = BuildReportService(store, scraper, fetcher, extractor, importer)

        job = _make_job("job-2")
        job.confirmed_urls = {
            "company_linkedin": "https://linkedin.com/company/missing",
        }
        await store.create(job)

        await service.execute(job)

        # Should be PARTIAL since all attempted sources failed
        assert job.state == JobState.PARTIAL
        assert len(job.warnings) > 0
        assert len(job.diagnostics) > 0

    async def test_build_report_records_diagnostics(self) -> None:
        store = FakeJobStore()
        scraper = FakeProfileScraper()
        scraper.company_profiles["https://linkedin.com/company/acme"] = CompanyProfile(
            name="Acme", description="A company",
        )
        fetcher = FakePageFetcher()
        fetcher.pages["https://www.acme.com"] = PageContent(
            url="https://www.acme.com",
            title="Acme",
            description="Acme desc",
            text="About Acme Corp.",
        )
        extractor = FakeReportExtractor()
        importer = FakeReportImport()

        service = BuildReportService(store, scraper, fetcher, extractor, importer)

        job = _make_job("job-diag")
        job.confirmed_urls = {
            "company_linkedin": "https://linkedin.com/company/acme",
            "website": "https://www.acme.com",
        }
        await store.create(job)
        await service.execute(job)

        assert len(job.diagnostics) >= 2
        get_svc = GetDiscoveryJobService(store)
        status = await get_svc.execute("job-diag")
        assert len(status.diagnostics) >= 2

    async def test_build_report_failed_on_critical_error(self) -> None:
        store = FakeJobStore()
        scraper = FakeProfileScraper()
        fetcher = FakePageFetcher()

        class FailingExtractor(FakeReportExtractor):
            async def extract(self, evidence, company_name, founder_names):
                raise RuntimeError("LLM exploded")

        extractor = FailingExtractor()
        importer = FakeReportImport()

        service = BuildReportService(store, scraper, fetcher, extractor, importer)

        job = _make_job("job-3")
        await store.create(job)

        await service.execute(job)

        assert job.state == JobState.FAILED
        assert job.error_message is not None
        assert "LLM exploded" in job.error_message


# ── Helpers ────────────────────────────────────────────────────────────

def _make_job(job_id: str) -> DiscoveryJob:
    now = datetime.now(timezone.utc)
    return DiscoveryJob(
        id=job_id,
        company_name="TestCo",
        founder_names=["Alice", "Bob"],
        state=JobState.QUEUED,
        stage="Initial",
        progress=0.0,
        warnings=[],
        result_slug=None,
        created_at=now,
        updated_at=now,
        confirmed_urls={},
    )
