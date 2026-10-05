"""Tests verifying robust parsing across all public profile HTML fixture variants."""
from __future__ import annotations

from pathlib import Path
import pytest

from app.infrastructure.discovery.scrapers.linkedin_public import LinkedInPublicScraper

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture
def scraper() -> LinkedInPublicScraper:
    return LinkedInPublicScraper()


def test_parse_full_jsonld(scraper: LinkedInPublicScraper) -> None:
    html = (FIXTURES_DIR / "public_profile_full_jsonld.html").read_text(encoding="utf-8")
    profile = scraper.parse_person_html("https://www.linkedin.com/in/asha-example", html)

    assert profile.name == "Asha Example"
    assert "Chief Executive Officer" in (profile.headline or "")
    assert profile.location == "Bengaluru, India"
    assert len(profile.experience) == 2
    assert profile.experience[0]["company"] == "Example Corp"
    assert profile.experience[1]["company"] == "PriorTech Labs"
    assert len(profile.education) == 1
    assert profile.education[0]["institution"] == "Indian Institute of Technology Madras"
    assert profile.education[0]["year"] == "2015"
    assert profile.is_auth_walled is False


def test_parse_sparse_jsonld(scraper: LinkedInPublicScraper) -> None:
    html = (FIXTURES_DIR / "public_profile_sparse_jsonld.html").read_text(encoding="utf-8")
    profile = scraper.parse_person_html("https://www.linkedin.com/in/asha-example", html)

    assert profile.name == "Asha Example"
    assert profile.headline == "Co-Founder at Example Corp"
    assert profile.is_auth_walled is False


def test_parse_og_only(scraper: LinkedInPublicScraper) -> None:
    html = (FIXTURES_DIR / "public_profile_og_only.html").read_text(encoding="utf-8")
    profile = scraper.parse_person_html("https://www.linkedin.com/in/asha-example", html)

    assert profile.name == "Asha Example"
    assert "Founder & Managing Director" in (profile.headline or "")
    assert profile.avatar_url == "https://static.licdn.com/media/example-avatar.jpg"
    assert profile.is_auth_walled is False


def test_parse_list_string_variants(scraper: LinkedInPublicScraper) -> None:
    html = (FIXTURES_DIR / "public_profile_list_string_variants.html").read_text(encoding="utf-8")
    profile = scraper.parse_person_html("https://www.linkedin.com/in/asha-example", html)

    assert profile.name == "Asha Example"
    assert "Founder" in (profile.headline or "")
    assert len(profile.experience) == 2
    assert profile.experience[0]["company"] == "Example Corp"
    assert profile.experience[1]["company"] == "Pioneer Labs"
    assert len(profile.education) == 2
    assert profile.education[0]["institution"] == "Oxford University"
    assert profile.education[1]["institution"] == "Cambridge University"
    assert profile.location == "Berlin"
    assert profile.is_auth_walled is False


def test_parse_missing_dates(scraper: LinkedInPublicScraper) -> None:
    html = (FIXTURES_DIR / "public_profile_missing_dates.html").read_text(encoding="utf-8")
    profile = scraper.parse_person_html("https://www.linkedin.com/in/asha-example", html)

    assert profile.name == "Asha Example"
    assert profile.headline == "Co-Founder"
    assert len(profile.experience) == 1
    assert profile.experience[0]["company"] == "Example Corp"
    assert len(profile.education) == 1
    assert profile.education[0]["year"] == ""  # safely empty string, no crash
    assert profile.is_auth_walled is False


def test_parse_non_english_titles_and_suffixes(scraper: LinkedInPublicScraper) -> None:
    html = (FIXTURES_DIR / "public_profile_non_english.html").read_text(encoding="utf-8")
    profile = scraper.parse_person_html("https://www.linkedin.com/in/asha-example", html)

    # Name must not contain localized LinkedIn suffixes or dashes
    assert profile.name == "Asha Example"
    assert "Gründerin" in (profile.headline or "")
    assert profile.location == "München, Deutschland"
    assert len(profile.experience) == 1
    assert profile.experience[0]["company"] == "Example Corp"
    assert len(profile.education) == 1
    assert profile.education[0]["institution"] == "Technische Universität München"
    assert profile.education[0]["year"] == "2018"
    assert profile.is_auth_walled is False
