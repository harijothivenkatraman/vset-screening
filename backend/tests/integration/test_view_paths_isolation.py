"""Test that GET/view endpoints never invoke scrapers, search adapters, or LLMs."""
from unittest.mock import patch
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_get_view_paths_never_call_scrapers_or_llm() -> None:
    """Requirement 7a: GET/view paths never call scrapers, search, or LLM.

    This test asserts that calls to any view/read endpoints will fail immediately
    if any scraper, search adapter, or LLM method is invoked.
    """
    error_msg = "VIOLATION: Scraper, search, or LLM invoked during GET/view path!"

    def forbidden_call(*args: object, **kwargs: object) -> None:
        raise AssertionError(error_msg)

    async def async_forbidden_call(*args: object, **kwargs: object) -> None:
        raise AssertionError(error_msg)

    with (
        patch("app.infrastructure.discovery.scrapers.linkedin_public.LinkedInPublicScraper.fetch_person", side_effect=async_forbidden_call),
        patch("app.infrastructure.discovery.scrapers.linkedin_public.LinkedInPublicScraper.fetch_company", side_effect=async_forbidden_call),
        patch("app.infrastructure.discovery.scrapers.website_fetcher.WebsiteFetcherAdapter.fetch", side_effect=async_forbidden_call),
        patch("app.infrastructure.discovery.search.duckduckgo_search.DuckDuckGoSearchAdapter.search", side_effect=async_forbidden_call),
        patch("app.infrastructure.discovery.search.searxng_search.SearXNGSearchAdapter.search", side_effect=async_forbidden_call),
        patch("app.infrastructure.discovery.llm.openai_compatible.OpenAICompatibleLlmAdapter.complete", side_effect=async_forbidden_call),
        patch("app.infrastructure.discovery.llm.report_extractor.SectionBySectionExtractor.extract", side_effect=async_forbidden_call),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Company list
            resp = await client.get("/api/v1/companies")
            assert resp.status_code == 200

            # 2. Company summary
            resp = await client.get("/api/v1/companies/mysa")
            assert resp.status_code == 200

            # 3. Sections list
            resp = await client.get("/api/v1/companies/mysa/sections")
            assert resp.status_code == 200

            # 4. Specific section: company
            resp = await client.get("/api/v1/companies/mysa/sections/company")
            assert resp.status_code == 200

            # 5. Specific section: team
            resp = await client.get("/api/v1/companies/mysa/sections/team")
            assert resp.status_code == 200

            # 6. Specific section: founder_profiles (returns 200 or 404 if not present in reference)
            resp = await client.get("/api/v1/companies/mysa/sections/founder_profiles")
            assert resp.status_code in (200, 404)

            # 7. Sources
            resp = await client.get("/api/v1/companies/mysa/sources")
            assert resp.status_code == 200

            # 8. Actions
            resp = await client.get("/api/v1/companies/mysa/actions")
            assert resp.status_code == 200
