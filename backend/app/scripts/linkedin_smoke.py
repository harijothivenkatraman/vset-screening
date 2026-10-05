"""LinkedIn live smoke test script.

Usage:
    python -m app.scripts.linkedin_smoke <url>

Example:
    python -m app.scripts.linkedin_smoke https://www.linkedin.com/company/mysa-smart-thermostats
    python -m app.scripts.linkedin_smoke https://www.linkedin.com/in/satyanadella
"""
from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict

from app.domain.entities.discovery import CompanyProfile, PersonProfile
from app.infrastructure.discovery.scrapers.linkedin_public import LinkedInPublicScraper


async def run_smoke_test(url: str) -> None:
    print("=" * 60)
    print("LINKEDIN SMOKE TEST")
    print("=" * 60)
    print(f"Target URL: {url}")

    scraper = LinkedInPublicScraper(timeout_seconds=15.0)

    url_lower = url.lower()
    is_company = "/company/" in url_lower
    is_person = "/in/" in url_lower

    if not is_company and not is_person:
        print("Warning: URL does not clearly contain '/company/' or '/in/'. Attempting company scraper first.")
        is_company = True

    profile: CompanyProfile | PersonProfile | None = None
    if is_company:
        print("Scraper Mode: Company Profile")
        profile, diag = await scraper.fetch_company_with_diagnostic(url)
    else:
        print("Scraper Mode: Person Profile")
        profile, diag = await scraper.fetch_person_with_diagnostic(url)

    print("-" * 60)
    print("DIAGNOSTIC SUMMARY:")
    print(f"  Outcome:          {diag.outcome}")
    print(f"  Auth Wall:        {'YES (BLOCKED)' if profile and profile.is_auth_walled else 'NO (ACCESSIBLE)'}")
    print(f"  Bytes Fetched:    {diag.bytes_fetched:,} bytes")
    print(f"  Fields Extracted: {diag.fields_extracted}")
    if diag.error_details:
        print(f"  Error Details:    {diag.error_details}")
    print("-" * 60)

    if profile:
        print("EXTRACTED PROFILE DATA:")
        profile_dict = asdict(profile)
        # Suppress raw_json_ld for cleaner terminal readability
        raw_ld = profile_dict.pop("raw_json_ld", None)
        print(json.dumps(profile_dict, indent=2, default=str))
        if raw_ld:
            print(f"  (Raw JSON-LD captured: {len(raw_ld)} keys)")
    else:
        print("No profile data extracted.")

    print("=" * 60)


def main() -> None:
    if len(sys.argv) < 2:
        print("Error: URL argument required.")
        print("Usage: python -m app.scripts.linkedin_smoke <url>")
        sys.exit(1)

    target_url = sys.argv[1].strip()
    try:
        asyncio.run(run_smoke_test(target_url))
    except KeyboardInterrupt:
        print("\nAborted by user.")
    except Exception as exc:
        print(f"\nExecution failed with error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
