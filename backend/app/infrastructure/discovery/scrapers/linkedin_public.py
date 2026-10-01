"""Public LinkedIn scraper implementing ProfileScraperPort.

Performs polite, unauthenticated extraction of public OpenGraph metadata and
Schema.org JSON-LD from public LinkedIn company and personal profile pages.
Never attempts login, session replay, or authwall bypass.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any
import httpx
from bs4 import BeautifulSoup

from app.application.ports.profile_scraper_port import ProfileScraperPort
from app.domain.entities.discovery import CompanyProfile, PersonProfile
from app.infrastructure.discovery.http.rate_limiter import HostRateLimiter
from app.infrastructure.discovery.scrapers.normalizer import clean_text, extract_year

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)


class LinkedInPublicScraper(ProfileScraperPort):
    """Scrapes public LinkedIn company and person profile pages without authentication."""

    def __init__(
        self,
        rate_limiter: HostRateLimiter | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._rate_limiter = rate_limiter or HostRateLimiter(min_interval_seconds=3.0)
        self._timeout = timeout_seconds

    async def _fetch_html(self, url: str) -> tuple[int, str, str, bool]:
        """Fetch page HTML with rate limiting and authwall detection.

        Returns:
            Tuple of (status_code, final_url, html_text, is_auth_walled).
        """
        await self._rate_limiter.wait(url)
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                headers=headers,
            ) as client:
                resp = await client.get(url)
                final_url = str(resp.url)
                status = resp.status_code
                html = resp.text

                # Authwall / login redirect detection
                is_auth_walled = (
                    status in (429, 999)
                    or "authwall" in final_url.lower()
                    or "login" in final_url.lower()
                    or "checkpoint" in final_url.lower()
                    or "signup" in final_url.lower()
                    or "authwall" in html.lower()
                )
                return status, final_url, html, is_auth_walled
        except Exception as exc:
            logger.warning("Failed fetching LinkedIn URL '%s': %s", url, exc)
            return 0, url, "", True

    def _extract_json_ld(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "{}")
                if isinstance(data, dict):
                    if "@graph" in data and isinstance(data["@graph"], list):
                        results.extend([item for item in data["@graph"] if isinstance(item, dict)])
                    else:
                        results.append(data)
                elif isinstance(data, list):
                    results.extend([item for item in data if isinstance(item, dict)])
            except Exception:
                continue
        return results

    def _extract_og_meta(self, soup: BeautifulSoup) -> dict[str, str]:
        og: dict[str, str] = {}
        for tag in soup.find_all("meta"):
            prop = tag.get("property") or tag.get("name") or ""
            content = tag.get("content") or ""
            if prop and content:
                og[prop.lower()] = content.strip()
        return og

    async def fetch_company(self, url: str) -> CompanyProfile | None:
        """Fetch and parse public LinkedIn company profile."""
        now_iso = datetime.now(timezone.utc).isoformat()
        status, final_url, html, is_auth_walled = await self._fetch_html(url)

        if not html:
            return CompanyProfile(
                url=url,
                retrieved_at=now_iso,
                is_auth_walled=True,
            )

        soup = BeautifulSoup(html, "html.parser")
        og = self._extract_og_meta(soup)
        json_lds = self._extract_json_ld(soup)

        # Find Organization or Corporation in JSON-LD
        org_data: dict[str, Any] = {}
        for item in json_lds:
            t = item.get("@type", "")
            if t in ("Organization", "Corporation", "LocalBusiness"):
                org_data = item
                break

        name = org_data.get("name") or og.get("og:title")
        if name and " | LinkedIn" in name:
            name = name.split(" | LinkedIn")[0].strip()

        description = (
            org_data.get("description")
            or og.get("og:description")
            or og.get("description")
        )

        website = org_data.get("sameAs") or org_data.get("url")
        if isinstance(website, list):
            website = website[0] if website else None

        address = org_data.get("address", {})
        headquarters = None
        if isinstance(address, dict):
            parts = [address.get("addressLocality"), address.get("addressCountry")]
            headquarters = ", ".join([p for p in parts if p])
        elif isinstance(address, str):
            headquarters = address

        founded_year = extract_year(org_data.get("foundingDate"))
        company_size = str(org_data.get("numberOfEmployees", {}).get("name", "")) or None
        logo_url = og.get("og:image")

        return CompanyProfile(
            name=name,
            description=clean_text(description or ""),
            industry=org_data.get("knowsAbout") or og.get("al:ios:app_name"),
            company_size=company_size,
            headquarters=headquarters,
            website=website,
            founded_year=founded_year,
            specialties=[],
            followers=None,
            logo_url=logo_url,
            tagline=None,
            url=url,
            retrieved_at=now_iso,
            is_auth_walled=is_auth_walled,
            raw_json_ld=org_data,
        )

    async def fetch_person(self, url: str) -> PersonProfile | None:
        """Fetch and parse public LinkedIn person profile."""
        now_iso = datetime.now(timezone.utc).isoformat()
        status, final_url, html, is_auth_walled = await self._fetch_html(url)

        if not html:
            return PersonProfile(
                url=url,
                retrieved_at=now_iso,
                is_auth_walled=True,
            )

        soup = BeautifulSoup(html, "html.parser")
        og = self._extract_og_meta(soup)
        json_lds = self._extract_json_ld(soup)

        person_data: dict[str, Any] = {}
        for item in json_lds:
            if item.get("@type") == "Person":
                person_data = item
                break

        name = person_data.get("name") or og.get("og:title")
        if name and " | LinkedIn" in name:
            name = name.split(" | LinkedIn")[0].strip()

        headline = person_data.get("jobTitle") or og.get("og:description") or og.get("description")
        summary = person_data.get("description")

        avatar_url = person_data.get("image") or og.get("og:image")
        if isinstance(avatar_url, dict):
            avatar_url = avatar_url.get("contentUrl")

        # Extract address / location
        address = person_data.get("address", {})
        location = None
        if isinstance(address, dict):
            parts = [address.get("addressLocality"), address.get("addressCountry")]
            location = ", ".join([p for p in parts if p])
        elif isinstance(address, str):
            location = address

        # Extract worksFor and alumniOf from JSON-LD
        experience: list[dict[str, str]] = []
        works_for = person_data.get("worksFor", [])
        if isinstance(works_for, dict):
            works_for = [works_for]
        for w in works_for:
            if isinstance(w, dict):
                experience.append({
                    "title": w.get("jobTitle") or w.get("name", ""),
                    "company": w.get("name", ""),
                    "duration": "",
                })

        education: list[dict[str, str]] = []
        alumni_of = person_data.get("alumniOf", [])
        if isinstance(alumni_of, dict):
            alumni_of = [alumni_of]
        for a in alumni_of:
            if isinstance(a, dict):
                education.append({
                    "institution": a.get("name", ""),
                    "degree": a.get("description", ""),
                    "year": extract_year(str(a)) or "",
                })

        return PersonProfile(
            name=name,
            headline=clean_text(headline or ""),
            location=location,
            summary=clean_text(summary or ""),
            education=education,
            experience=experience,
            follower_count=None,
            connection_count=None,
            avatar_url=avatar_url,
            url=url,
            retrieved_at=now_iso,
            is_auth_walled=is_auth_walled,
            raw_json_ld=person_data,
        )
