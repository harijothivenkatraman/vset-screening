"""Unit tests for public scrapers and normalizers."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from app.infrastructure.discovery.http.rate_limiter import HostRateLimiter
from app.infrastructure.discovery.scrapers.linkedin_public import LinkedInPublicScraper
from app.infrastructure.discovery.scrapers.normalizer import (
    clean_text,
    clean_url,
    deduplicate_list,
    extract_year,
)
from app.infrastructure.discovery.scrapers.website_fetcher import WebsiteFetcherAdapter


PERSON_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta property="og:title" content="Jane Doe - Co-Founder & CEO | LinkedIn">
  <meta property="og:description" content="Experienced founder in enterprise AI.">
  <meta property="og:image" content="https://media.licdn.com/avatar.jpg">
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Person",
    "name": "Jane Doe",
    "jobTitle": "Co-Founder & CEO",
    "description": "Building next-generation enterprise AI agents.",
    "address": {
      "addressLocality": "Bengaluru",
      "addressCountry": "India"
    },
    "alumniOf": [
      {
        "@type": "EducationalOrganization",
        "name": "IIT Madras",
        "description": "B.Tech Computer Science (2018)"
      }
    ],
    "worksFor": [
      {
        "@type": "Organization",
        "name": "Acme AI",
        "jobTitle": "CEO"
      }
    ]
  }
  </script>
</head>
<body><h1>Jane Doe</h1></body>
</html>
"""

COMPANY_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta property="og:title" content="Acme AI | LinkedIn">
  <meta property="og:description" content="AI infrastructure platform.">
  <meta property="og:image" content="https://media.licdn.com/logo.png">
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "Acme AI",
    "description": "High-performance AI platform.",
    "url": "https://acme.ai",
    "foundingDate": "2023",
    "numberOfEmployees": {"name": "11-50"},
    "address": {
      "addressLocality": "San Francisco",
      "addressCountry": "United States"
    }
  }
  </script>
</head>
<body><h1>Acme AI</h1></body>
</html>
"""


class TestNormalizer:
    def test_clean_url(self) -> None:
        raw = "HTTPS://WWW.EXAMPLE.COM/path/?utm_source=twitter&utm_medium=cpc&keep=1#fragment"
        cleaned = clean_url(raw)
        assert cleaned == "https://www.example.com/path?keep=1"

    def test_clean_text(self) -> None:
        raw = "Smart \u201cquotes\u201d and   extra   spaces\n\n\n\nNew line"
        cleaned = clean_text(raw)
        assert cleaned == 'Smart "quotes" and extra spaces\n\nNew line'

    def test_extract_year(self) -> None:
        assert extract_year("Founded in 2021.") == "2021"
        assert extract_year("2015-08-12") == "2015"
        assert extract_year("No year here") is None

    def test_deduplicate_list(self) -> None:
        items = ["Apple", "banana", "apple", "Banana", "Cherry"]
        assert deduplicate_list(items) == ["Apple", "banana", "Cherry"]


class TestLinkedInPublicScraper:
    async def test_parse_person_profile(self) -> None:
        scraper = LinkedInPublicScraper(rate_limiter=HostRateLimiter(min_interval_seconds=0))

        with patch.object(scraper, "_fetch_html", return_value=(200, "https://linkedin.com/in/janedoe", PERSON_HTML, False)):
            profile = await scraper.fetch_person("https://linkedin.com/in/janedoe")
            assert profile is not None
            assert not profile.is_auth_walled
            assert profile.name == "Jane Doe"
            assert "Co-Founder & CEO" in (profile.headline or "")
            assert profile.location == "Bengaluru, India"
            assert len(profile.education) == 1
            assert profile.education[0]["institution"] == "IIT Madras"
            assert len(profile.experience) == 1
            assert profile.experience[0]["company"] == "Acme AI"

    async def test_parse_company_profile(self) -> None:
        scraper = LinkedInPublicScraper(rate_limiter=HostRateLimiter(min_interval_seconds=0))

        with patch.object(scraper, "_fetch_html", return_value=(200, "https://linkedin.com/company/acme-ai", COMPANY_HTML, False)):
            profile = await scraper.fetch_company("https://linkedin.com/company/acme-ai")
            assert profile is not None
            assert not profile.is_auth_walled
            assert profile.name == "Acme AI"
            assert profile.website == "https://acme.ai"
            assert profile.founded_year == "2023"
            assert profile.company_size == "11-50"
            assert profile.headquarters == "San Francisco, United States"

    async def test_authwall_detection(self) -> None:
        scraper = LinkedInPublicScraper(rate_limiter=HostRateLimiter(min_interval_seconds=0))

        with patch.object(scraper, "_fetch_html", return_value=(999, "https://linkedin.com/authwall", "Sign In", True, False)):
            profile, diag = await scraper.fetch_company_with_diagnostic("https://linkedin.com/company/secret")
            assert profile is not None
            assert profile.is_auth_walled is True
            assert diag.outcome == "auth_wall"

    async def test_bot_protection_detection(self) -> None:
        from app.infrastructure.discovery.scrapers.linkedin_public import LinkedInCircuitBreaker
        breaker = LinkedInCircuitBreaker(failure_threshold=3)
        scraper = LinkedInPublicScraper(rate_limiter=HostRateLimiter(min_interval_seconds=0), circuit_breaker=breaker)

        html_cf = "<html><head><title>Just a moment...</title></head><body>challenges.cloudflare.com</body></html>"
        with patch.object(scraper, "_fetch_html", return_value=(403, "https://linkedin.com/company/blocked", html_cf, True, True)):
            profile, diag = await scraper.fetch_company_with_diagnostic("https://linkedin.com/company/blocked")
            assert profile is not None
            assert profile.is_auth_walled is True
            assert diag.outcome == "blocked_by_bot_protection"
            assert "Cloudflare" in (diag.error_details or "")

    async def test_circuit_breaker_opens_after_3_blocks(self) -> None:
        from app.infrastructure.discovery.scrapers.linkedin_public import LinkedInCircuitBreaker
        breaker = LinkedInCircuitBreaker(failure_threshold=3, cooldown_seconds=1800.0)
        scraper = LinkedInPublicScraper(rate_limiter=HostRateLimiter(min_interval_seconds=0), circuit_breaker=breaker)

        html_cf = "Just a moment... challenges.cloudflare.com"
        with patch.object(scraper, "_fetch_html", return_value=(403, "https://linkedin.com/company/blocked", html_cf, True, True)):
            # 3 consecutive blocks
            for _ in range(3):
                _, diag = await scraper.fetch_company_with_diagnostic("https://linkedin.com/company/blocked")
                assert diag.outcome == "blocked_by_bot_protection"

            # 4th call: circuit breaker is open!
            _, diag4 = await scraper.fetch_company_with_diagnostic("https://linkedin.com/company/blocked")
            assert diag4.outcome == "circuit_breaker_open"
            assert "circuit breaker open" in (diag4.error_details or "")


class TestWebsiteFetcher:
    async def test_fetch_extracts_clean_text(self) -> None:
        html = """
        <html>
        <head>
          <title>Acme Inc | Home</title>
          <meta name="description" content="Leading robotics startup.">
        </head>
        <body>
          <nav><a href="/">Nav Item</a></nav>
          <h1>Welcome to Acme</h1>
          <p>We build autonomous robots for precision logistics.</p>
          <script>console.log("analytics");</script>
          <footer>Copyright 2026</footer>
        </body>
        </html>
        """
        fetcher = WebsiteFetcherAdapter(
            rate_limiter=HostRateLimiter(min_interval_seconds=0),
            check_robots=False,
            validate_ssrf_dns=False,
        )

        class MockStreamResponse:
            status_code = 200
            headers = {"content-type": "text/html; charset=utf-8"}
            encoding = "utf-8"

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def aiter_bytes(self):
                yield html.encode("utf-8")

        mock_client = MagicMock()
        mock_client.stream.return_value = MockStreamResponse()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("httpx.AsyncClient", return_value=mock_client):
            page = await fetcher.fetch("https://acme.io")
            assert page is not None
            assert page.title == "Acme Inc | Home"
            assert page.description == "Leading robotics startup."
            assert "Welcome to Acme" in page.text
            assert "We build autonomous robots" in page.text
            assert "analytics" not in page.text
            assert "Nav Item" not in page.text
            assert "Copyright" not in page.text

    async def test_ssrf_blocked_returns_none(self) -> None:
        fetcher = WebsiteFetcherAdapter()
        page = await fetcher.fetch("http://127.0.0.1/admin")
        assert page is None
