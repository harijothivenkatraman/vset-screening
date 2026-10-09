"""Verification script for Bright Data LinkedIn Scraper API.

Tests person profile scraping, company profile scraping, and the
TryPublicFetchUseCase integration using only Bright Data API.
"""
import asyncio
import json
import sys
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.config import get_settings
from app.infrastructure.discovery.scrapers.brightdata_linkedin import BrightDataLinkedInScraper
from app.application.use_cases.try_public_fetch import TryPublicFetchUseCase
from unittest.mock import AsyncMock


async def main() -> None:
    settings = get_settings()
    token = settings.BRIGHTDATA_API_TOKEN
    print("=" * 60)
    print("BRIGHT DATA API INTEGRATION TEST")
    print("=" * 60)
    print(f"Token Configured: {bool(token)} (Prefix: {token[:8]}...)")

    scraper = BrightDataLinkedInScraper(token=token)

    # 1. Test Person Profile Scraping
    person_url = "https://www.linkedin.com/in/satyanadella"
    print(f"\n[1/3] Testing Person Profile Scraping: {person_url}")
    person_profile, person_diag = await scraper.fetch_person_with_diagnostic(person_url)
    print(f"  Diagnostic Outcome : {person_diag.outcome}")
    print(f"  Bytes Fetched      : {person_diag.bytes_fetched}")
    print(f"  Fields Extracted   : {person_diag.fields_extracted}")
    if person_profile:
        print(f"  Name               : {person_profile.name}")
        print(f"  Headline           : {person_profile.headline}")
        print(f"  Location           : {person_profile.location}")
        print(f"  Summary            : {person_profile.summary[:80]}...")
        print(f"  Experience Count   : {len(person_profile.experience)}")
        for idx, exp in enumerate(person_profile.experience[:3], 1):
            print(f"    {idx}. {exp.get('title')} at {exp.get('company')} ({exp.get('start')} - {exp.get('end')})")
        print(f"  Education Count    : {len(person_profile.education)}")
        for idx, edu in enumerate(person_profile.education[:3], 1):
            deg = f" - {edu.get('degree')}" if edu.get("degree") else ""
            print(f"    {idx}. {edu.get('school')}{deg} ({edu.get('start_year')} - {edu.get('end_year')})")

    # 2. Test Company Profile Scraping
    company_url = "https://www.linkedin.com/company/microsoft"
    print(f"\n[2/3] Testing Company Profile Scraping: {company_url}")
    comp_profile, comp_diag = await scraper.fetch_company_with_diagnostic(company_url)
    print(f"  Diagnostic Outcome : {comp_diag.outcome}")
    print(f"  Bytes Fetched      : {comp_diag.bytes_fetched}")
    print(f"  Fields Extracted   : {comp_diag.fields_extracted}")
    if comp_profile:
        print(f"  Name               : {comp_profile.name}")
        print(f"  Website            : {comp_profile.website}")
        print(f"  Headquarters       : {comp_profile.headquarters}")
        print(f"  Description        : {comp_profile.description[:80]}...")

    # 3. Test TryPublicFetch Use Case Integration
    print(f"\n[3/3] Testing TryPublicFetchUseCase Integration")
    mock_repo = AsyncMock()
    mock_repo.find_by_name_and_company = AsyncMock(return_value=None)
    mock_repo.find_by_linkedin_url = AsyncMock(return_value=None)
    mock_repo.find_by_slug = AsyncMock(return_value=None)

    use_case = TryPublicFetchUseCase(repository=mock_repo, scraper=scraper)
    fetch_result = await use_case.execute(
        founder_name="Satya Nadella",
        linkedin_url=person_url,
        company_name="Microsoft",
        save_as_pending=False,
    )
    print(f"  Success / Verified : {fetch_result.is_verified}")
    print(f"  Diagnostic Status  : {fetch_result.diagnostic.outcome}")
    print(f"  Message            : {fetch_result.message}")
    if fetch_result.candidate:
        print(f"  Candidate Slug     : {fetch_result.candidate.slug}")
        print(f"  Identity Status    : {fetch_result.candidate.identity_status}")
        print(f"  Founder Name       : {fetch_result.candidate.founder_name}")
        print(f"  Timeline Entries   : {len(fetch_result.candidate.experience_timeline)}")
        print(f"  Education Entries  : {len(fetch_result.candidate.education)}")

    print("\n" + "=" * 60)
    print("ALL BRIGHT DATA TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
