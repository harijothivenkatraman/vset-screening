"""Fake implementations of discovery ports for testing."""
from __future__ import annotations
from uuid import UUID
from app.application.ports.cache_port import CachePort
from app.application.ports.company_repository import CompanyRepository
from app.application.ports.job_store_port import JobStorePort
from app.application.ports.llm_port import LlmPort
from app.application.ports.page_fetcher_port import PageFetcherPort
from app.application.ports.profile_scraper_port import ProfileScraperPort
from app.application.ports.report_extractor_port import ReportExtractorPort
from app.application.ports.report_import_port import ReportImportPort, ImportResult
from app.application.ports.web_search_port import WebSearchPort
from app.domain.entities.company import Company
from app.domain.entities.discovery import *


class FakeWebSearch(WebSearchPort):
    def __init__(self, results: list[SearchResult] | None = None) -> None:
        self.results = results or []
        self.queries: list[str] = []
    
    async def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        self.queries.append(query)
        return self.results[:max_results]


class FakeProfileScraper(ProfileScraperPort):
    def __init__(self) -> None:
        self.company_profiles: dict[str, CompanyProfile] = {}
        self.person_profiles: dict[str, PersonProfile] = {}
    
    async def fetch_company(self, url: str) -> CompanyProfile | None:
        return self.company_profiles.get(url)
    
    async def fetch_person(self, url: str) -> PersonProfile | None:
        return self.person_profiles.get(url)


class FakePageFetcher(PageFetcherPort):
    def __init__(self) -> None:
        self.pages: dict[str, PageContent] = {}
    
    async def fetch(self, url: str) -> PageContent | None:
        return self.pages.get(url)


class FakeLlm(LlmPort):
    def __init__(self, response: str = '{}') -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []
    
    async def complete(self, prompt: str, *, system_prompt: str = '', response_schema: dict[str, Any] | None = None, max_tokens: int = 1024, temperature: float = 0.0) -> str:
        self.calls.append({'prompt': prompt, 'system_prompt': system_prompt})
        return self.response
    
    async def is_available(self) -> bool:
        return True


class FakeReportExtractor(ReportExtractorPort):
    """Returns a pre-configured canonical JSON for testing."""
    def __init__(self, report_json: dict[str, Any] | None = None) -> None:
        self._report_json = report_json
    
    async def extract(self, evidence: Evidence, company_name: str, founder_names: list[str]) -> dict[str, Any]:
        if self._report_json:
            return self._report_json
        # Import the mapper and generate a real one
        from app.application.mappers.evidence_to_report_mapper import build_canonical_report
        return build_canonical_report(evidence, company_name, founder_names)


class FakeCache(CachePort):
    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
    
    async def get(self, key: str) -> Any | None:
        return self._store.get(key)
    
    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        self._store[key] = value
    
    async def delete(self, key: str) -> None:
        self._store.pop(key, None)


class FakeJobStore(JobStorePort):
    def __init__(self) -> None:
        self._jobs: dict[str, DiscoveryJob] = {}
    
    async def create(self, job: DiscoveryJob) -> DiscoveryJob:
        self._jobs[job.id] = job
        return job
    
    async def get(self, job_id: str) -> DiscoveryJob | None:
        return self._jobs.get(job_id)
    
    async def update(self, job: DiscoveryJob) -> None:
        self._jobs[job.id] = job
    
    async def list_recent(self, limit: int = 10) -> list[DiscoveryJob]:
        jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]


class FakeReportImport(ReportImportPort):
    def __init__(self) -> None:
        self.imported: list[dict[str, Any]] = []
    
    async def import_report(self, raw_data: dict[str, Any]) -> ImportResult:
        self.imported.append(raw_data)
        company_name = raw_data.get('canonical', {}).get('meta', {}).get('company_name', 'unknown')
        slug = company_name.lower().replace(' ', '-')
        return ImportResult(status='created', company_slug=slug, message='ok')


class FakeCompanyRepository(CompanyRepository):
    def __init__(self, companies: list[Company] | None = None) -> None:
        self.companies: dict[str, Company] = {c.slug: c for c in (companies or [])}

    async def find_all(self) -> list[Company]:
        return sorted(list(self.companies.values()), key=lambda c: c.name)

    async def find_by_id(self, company_id: UUID) -> Company | None:
        for c in self.companies.values():
            if c.id == company_id:
                return c
        return None

    async def find_by_slug(self, slug: str) -> Company | None:
        return self.companies.get(slug)

    async def find_by_name(self, name: str) -> Company | None:
        for c in self.companies.values():
            if c.name.lower() == name.lower():
                return c
        return None

    async def save(self, company: Company) -> Company:
        self.companies[company.slug] = company
        return company

    async def delete_by_slug(self, slug: str) -> bool:
        if slug in self.companies:
            del self.companies[slug]
            return True
        return False

