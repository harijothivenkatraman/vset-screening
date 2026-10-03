"""Tests verifying parsers, fetchers, and security guards against saved offline fixtures.

NO LIVE NETWORK calls are made in this module.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from app.domain.entities.discovery import PageContent
from app.infrastructure.discovery.http.ssrf_guard import (
    FORBIDDEN_FETCH_DOMAINS,
    is_forbidden_fetch_domain,
)
from app.infrastructure.discovery.scrapers.linkedin_public import (
    LinkedInPublicScraper,
)
from app.infrastructure.discovery.scrapers.website_fetcher import (
    extract_page_content,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


class TestLinkedInSavedFixtures:
    def setup_method(self) -> None:
        self.scraper = LinkedInPublicScraper()

    def test_auth_walled_linkedin_page_detected(self) -> None:
        """Auth-walled page must be identified with is_auth_walled=True and not raise."""
        html = (FIXTURES_DIR / "linkedin_auth_walled.html").read_text(encoding="utf-8")
        profile = self.scraper.parse_company_html("https://www.linkedin.com/company/auth-blocked", html)
        assert profile.is_auth_walled is True
        assert profile.name is None

    def test_sparse_small_company_linkedin_page(self) -> None:
        """Sparse small-company profile extracts name/description; industry is not 'LinkedIn'."""
        html = (FIXTURES_DIR / "linkedin_company_sparse.html").read_text(encoding="utf-8")
        profile = self.scraper.parse_company_html("https://www.linkedin.com/company/tinyseed-labs", html)
        assert profile.is_auth_walled is False
        assert profile.name == "TinySeed Labs"
        assert "Bootstrapped developer tools" in (profile.description or "")
        # Critical regression test: industry must NEVER be "LinkedIn"
        assert profile.industry != "LinkedIn"

    def test_linkedin_person_jobtitle_as_list(self) -> None:
        """Person profile with jobTitle as list[str] parses cleanly without crashing."""
        html = (FIXTURES_DIR / "linkedin_person_jobtitle_list.html").read_text(encoding="utf-8")
        person = self.scraper.parse_person_html("https://www.linkedin.com/in/alice-chen", html)
        assert person.is_auth_walled is False
        assert person.name == "Alice Chen"
        assert "CEO & Co-founder" in (person.headline or "")
        assert "Austin" in (person.location or "")

    def test_linkedin_person_jobtitle_as_str(self) -> None:
        """Person profile with jobTitle as str parses cleanly."""
        html = (FIXTURES_DIR / "linkedin_person_jobtitle_str.html").read_text(encoding="utf-8")
        person = self.scraper.parse_person_html("https://www.linkedin.com/in/bob-vance", html)
        assert person.is_auth_walled is False
        assert person.name == "Bob Vance"
        assert person.headline == "Chief Technology Officer"
        assert "Austin" in (person.location or "")

    def test_linkedin_company_with_signin_modal_not_flagged_authwall(self) -> None:
        """Normal LinkedIn company page with sign-in modals parses without auth_wall."""
        html = (FIXTURES_DIR / "linkedin_company_with_signin_modal.html").read_text(encoding="utf-8")
        profile = self.scraper.parse_company_html("https://www.linkedin.com/company/mysa", html)
        assert profile.is_auth_walled is False
        assert profile.name == "Mysa"
        assert profile.founded_year == "2023"
        assert profile.headquarters == "Bengaluru, India"
        assert profile.company_size == "11-50 employees"
        assert profile.website == "https://mysa.io"

    def test_normalize_regional_linkedin_subdomains(self) -> None:
        """Regional subdomains (in., uk., ca., etc.) are normalized to www.linkedin.com."""
        from app.infrastructure.discovery.scrapers.linkedin_public import normalize_linkedin_url
        assert normalize_linkedin_url("https://in.linkedin.com/company/mysa-io") == "https://www.linkedin.com/company/mysa-io"
        assert normalize_linkedin_url("https://uk.linkedin.com/in/john-doe") == "https://www.linkedin.com/in/john-doe"
        assert normalize_linkedin_url("https://ca.linkedin.com/company/acme") == "https://www.linkedin.com/company/acme"
        assert normalize_linkedin_url("https://www.linkedin.com/company/mysa-io") == "https://www.linkedin.com/company/mysa-io"


class TestWebsiteSavedFixtures:
    def test_healthy_website_extraction(self) -> None:
        """Rich website page extracts JSON-LD, OG tags, navigation links, and social profiles."""
        html = (FIXTURES_DIR / "website_healthy.html").read_text(encoding="utf-8")
        page = extract_page_content("https://acme-tech.example.com", html)

        assert "Acme Technologies" in page.title
        assert "smart iot hardware" in page.description.lower()
        assert "Intelligent Energy Optimization" in page.text

        # JSON-LD verification
        assert len(page.json_ld) >= 1
        org_data = next((item for item in page.json_ld if item.get("@type") == "Organization"), None)
        assert org_data is not None
        assert org_data.get("name") == "Acme Technologies Inc"
        assert org_data.get("foundingDate") == "2021-04-15"
        assert "CleanTech" in org_data.get("knowsAbout", [])

        # Links and social discovery
        assert any("/about" in l for l in page.links)
        assert "linkedin" in page.social_links
        assert "github" in page.social_links
        assert "linkedin.com/company/acme-technologies-real" in page.social_links["linkedin"]

    def test_js_only_website_extraction(self) -> None:
        """JS-only website produces minimal text without crashing and noscript boilerplate stripped."""
        html = (FIXTURES_DIR / "website_js_only.html").read_text(encoding="utf-8")
        page = extract_page_content("https://spa.example.com", html)
        assert page.title == "Single Page App"
        # Noscript was decomposed so no product text or usable descriptions
        assert len(page.json_ld) == 0
        assert not any(kw in page.text.lower() for kw in ["product", "about", "solution", "company"])

    def test_mysa_boilerplate_and_widget_stripping(self) -> None:
        """Chat widgets, cookie banners, form error states stripped from mysa.io HTML."""
        html = (FIXTURES_DIR / "mysa_with_widget.html").read_text(encoding="utf-8")
        page = extract_page_content("https://mysa.io", html)

        # Useful content preserved
        assert "Automate Finance Operations with AI" in page.text
        assert "Accounts Payable" in page.text
        assert len(page.json_ld) >= 1

        # Chat widget completely stripped (no Arnav or online now)
        text_lower = page.text.lower()
        assert "arnav" not in text_lower
        assert "online now" not in text_lower
        assert "expert is available" not in text_lower

        # Cookie banner stripped
        assert "accept all cookies" not in text_lower
        assert "cookie policy" not in text_lower

        # Webflow form error stripped
        assert "something went wrong" not in text_lower

        # Discovered company LinkedIn preserved
        assert page.social_links.get("linkedin") == "https://in.linkedin.com/company/mysa-io"

    def test_canonicalize_url(self) -> None:
        """URLs are canonicalized: www stripped, trailing slash removed, query/fragment stripped."""
        from app.infrastructure.discovery.scrapers.normalizer import canonicalize_url
        assert canonicalize_url("https://www.mysa.io/") == "https://mysa.io"
        assert canonicalize_url("https://mysa.io") == "https://mysa.io"
        assert canonicalize_url("https://mysa.io/about/?utm_source=twitter#team") == "https://mysa.io/about"
        assert canonicalize_url("https://www.mysa.io/product/") == "https://mysa.io/product"
        assert canonicalize_url("http://dimdot.com/") == "http://dimdot.com"


class TestSearchSavedFixtures:
    def test_empty_search_results_json(self) -> None:
        """Empty search results payload loads as empty list without exception."""
        raw = (FIXTURES_DIR / "empty_search_results.json").read_text(encoding="utf-8")
        results = json.loads(raw)
        assert isinstance(results, list)
        assert len(results) == 0


class TestDomainDenylistFixtures:
    def test_forbidden_fetch_domains(self) -> None:
        """Forbidden directories (Crunchbase, PitchBook, G2, etc.) are strictly blocked from direct fetch."""
        blocked_urls = [
            "https://www.crunchbase.com/organization/mysa",
            "https://crunchbase.com/person/josh-green",
            "https://www.pitchbook.com/profiles/company/12345",
            "https://zoominfo.com/c/acme/123",
            "https://www.g2.com/products/mysa/reviews",
            "https://tracxn.com/d/companies/mysa",
            "https://www.trustpilot.com/review/mysa.com",
        ]
        for url in blocked_urls:
            assert is_forbidden_fetch_domain(url) is True, f"Expected {url} to be blocked"

        allowed_urls = [
            "https://mysa.io",
            "https://mysa.io/about",
            "https://linkedin.com/company/mysa",
            "https://github.com/mysa",
            "https://dimdot.com",
        ]
        for url in allowed_urls:
            assert is_forbidden_fetch_domain(url) is False, f"Expected {url} to be allowed"


class TestCrawlerDeduplication:
    @pytest.mark.asyncio
    async def test_spa_catch_all_deduplicated_with_warning(self) -> None:
        """Identical page bodies (e.g. dimdot.com SPA) are detected as duplicate_of:<first> and raise SPA warning."""
        from unittest.mock import AsyncMock
        from app.domain.entities.discovery import DiscoveryJob, Evidence, SourceDiagnostic
        from app.application.services.build_report import BuildReportService

        spa_html = "<html><head><title>Dimdot App</title></head><body><div id='root'>Loading...</div></body></html>"
        spa_page = extract_page_content("https://dimdot.com", spa_html)

        # Mock page fetcher returning the exact same page for every URL
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch_with_diagnostic.side_effect = lambda u: (
            extract_page_content(u, spa_html),
            SourceDiagnostic(url=u, outcome="ok", bytes_fetched=9609, fields_extracted=["title"]),
        )
        mock_fetcher.fetch_sitemap_urls.return_value = []

        service = BuildReportService(
            job_store=AsyncMock(),
            page_fetcher=mock_fetcher,
            profile_scraper=AsyncMock(),
            report_extractor=AsyncMock(),
            report_import=AsyncMock(),
        )

        from datetime import datetime, timezone
        from app.domain.entities.discovery import JobState

        now = datetime.now(timezone.utc)
        job = DiscoveryJob(
            id="job-spa-test",
            company_name="Dimdot",
            founder_names=["Founder"],
            state=JobState.RUNNING,
            stage="Fetching website",
            progress=0.1,
            warnings=[],
            result_slug=None,
            created_at=now,
            updated_at=now,
            confirmed_urls={"website": "https://dimdot.com"},
        )
        evidence = Evidence()

        await service._fetch_website(job, evidence)

        # 1. Exactly ONE distinct page registered in evidence
        assert len(evidence.website_pages) == 1
        assert evidence.website_pages[0].url == "https://dimdot.com"

        # 2. Exactly ONE website source registered
        assert len(evidence.sources) == 1
        assert evidence.sources[0].url == "https://dimdot.com"

        # 3. Subpage diagnostics marked duplicate_of:https://dimdot.com
        dup_diags = [d for d in job.diagnostics if d.outcome.startswith("duplicate_of:")]
        assert len(dup_diags) >= 2
        for d in dup_diags:
            assert d.outcome == "duplicate_of:https://dimdot.com"

        # 4. SPA warning recorded
        assert any("JavaScript-rendered" in w for w in job.warnings)
        assert any("JavaScript-rendered" in w for w in evidence.warnings)
