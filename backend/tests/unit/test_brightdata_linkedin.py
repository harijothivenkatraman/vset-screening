"""Unit tests for BrightDataLinkedInScraper adapter."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import pytest

from app.config import Settings
from app.domain.entities.discovery import SourceDiagnostic
from app.infrastructure.discovery.scrapers.brightdata_linkedin import (
    BrightDataLinkedInScraper,
    map_brightdata_item_to_company_profile,
    map_brightdata_item_to_person_profile,
    normalize_linkedin_url,
)

SAMPLE_BRIGHTDATA_PERSON = {
    "name": "Jane Smith",
    "headline": "VP of Engineering at TechCorp",
    "about": "Engineering leader with 12+ years building distributed cloud platforms.",
    "avatar": "https://media.licdn.com/dms/image/jane.jpg",
    "city": "Bengaluru",
    "country": "India",
    "followers": 1500,
    "connections": 500,
    "experience": [
        {
            "title": "VP of Engineering",
            "company_name": "TechCorp",
            "duration": "2 yrs",
            "description": "Leading 50+ engineers across infrastructure and platform.",
            "start_date": "Jan 2024",
            "end_date": "Present",
            "is_current": True,
        },
        {
            "title": "Engineering Director",
            "company_name": "CloudScale",
            "duration": "3 yrs",
            "description": "Built scalable SaaS platform.",
            "start_date": "Jan 2021",
            "end_date": "Dec 2023",
            "is_current": False,
        },
    ],
    "education": [
        {
            "school_name": "Indian Institute of Technology, Madras",
            "degree": "B.Tech",
            "field_of_study": "Computer Science",
            "start_year": "2010",
            "end_year": "2014",
        }
    ],
    "skills": ["Distributed Systems", "Cloud Architecture", "Python"],
    "certifications": [
        {
            "name": "AWS Certified Solutions Architect",
            "issuer": "Amazon Web Services",
        }
    ],
    "languages": [
        {
            "name": "English",
            "proficiency": "Full professional",
        }
    ],
    "url": "https://www.linkedin.com/in/janesmith",
}

SAMPLE_BRIGHTDATA_COMPANY = {
    "name": "TechCorp",
    "about": "Global enterprise software provider.",
    "industry": "Software Development",
    "company_size": "500-1000",
    "headquarters": "San Francisco, CA",
    "website": "https://techcorp.com",
    "founded": "2015",
    "specialties": ["Enterprise Cloud", "AI Solutions"],
    "followers": 25000,
    "logo": "https://media.licdn.com/dms/image/techcorp-logo.jpg",
    "tagline": "Empowering Enterprise Velocity",
    "url": "https://www.linkedin.com/company/techcorp",
}


def test_normalize_linkedin_url() -> None:
    assert (
        normalize_linkedin_url("https://in.linkedin.com/in/janesmith/")
        == "https://www.linkedin.com/in/janesmith"
    )
    assert (
        normalize_linkedin_url("linkedin.com/in/janesmith")
        == "https://www.linkedin.com/in/janesmith"
    )
    assert normalize_linkedin_url("") == ""


def test_map_brightdata_item_to_person_profile() -> None:
    profile = map_brightdata_item_to_person_profile(
        SAMPLE_BRIGHTDATA_PERSON, fallback_url="https://www.linkedin.com/in/janesmith"
    )

    assert profile.name == "Jane Smith"
    assert profile.headline == "VP of Engineering at TechCorp"
    assert profile.summary == "Engineering leader with 12+ years building distributed cloud platforms."
    assert profile.location == "Bengaluru, India"
    assert profile.avatar_url == "https://media.licdn.com/dms/image/jane.jpg"
    assert profile.follower_count == 1500
    assert profile.connection_count == 500

    # Experience
    assert len(profile.experience) == 2
    assert profile.experience[0]["title"] == "VP of Engineering"
    assert profile.experience[0]["company"] == "TechCorp"
    assert profile.experience[0]["is_current"] is True
    assert profile.experience[1]["title"] == "Engineering Director"
    assert profile.experience[1]["is_current"] is False

    # Education
    assert len(profile.education) == 1
    assert profile.education[0]["school"] == "Indian Institute of Technology, Madras"
    assert profile.education[0]["degree"] == "B.Tech"
    assert profile.education[0]["year"] == "2014"

    # Skills, Certifications, Languages
    assert profile.skills == ["Distributed Systems", "Cloud Architecture", "Python"]
    assert profile.certifications == ["AWS Certified Solutions Architect - Amazon Web Services"]
    assert profile.languages == ["English (Full professional)"]
    assert profile.is_auth_walled is False


def test_map_brightdata_item_to_company_profile() -> None:
    company = map_brightdata_item_to_company_profile(
        SAMPLE_BRIGHTDATA_COMPANY, fallback_url="https://www.linkedin.com/company/techcorp"
    )

    assert company.name == "TechCorp"
    assert company.description == "Global enterprise software provider."
    assert company.industry == "Software Development"
    assert company.company_size == "500-1000"
    assert company.headquarters == "San Francisco, CA"
    assert company.website == "https://techcorp.com"
    assert company.founded_year == "2015"
    assert company.specialties == ["Enterprise Cloud", "AI Solutions"]
    assert company.followers == 25000
    assert company.logo_url == "https://media.licdn.com/dms/image/techcorp-logo.jpg"
    assert company.tagline == "Empowering Enterprise Velocity"
    assert company.is_auth_walled is False


@pytest.mark.asyncio
async def test_brightdata_scraper_successful_person_fetch() -> None:
    mock_client = MagicMock()
    mock_scrape = MagicMock()
    mock_linkedin = MagicMock()

    mock_client.scrape = mock_scrape
    mock_scrape.linkedin = mock_linkedin

    mock_result = MagicMock()
    mock_result.data = SAMPLE_BRIGHTDATA_PERSON
    mock_linkedin.profiles = AsyncMock(return_value=mock_result)

    scraper = BrightDataLinkedInScraper(
        token="test_brightdata_token_123",
        client=mock_client,
    )

    target_url = "https://www.linkedin.com/in/janesmith"
    profile, diag = await scraper.fetch_person_with_diagnostic(target_url)

    mock_linkedin.profiles.assert_awaited_once_with(url=target_url, timeout=180)
    assert profile is not None
    assert profile.name == "Jane Smith"
    assert diag.outcome == "ok"
    assert "name" in diag.fields_extracted
    assert "experience" in diag.fields_extracted
    assert "education" in diag.fields_extracted


@pytest.mark.asyncio
async def test_brightdata_scraper_successful_company_fetch() -> None:
    mock_client = MagicMock()
    mock_scrape = MagicMock()
    mock_linkedin = MagicMock()

    mock_client.scrape = mock_scrape
    mock_scrape.linkedin = mock_linkedin

    mock_result = MagicMock()
    mock_result.data = SAMPLE_BRIGHTDATA_COMPANY
    mock_linkedin.companies = AsyncMock(return_value=mock_result)

    scraper = BrightDataLinkedInScraper(
        token="test_brightdata_token_123",
        client=mock_client,
    )

    target_url = "https://www.linkedin.com/company/techcorp"
    company, diag = await scraper.fetch_company_with_diagnostic(target_url)

    mock_linkedin.companies.assert_awaited_once_with(url=target_url, timeout=180)
    assert company is not None
    assert company.name == "TechCorp"
    assert diag.outcome == "ok"
    assert "name" in diag.fields_extracted
    assert "industry" in diag.fields_extracted


@pytest.mark.asyncio
async def test_brightdata_scraper_missing_token_with_fallback() -> None:
    fallback = MagicMock()
    fallback.fetch_person_with_diagnostic = AsyncMock(
        return_value=(
            None,
            SourceDiagnostic(
                url="https://www.linkedin.com/in/janesmith",
                outcome="auth_wall",
            ),
        )
    )

    scraper = BrightDataLinkedInScraper(
        token=None,
        fallback_scraper=fallback,
    )

    profile, diag = await scraper.fetch_person_with_diagnostic("https://www.linkedin.com/in/janesmith")
    assert fallback.fetch_person_with_diagnostic.called
    assert diag.outcome == "auth_wall"


@pytest.mark.asyncio
async def test_brightdata_scraper_error_with_fallback() -> None:
    mock_client = MagicMock()
    mock_scrape = MagicMock()
    mock_linkedin = MagicMock()

    mock_client.scrape = mock_scrape
    mock_scrape.linkedin = mock_linkedin
    mock_linkedin.profiles = AsyncMock(side_effect=Exception("Bright Data 401 Unauthorized"))

    fallback = MagicMock()
    fallback.fetch_person_with_diagnostic = AsyncMock(
        return_value=(
            None,
            SourceDiagnostic(
                url="https://www.linkedin.com/in/janesmith",
                outcome="ok",
                fields_extracted=["name"],
            ),
        )
    )

    scraper = BrightDataLinkedInScraper(
        token="test_brightdata_token_123",
        client=mock_client,
        fallback_scraper=fallback,
    )

    profile, diag = await scraper.fetch_person_with_diagnostic("https://www.linkedin.com/in/janesmith")
    assert fallback.fetch_person_with_diagnostic.called
    assert diag.outcome == "ok"


@pytest.mark.asyncio
async def test_brightdata_scraper_error_without_fallback() -> None:
    mock_client = MagicMock()
    mock_scrape = MagicMock()
    mock_linkedin = MagicMock()

    mock_client.scrape = mock_scrape
    mock_scrape.linkedin = mock_linkedin
    mock_linkedin.profiles = AsyncMock(side_effect=Exception("Timeout connecting to Bright Data"))

    scraper = BrightDataLinkedInScraper(
        token="test_brightdata_token_123",
        client=mock_client,
        fallback_scraper=None,
    )

    profile, diag = await scraper.fetch_person_with_diagnostic("https://www.linkedin.com/in/janesmith")
    assert profile is None
    assert diag.outcome == "brightdata_error"


def test_settings_brightdata_token_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BRIGHTDATA_API_TOKEN", raising=False)
    monkeypatch.setenv("BRIGHTDATA_API_KEY", "custom_key_from_env_32chars_test")
    settings = Settings(BRIGHTDATA_API_TOKEN=None, _env_file=None)
    assert settings.BRIGHTDATA_API_TOKEN == "custom_key_from_env_32chars_test"
