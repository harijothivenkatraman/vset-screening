"""Unit tests for ApifyLinkedInScraper adapter."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import pytest

from app.domain.entities.discovery import SourceDiagnostic
from app.infrastructure.discovery.scrapers.apify_linkedin import (
    ApifyLinkedInScraper,
    map_apify_item_to_person_profile,
    normalize_linkedin_url,
)

SAMPLE_APIFY_ITEM = {
    "id": "ACoAACLevxsBfWQoDUYkHyCP2jzl81cDAvckQEI",
    "publicIdentifier": "towhid-rahman",
    "linkedinUrl": "https://www.linkedin.com/in/towhid-rahman",
    "firstName": "Towhid",
    "lastName": "Rahman",
    "headline": "Pharmacology | Project Management | Leadership",
    "about": "Over eight years of experience in pharmacology and project management.",
    "photo": "https://media.licdn.com/photo.jpg",
    "followerCount": 264,
    "connectionsCount": 261,
    "location": {
        "linkedinText": "Los Angeles, California, United States",
        "countryCode": "US",
    },
    "experience": [
        {
            "position": "Staff Pharmacist",
            "companyName": "CVS Health",
            "duration": "1 yr 7 mos",
            "description": "Exceeded daily production targets by 15%.",
            "startDate": {"month": "Jan", "year": 2024, "text": "Jan 2024"},
            "endDate": {"text": "Present"},
        },
        {
            "position": "Support Pharmacist",
            "companyName": "CVS Health",
            "duration": "1 yr 2 mos",
            "description": "Collaborated with over 30 pharmacy teams.",
            "startDate": {"month": "Nov", "year": 2022, "text": "Nov 2022"},
            "endDate": {"month": "Dec", "year": 2023, "text": "Dec 2023"},
        },
    ],
    "education": [
        {
            "schoolName": "Western University of Health Sciences",
            "degree": "Doctor of Pharmacy",
            "fieldOfStudy": "Pharmacy",
            "startDate": {"month": "Aug", "year": 2018, "text": "Aug 2018"},
            "endDate": {"month": "May", "year": 2022, "text": "May 2022"},
        }
    ],
    "skills": [
        {"name": "Pharmacology"},
        {"name": "Project Management"},
    ],
    "certifications": [
        {
            "title": "Excel Essential Training",
            "issuedBy": "LinkedIn",
        }
    ],
    "languages": [
        {
            "name": "English",
            "proficiency": "Full professional proficiency",
        }
    ],
    "status": 200,
}


def test_normalize_linkedin_url() -> None:
    assert normalize_linkedin_url("https://in.linkedin.com/in/test-user/") == "https://www.linkedin.com/in/test-user"
    assert normalize_linkedin_url("linkedin.com/in/test-user") == "https://www.linkedin.com/in/test-user"
    assert normalize_linkedin_url("") == ""


def test_map_apify_item_to_person_profile() -> None:
    profile = map_apify_item_to_person_profile(SAMPLE_APIFY_ITEM, fallback_url="https://www.linkedin.com/in/towhid-rahman")

    assert profile.name == "Towhid Rahman"
    assert profile.headline == "Pharmacology | Project Management | Leadership"
    assert profile.summary == "Over eight years of experience in pharmacology and project management."
    assert profile.location == "Los Angeles, California, United States"
    assert profile.follower_count == 264
    assert profile.connection_count == 261
    assert profile.avatar_url == "https://media.licdn.com/photo.jpg"

    # Experiences
    assert len(profile.experience) == 2
    assert profile.experience[0]["title"] == "Staff Pharmacist"
    assert profile.experience[0]["company"] == "CVS Health"
    assert profile.experience[0]["start"] == "Jan 2024"
    assert profile.experience[0]["end"] == "Present"
    assert profile.experience[0]["is_current"] is True

    assert profile.experience[1]["title"] == "Support Pharmacist"
    assert profile.experience[1]["start"] == "Nov 2022"
    assert profile.experience[1]["end"] == "Dec 2023"
    assert profile.experience[1]["is_current"] is False

    # Education
    assert len(profile.education) == 1
    assert profile.education[0]["school"] == "Western University of Health Sciences"
    assert profile.education[0]["degree"] == "Doctor of Pharmacy"
    assert profile.education[0]["year"] == "2022"

    # Skills & Certifications & Languages
    assert profile.skills == ["Pharmacology", "Project Management"]
    assert profile.certifications == ["Excel Essential Training - LinkedIn"]
    assert profile.languages == ["English (Full professional proficiency)"]
    assert profile.is_auth_walled is False


def test_map_apify_item_fallback_and_top_skills() -> None:
    item = {
        "name": "Jane Doe",
        "headline": "Founder",
        "topSkills": "Leadership • Strategy",
        "skills": [],
        "certifications": ["PMP"],
        "languages": ["English"],
    }
    profile = map_apify_item_to_person_profile(item, fallback_url="https://www.linkedin.com/in/janedoe")

    assert profile.name == "Jane Doe"
    assert profile.skills == ["Leadership", "Strategy"]
    assert profile.certifications == ["PMP"]
    assert profile.languages == ["English"]


@pytest.mark.asyncio
async def test_apify_scraper_successful_fetch() -> None:
    mock_client = MagicMock()
    mock_actor = MagicMock()
    mock_dataset = MagicMock()

    mock_client.actor.return_value = mock_actor
    mock_client.dataset.return_value = mock_dataset

    # Run result mock
    mock_run = MagicMock()
    mock_run.default_dataset_id = "dataset_xyz"
    mock_actor.call = AsyncMock(return_value=mock_run)

    # Dataset list_items mock
    mock_page = MagicMock()
    mock_page.items = [SAMPLE_APIFY_ITEM]
    mock_dataset.list_items = AsyncMock(return_value=mock_page)

    scraper = ApifyLinkedInScraper(
        token="test_token",
        client=mock_client,
    )

    target_url = "https://www.linkedin.com/in/towhid-rahman"
    profile, diag = await scraper.fetch_person_with_diagnostic(target_url)

    # Verify Actor call parameters match the exact schema
    mock_actor.call.assert_awaited_once_with(
        run_input={
            "profileScraperMode": "Profile details no email ($4 per 1k)",
            "queries": [target_url],
        }
    )

    assert profile is not None
    assert profile.name == "Towhid Rahman"
    assert diag.outcome == "ok"
    assert "name" in diag.fields_extracted
    assert "experience" in diag.fields_extracted
    assert "education" in diag.fields_extracted
    assert "skills" in diag.fields_extracted


@pytest.mark.asyncio
async def test_apify_scraper_empty_dataset() -> None:
    mock_client = MagicMock()
    mock_actor = MagicMock()
    mock_dataset = MagicMock()

    mock_client.actor.return_value = mock_actor
    mock_client.dataset.return_value = mock_dataset

    mock_run = MagicMock()
    mock_run.default_dataset_id = "dataset_empty"
    mock_actor.call = AsyncMock(return_value=mock_run)

    mock_page = MagicMock()
    mock_page.items = []
    mock_dataset.list_items = AsyncMock(return_value=mock_page)

    scraper = ApifyLinkedInScraper(
        token="test_token",
        client=mock_client,
    )

    profile, diag = await scraper.fetch_person_with_diagnostic("https://www.linkedin.com/in/notfound")

    assert profile is None
    assert diag.outcome == "not_found"


@pytest.mark.asyncio
async def test_apify_scraper_missing_token_with_fallback() -> None:
    fallback_scraper = MagicMock()
    fallback_scraper.fetch_person_with_diagnostic = AsyncMock(
        return_value=(
            None,
            SourceDiagnostic(
                url="https://www.linkedin.com/in/someone",
                outcome="auth_wall",
                bytes_fetched=0,
            ),
        )
    )

    scraper = ApifyLinkedInScraper(
        token=None,
        fallback_scraper=fallback_scraper,
    )

    profile, diag = await scraper.fetch_person_with_diagnostic("https://www.linkedin.com/in/someone")

    assert fallback_scraper.fetch_person_with_diagnostic.called
    assert diag.outcome == "auth_wall"


@pytest.mark.asyncio
async def test_apify_scraper_error_with_fallback() -> None:
    mock_client = MagicMock()
    mock_actor = MagicMock()
    mock_client.actor.return_value = mock_actor

    mock_actor.call = AsyncMock(side_effect=Exception("Apify 429 Rate limit exceeded"))

    fallback_scraper = MagicMock()
    fallback_scraper.fetch_person_with_diagnostic = AsyncMock(
        return_value=(
            None,
            SourceDiagnostic(
                url="https://www.linkedin.com/in/someone",
                outcome="auth_wall",
                bytes_fetched=0,
            ),
        )
    )

    scraper = ApifyLinkedInScraper(
        token="test_token",
        client=mock_client,
        fallback_scraper=fallback_scraper,
    )

    profile, diag = await scraper.fetch_person_with_diagnostic("https://www.linkedin.com/in/someone")

    assert fallback_scraper.fetch_person_with_diagnostic.called
    assert diag.outcome == "auth_wall"


@pytest.mark.asyncio
async def test_apify_scraper_error_without_fallback() -> None:
    mock_client = MagicMock()
    mock_actor = MagicMock()
    mock_client.actor.return_value = mock_actor

    mock_actor.call = AsyncMock(side_effect=Exception("Unauthorized: invalid token"))

    scraper = ApifyLinkedInScraper(
        token="invalid_token",
        client=mock_client,
        fallback_scraper=None,
    )

    profile, diag = await scraper.fetch_person_with_diagnostic("https://www.linkedin.com/in/someone")

    assert profile is None
    assert diag.outcome == "apify_unauthorized"
