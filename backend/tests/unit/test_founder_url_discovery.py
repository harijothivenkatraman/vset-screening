"""Unit tests for FounderUrlDiscoveryService covering all 3 priority tiers:
1. User-confirmed / provided URL
2. Team/about page links adjacent to founder name
3. Public search candidate fallback
"""
import pytest
from app.application.services.founder_url_discovery import FounderUrlDiscoveryService
from app.domain.entities.discovery import PageContent


class TestFounderUrlDiscovery:
    def test_priority_1_user_confirmed_url_takes_precedence(self) -> None:
        """User-confirmed URL must take precedence over website and search."""
        confirmed = {"founder_linkedin_arpita_kapoor": "https://www.linkedin.com/in/arpita-user-confirmed"}
        pages = [
            PageContent(
                url="https://mysa.io/team",
                title="Team",
                description="",
                text="Arpita Kapoor is our CEO. Connect: https://www.linkedin.com/in/arpita-website",
                links=["https://www.linkedin.com/in/arpita-website"],
            )
        ]
        snippets = {"founder_arpita_kapoor": "Arpita Kapoor LinkedIn profile: https://www.linkedin.com/in/arpita-search"}

        res = FounderUrlDiscoveryService.discover_url(
            founder_name="Arpita Kapoor",
            company_name="Mysa",
            confirmed_urls=confirmed,
            website_pages=pages,
            search_snippets=snippets,
        )
        assert res.url == "https://www.linkedin.com/in/arpita-user-confirmed"
        assert res.source_type == "user_confirmed"

    def test_priority_2_website_team_page_near_founder_name(self) -> None:
        """Website team/about page link matching founder name must be discovered when no user URL is confirmed."""
        pages = [
            PageContent(
                url="https://mysa.io/team",
                title="Leadership Team",
                description="",
                text="Arpita Kapoor - Chief Executive Officer. Leading product vision and operational execution at Mysa.",
                links=["https://www.linkedin.com/in/arpita-kapoor-12345/"],
                social_links={"linkedin_person_arpita_kapoor": "https://www.linkedin.com/in/arpita-kapoor-12345/"},
            )
        ]
        snippets = {"founder_arpita_kapoor": "Search snippet: https://www.linkedin.com/in/arpita-search"}

        res = FounderUrlDiscoveryService.discover_url(
            founder_name="Arpita Kapoor",
            company_name="Mysa",
            confirmed_urls={},
            website_pages=pages,
            search_snippets=snippets,
        )
        assert res.url == "https://www.linkedin.com/in/arpita-kapoor-12345/"
        assert res.source_type == "website_near_name"
        assert res.source_page_url == "https://mysa.io/team"

    def test_priority_3_search_candidate_fallback(self) -> None:
        """When neither user nor website provides a URL, fall back to public search snippets."""
        pages = [
            PageContent(
                url="https://mysa.io/about",
                title="About",
                description="",
                text="Mysa is building financial infrastructure.",
                links=[],
            )
        ]
        snippets = {
            "founder_ashutosh_panigrahi": (
                "Ashutosh Panigrahi - Co-founder & CTO at Mysa | LinkedIn. "
                "View Ashutosh Panigrahi's profile on LinkedIn: https://www.linkedin.com/in/ashutosh-panigrahi-987"
            )
        }

        res = FounderUrlDiscoveryService.discover_url(
            founder_name="Ashutosh Panigrahi",
            company_name="Mysa",
            confirmed_urls={},
            website_pages=pages,
            search_snippets=snippets,
        )
        assert res.url == "https://www.linkedin.com/in/ashutosh-panigrahi-987"
        assert res.source_type == "search_discovery"

    def test_no_url_returns_none_status(self) -> None:
        """When no URL exists across all tiers, returns source_type='none' and url=None."""
        res = FounderUrlDiscoveryService.discover_url(
            founder_name="Unknown Founder",
            company_name="Mysa",
            confirmed_urls={},
            website_pages=[],
            search_snippets={},
        )
        assert res.url is None
        assert res.source_type == "none"
