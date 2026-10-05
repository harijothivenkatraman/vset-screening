"""Unit tests for the Auto-Extract pipeline and AutoDiscoverFounderUseCase."""
from __future__ import annotations

from typing import Any
import pytest

from app.application.ports.founder_profile_repository import FounderProfileRepository
from app.application.ports.page_fetcher_port import PageFetcherPort
from app.application.ports.profile_scraper_port import ProfileScraperPort
from app.application.ports.web_search_port import WebSearchPort
from app.application.use_cases.auto_discover_founder import AutoDiscoverFounderUseCase
from app.domain.entities.discovery import PageContent, PersonProfile, SearchResult, SourceDiagnostic
from app.domain.entities.founder_profile import FounderProfile


class FakeFounderRepository(FounderProfileRepository):
    """In-memory fake repository for testing."""

    def __init__(self) -> None:
        self.profiles: dict[str, FounderProfile] = {}

    async def save(self, profile: FounderProfile) -> FounderProfile:
        self.profiles[profile.slug] = profile
        return profile

    async def find_by_id(self, profile_id: Any) -> FounderProfile | None:
        for p in self.profiles.values():
            if str(p.id) == str(profile_id):
                return p
        return None

    async def find_by_slug(self, slug: str) -> FounderProfile | None:
        return self.profiles.get(slug)

    async def find_by_name_and_company(self, name: str, company: str | None) -> FounderProfile | None:
        for p in self.profiles.values():
            if p.founder_name.lower() == name.lower() and (p.company_name or "").lower() == (company or "").lower():
                return p
        return None

    async def list_all(
        self, search: str | None = None, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[FounderProfile]:
        return list(self.profiles.values())

    async def count(self, search: str | None = None, status: str | None = None) -> int:
        return len(self.profiles)

    async def delete(self, profile_id: Any) -> bool:
        to_del = [s for s, p in self.profiles.items() if str(p.id) == str(profile_id)]
        for s in to_del:
            del self.profiles[s]
        return bool(to_del)

    async def save_version_snapshot(self, profile_id: Any, snapshot: dict[str, Any]) -> None:
        pass

    async def get_latest_version_snapshot(self, profile_id: Any) -> dict[str, Any] | None:
        return None


class FakeScraper(ProfileScraperPort):
    """Fake profile scraper returning predefined DTOs or diagnostics."""

    def __init__(self, outcomes: dict[str, tuple[PersonProfile | None, SourceDiagnostic]]) -> None:
        self.outcomes = outcomes

    async def fetch_person_with_diagnostic(self, url: str) -> tuple[PersonProfile | None, SourceDiagnostic]:
        if url in self.outcomes:
            return self.outcomes[url]
        return None, SourceDiagnostic(url=url, outcome="not_found")

    async def fetch_company(self, url: str) -> Any:
        return None

    async def fetch_person(self, url: str) -> PersonProfile | None:
        p, _ = await self.fetch_person_with_diagnostic(url)
        return p


class FakePageFetcher(PageFetcherPort):
    """Fake page fetcher returning predefined pages."""

    def __init__(self, pages: dict[str, PageContent]) -> None:
        self.pages = pages

    async def fetch(self, url: str) -> PageContent | None:
        return self.pages.get(url)


class FakeSearchAdapter(WebSearchPort):
    """Fake web search adapter returning predefined search results."""

    def __init__(self, results_map: dict[str, list[SearchResult]]) -> None:
        self.results_map = results_map

    async def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        for k, v in self.results_map.items():
            if k.lower() in query.lower():
                return v[:max_results]
        return []


@pytest.mark.asyncio
async def test_auto_discover_verified_via_website_proximity() -> None:
    """Outcome 1: URL discovered on company website near founder name -> Verified & saved."""
    repo = FakeFounderRepository()

    # Company website contains founder name and LinkedIn link
    website_page = PageContent(
        url="https://example.com/team",
        title="Example Corp - Leadership Team",
        description="Our founders and team",
        text="Asha Example is the Chief Executive Officer of Example Corp.",
        links=["https://www.linkedin.com/in/asha-example"],
    )
    fetcher = FakePageFetcher({"https://example.com": website_page, "https://example.com/team": website_page})

    profile_dto = PersonProfile(
        name="Asha Example",
        headline="CEO at Example Corp",
        summary="Building infrastructure",
        experience=[{"title": "CEO", "company": "Example Corp"}],
        url="https://www.linkedin.com/in/asha-example",
    )
    diag = SourceDiagnostic(url="https://www.linkedin.com/in/asha-example", outcome="ok")
    scraper = FakeScraper({"https://www.linkedin.com/in/asha-example": (profile_dto, diag)})

    use_case = AutoDiscoverFounderUseCase(
        repository=repo,
        scraper=scraper,
        page_fetcher=fetcher,
        search_adapter=None,
    )

    result = await use_case.execute(
        founder_name="Asha Example",
        company_name="Example Corp",
        company_website="https://example.com",
    )

    assert result.outcome == "verified"
    assert result.persisted is True
    assert result.candidate is not None
    assert result.candidate.founder_name == "Asha Example"
    assert result.candidate.identity_status == "verified"
    assert len(repo.profiles) == 1


@pytest.mark.asyncio
async def test_auto_discover_likely_match_saved_as_needs_confirmation() -> None:
    """Outcome 2: Found via search fallback with company name match only -> likely_match (Needs confirmation)."""
    repo = FakeFounderRepository()

    search_adapter = FakeSearchAdapter({
        "Asha Example": [
            SearchResult(
                url="https://www.linkedin.com/in/asha-example",
                title="Asha Example - CEO - Example Corp | LinkedIn",
                snippet="Asha Example is CEO at Example Corp.",
                domain="linkedin.com",
            )
        ]
    })

    # Profile mentions company name but no domain corroboration
    profile_dto = PersonProfile(
        name="Asha Example",
        headline="CEO at Example Corp",
        summary="Leading tech startup Example Corp",
        experience=[{"title": "CEO", "company": "Example Corp"}],
        url="https://www.linkedin.com/in/asha-example",
    )
    diag = SourceDiagnostic(url="https://www.linkedin.com/in/asha-example", outcome="ok")
    scraper = FakeScraper({"https://www.linkedin.com/in/asha-example": (profile_dto, diag)})

    use_case = AutoDiscoverFounderUseCase(
        repository=repo,
        scraper=scraper,
        page_fetcher=None,
        search_adapter=search_adapter,
    )

    result = await use_case.execute(
        founder_name="Asha Example",
        company_name="Example Corp",
    )

    assert result.outcome == "likely_match"
    assert result.persisted is True
    assert result.candidate is not None
    assert result.candidate.identity_status == "likely_match"
    assert result.candidate.retrieval.source_label == "Needs confirmation"
    assert len(repo.profiles) == 1


@pytest.mark.asyncio
async def test_auto_discover_blocked_never_persisted() -> None:
    """Outcome 3: Automated fetch blocked by bot protection -> NOT persisted."""
    repo = FakeFounderRepository()

    diag = SourceDiagnostic(
        url="https://www.linkedin.com/in/asha-example",
        outcome="blocked_by_bot_protection",
        error_details="Cloudflare challenge encountered",
    )
    scraper = FakeScraper({"https://www.linkedin.com/in/asha-example": (None, diag)})

    use_case = AutoDiscoverFounderUseCase(
        repository=repo,
        scraper=scraper,
        page_fetcher=None,
        search_adapter=None,
    )

    result = await use_case.execute(
        founder_name="Asha Example",
        company_name="Example Corp",
        profile_url="https://www.linkedin.com/in/asha-example",
    )

    assert result.outcome == "blocked"
    assert result.persisted is False
    assert result.candidate is None
    assert len(repo.profiles) == 0


@pytest.mark.asyncio
async def test_auto_discover_no_url_found_never_persisted() -> None:
    """Outcome 4: No URL discovered across all tiers -> outcome not_found, NOT persisted."""
    repo = FakeFounderRepository()

    search_adapter = FakeSearchAdapter({})
    scraper = FakeScraper({})

    use_case = AutoDiscoverFounderUseCase(
        repository=repo,
        scraper=scraper,
        page_fetcher=None,
        search_adapter=search_adapter,
    )

    result = await use_case.execute(
        founder_name="Asha Example",
        company_name="Example Corp",
    )

    assert result.outcome == "not_found"
    assert result.persisted is False
    assert result.candidate is None
    assert len(repo.profiles) == 0


@pytest.mark.asyncio
async def test_same_name_different_company_never_auto_attaches() -> None:
    """CRITICAL RULE: Same person name at a different company must NEVER auto-attach or be saved."""
    repo = FakeFounderRepository()

    # Search returned another person with same name at a completely unrelated company
    search_adapter = FakeSearchAdapter({
        "Asha Example": [
            SearchResult(
                url="https://www.linkedin.com/in/asha-example-other",
                title="Asha Example - VP Sales - Unrelated Industry Corp | LinkedIn",
                snippet="Asha Example is VP Sales at Unrelated Industry Corp.",
                domain="linkedin.com",
            )
        ]
    })

    # Profile does NOT reference Example Corp anywhere
    unrelated_profile_dto = PersonProfile(
        name="Asha Example",
        headline="VP Sales at Unrelated Industry Corp",
        summary="Enterprise sales leader at Unrelated Industry Corp",
        experience=[{"title": "VP Sales", "company": "Unrelated Industry Corp"}],
        url="https://www.linkedin.com/in/asha-example-other",
    )
    diag = SourceDiagnostic(url="https://www.linkedin.com/in/asha-example-other", outcome="ok")
    scraper = FakeScraper({"https://www.linkedin.com/in/asha-example-other": (unrelated_profile_dto, diag)})

    use_case = AutoDiscoverFounderUseCase(
        repository=repo,
        scraper=scraper,
        page_fetcher=None,
        search_adapter=search_adapter,
    )

    result = await use_case.execute(
        founder_name="Asha Example",
        company_name="Example Corp",
        company_website="https://example.com",
    )

    # Must NOT auto-attach, must NOT be saved!
    assert result.outcome == "not_found"
    assert result.persisted is False
    assert result.candidate is None
    assert len(repo.profiles) == 0
