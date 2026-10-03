"""Public LinkedIn scraper implementing ProfileScraperPort.

Performs polite, unauthenticated extraction of public OpenGraph metadata and
Schema.org JSON-LD from public LinkedIn company and personal profile pages.
Never attempts login, session replay, or authwall bypass.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any
import httpx
from bs4 import BeautifulSoup

from app.application.ports.profile_scraper_port import ProfileScraperPort
from app.domain.entities.discovery import CompanyProfile, PersonProfile, SourceDiagnostic
from app.infrastructure.discovery.http.rate_limiter import HostRateLimiter
from app.infrastructure.discovery.scrapers.normalizer import clean_text, extract_year

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)


class LinkedInCircuitBreaker:
    """Circuit breaker for public LinkedIn requests.

    After 3 consecutive bot protection blocks (Cloudflare challenge / HTTP 403),
    opens for 30 minutes (1800s) to avoid fruitless traffic and protect IP reputation.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: float = 1800.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.consecutive_blocks: int = 0
        self.last_block_time: float = 0.0
        self._lock = asyncio.Lock()

    async def is_open(self) -> bool:
        async with self._lock:
            if self.consecutive_blocks >= self.failure_threshold:
                if time.monotonic() - self.last_block_time < self.cooldown_seconds:
                    return True
                # Cooldown expired: trial retry allowed
                return False
            return False

    async def record_block(self) -> None:
        async with self._lock:
            self.consecutive_blocks += 1
            self.last_block_time = time.monotonic()
            if self.consecutive_blocks >= self.failure_threshold:
                logger.warning(
                    "LinkedIn circuit breaker opened after %d consecutive bot protection blocks. Skipping LinkedIn for %.0fs (30m).",
                    self.consecutive_blocks,
                    self.cooldown_seconds,
                )

    async def record_success(self) -> None:
        async with self._lock:
            self.consecutive_blocks = 0

    async def reset(self) -> None:
        async with self._lock:
            self.consecutive_blocks = 0
            self.last_block_time = 0.0


_SHARED_LINKEDIN_CIRCUIT_BREAKER = LinkedInCircuitBreaker()


def _parse_text_or_list(val: Any, delimiter: str = " | ") -> str | None:
    """Safely parse a field that can be either a string or a list of strings in schema.org JSON-LD."""
    if val is None:
        return None
    if isinstance(val, (list, tuple, set)):
        items = [str(x).strip() for x in val if x is not None and str(x).strip()]
        return delimiter.join(items) if items else None
    if isinstance(val, dict):
        name_val = val.get("name")
        return str(name_val).strip() if name_val else None
    s = str(val).strip()
    return s if s else None


def normalize_linkedin_url(url: str) -> str:
    """Normalize regional subdomains (in., uk., ca., etc.) to www.linkedin.com."""
    if not url:
        return url
    u = url.strip()
    if not u.startswith(("http://", "https://")):
        u = f"https://{u}"
    return re.sub(
        r"^(https?://)(?:[a-z]{2,3}\.)?linkedin\.com",
        r"\1www.linkedin.com",
        u,
        flags=re.IGNORECASE,
    )


class LinkedInPublicScraper(ProfileScraperPort):
    """Scrapes public LinkedIn company and person profile pages without authentication."""

    def __init__(
        self,
        rate_limiter: HostRateLimiter | None = None,
        timeout_seconds: float = 10.0,
        circuit_breaker: LinkedInCircuitBreaker | None = None,
    ) -> None:
        self._rate_limiter = rate_limiter or HostRateLimiter(min_interval_seconds=3.0)
        self._timeout = timeout_seconds
        self._circuit_breaker = circuit_breaker or _SHARED_LINKEDIN_CIRCUIT_BREAKER

    async def _fetch_html(self, url: str) -> tuple[int, str, str, bool, bool]:
        """Fetch page HTML with rate limiting, bot protection, and authwall detection.

        Returns:
            Tuple of (status_code, final_url, html_text, is_auth_walled, is_bot_blocked).
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

                # Authwall / login redirect / Cloudflare challenge detection
                final_url_lower = final_url.lower()
                is_bot_blocked = (
                    status in (403, 429)
                    or "challenges.cloudflare.com" in html
                    or "just a moment..." in html[:1000].lower()
                    or "<title>just a moment...</title>" in html[:2000].lower()
                    or "turnstile" in html.lower()
                )
                is_auth_walled = (
                    is_bot_blocked
                    or status == 999
                    or "/authwall" in final_url_lower
                    or "/checkpoint" in final_url_lower
                    or "/login" in final_url_lower
                    or "uas/login" in final_url_lower
                )
                return status, final_url, html, is_auth_walled, is_bot_blocked
        except Exception as exc:
            logger.warning("Failed fetching LinkedIn URL '%s': %s", url, exc)
            return 0, url, "", True, False

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

    def parse_company_html(
        self,
        url: str,
        html: str,
        is_auth_walled: bool = False,
        status: int = 200,
        retrieved_at: str | None = None,
    ) -> CompanyProfile:
        """Parse raw HTML for a LinkedIn company profile."""
        now_iso = retrieved_at or datetime.now(timezone.utc).isoformat()
        if not html:
            return CompanyProfile(url=url, retrieved_at=now_iso, is_auth_walled=is_auth_walled)

        # Real signal: status 403/429/999 is always auth-walled / rate-limited
        if status in (403, 429, 999) and "challenges.cloudflare.com" in html:
            return CompanyProfile(url=url, retrieved_at=now_iso, is_auth_walled=True)

        soup = BeautifulSoup(html, "html.parser")
        og = self._extract_og_meta(soup)
        json_lds = self._extract_json_ld(soup)

        # Find Organization or Corporation in JSON-LD
        org_data: dict[str, Any] = {}
        has_org_json_ld = False
        for item in json_lds:
            t = item.get("@type", "")
            if t in ("Organization", "Corporation", "LocalBusiness"):
                org_data = item
                has_org_json_ld = True
                break

        og_title = (og.get("og:title") or "").strip()
        is_generic_login_title = (
            not og_title
            or "log in" in og_title.lower()
            or "sign up" in og_title.lower()
            or og_title.lower() == "linkedin"
            or "just a moment" in og_title.lower()
        )
        has_entity_og = bool(og_title and not is_generic_login_title)

        # Declare auth_wall ONLY if neither JSON-LD nor entity og:title is present AND real authwall signals exist
        if not has_org_json_ld and not has_entity_og:
            title_text = (soup.title.string or "").lower() if soup.title else ""
            if (
                is_auth_walled
                or status in (403, 429, 999)
                or "authwall" in html.lower()
                or "challenges.cloudflare.com" in html
                or "sign in" in title_text
                or "log in" in title_text
                or "join linkedin" in title_text
                or "just a moment" in title_text
            ):
                return CompanyProfile(url=url, retrieved_at=now_iso, is_auth_walled=True)

        name = _parse_text_or_list(org_data.get("name")) or og.get("og:title")
        if name and " | LinkedIn" in name:
            name = name.split(" | LinkedIn")[0].strip()

        description = (
            _parse_text_or_list(org_data.get("description"))
            or og.get("og:description")
            or og.get("description")
        )

        same_as = org_data.get("sameAs")
        website = None
        if isinstance(same_as, list):
            website = str(same_as[0]).strip() if same_as else None
        elif isinstance(same_as, str):
            website = same_as.strip()
        else:
            url_val = org_data.get("url")
            website = str(url_val).strip() if url_val else None

        address = org_data.get("address", {})
        headquarters = None
        if isinstance(address, dict):
            parts = [address.get("addressLocality"), address.get("addressCountry")]
            headquarters = ", ".join([str(p).strip() for p in parts if p and str(p).strip()])
        elif isinstance(address, list):
            for a in address:
                if isinstance(a, dict):
                    parts = [a.get("addressLocality"), a.get("addressCountry")]
                    hq_cand = ", ".join([str(p).strip() for p in parts if p and str(p).strip()])
                    if hq_cand:
                        headquarters = hq_cand
                        break
        elif isinstance(address, str):
            headquarters = address.strip()

        founded_year = extract_year(str(org_data.get("foundingDate") or ""))
        company_size = None
        num_emp = org_data.get("numberOfEmployees")
        if isinstance(num_emp, dict):
            company_size = _parse_text_or_list(num_emp.get("name"))
        elif num_emp:
            company_size = str(num_emp).strip()

        logo_url = og.get("og:image")

        industry_val = org_data.get("knowsAbout")
        industry = _parse_text_or_list(industry_val, delimiter=", ")
        # NOTE: Never use og.get("al:ios:app_name") as industry fallback (it is literally "LinkedIn")

        return CompanyProfile(
            name=name,
            description=clean_text(description or ""),
            industry=clean_text(industry or "") if industry else None,
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
            is_auth_walled=False,
            raw_json_ld=org_data,
        )

    def parse_person_html(
        self,
        url: str,
        html: str,
        is_auth_walled: bool = False,
        status: int = 200,
        retrieved_at: str | None = None,
    ) -> PersonProfile:
        """Parse raw HTML for a LinkedIn personal profile."""
        now_iso = retrieved_at or datetime.now(timezone.utc).isoformat()
        if not html:
            return PersonProfile(url=url, retrieved_at=now_iso, is_auth_walled=is_auth_walled)

        # Real signal: status 429/999 is always auth-walled / rate-limited
        if status in (429, 999):
            return PersonProfile(url=url, retrieved_at=now_iso, is_auth_walled=True)

        soup = BeautifulSoup(html, "html.parser")
        og = self._extract_og_meta(soup)
        json_lds = self._extract_json_ld(soup)

        person_data: dict[str, Any] = {}
        has_person_json_ld = False
        for item in json_lds:
            if item.get("@type") == "Person":
                person_data = item
                has_person_json_ld = True
                break

        og_title = (og.get("og:title") or "").strip()
        is_generic_login_title = (
            not og_title
            or "log in" in og_title.lower()
            or "sign up" in og_title.lower()
            or og_title.lower() == "linkedin"
            or "just a moment" in og_title.lower()
        )
        has_entity_og = bool(og_title and not is_generic_login_title)

        # Declare auth_wall ONLY if neither JSON-LD nor entity og:title is present AND real authwall signals exist
        if not has_person_json_ld and not has_entity_og:
            title_text = (soup.title.string or "").lower() if soup.title else ""
            if (
                is_auth_walled
                or status in (403, 429, 999)
                or "authwall" in html.lower()
                or "challenges.cloudflare.com" in html
                or "sign in" in title_text
                or "log in" in title_text
                or "join linkedin" in title_text
                or "just a moment" in title_text
            ):
                return PersonProfile(url=url, retrieved_at=now_iso, is_auth_walled=True)

        name = _parse_text_or_list(person_data.get("name")) or og.get("og:title")
        if name and " | LinkedIn" in name:
            name = name.split(" | LinkedIn")[0].strip()

        job_title_parsed = _parse_text_or_list(person_data.get("jobTitle"), delimiter=" - ")
        headline = job_title_parsed or og.get("og:description") or og.get("description")
        summary = _parse_text_or_list(person_data.get("description"))

        avatar_url = person_data.get("image") or og.get("og:image")
        if isinstance(avatar_url, dict):
            avatar_url = avatar_url.get("contentUrl")

        # Extract address / location
        address = person_data.get("address", {})
        location = None
        if isinstance(address, dict):
            parts = [address.get("addressLocality"), address.get("addressCountry")]
            location = ", ".join([str(p).strip() for p in parts if p and str(p).strip()])
        elif isinstance(address, list):
            for a in address:
                if isinstance(a, dict):
                    parts = [a.get("addressLocality"), a.get("addressCountry")]
                    loc_cand = ", ".join([str(p).strip() for p in parts if p and str(p).strip()])
                    if loc_cand:
                        location = loc_cand
                        break
        elif isinstance(address, str):
            location = address.strip()

        # Extract worksFor and alumniOf from JSON-LD
        experience: list[dict[str, str]] = []
        works_for = person_data.get("worksFor", [])
        if isinstance(works_for, dict):
            works_for = [works_for]
        for w in works_for:
            if isinstance(w, dict):
                job_title = _parse_text_or_list(w.get("jobTitle"), delimiter=" - ")
                comp_name = _parse_text_or_list(w.get("name"), delimiter=" ")
                experience.append({
                    "title": job_title or comp_name or "",
                    "company": comp_name or "",
                    "duration": "",
                })

        education: list[dict[str, str]] = []
        alumni_of = person_data.get("alumniOf", [])
        if isinstance(alumni_of, dict):
            alumni_of = [alumni_of]
        for a in alumni_of:
            if isinstance(a, dict):
                inst_name = _parse_text_or_list(a.get("name")) or ""
                deg_name = _parse_text_or_list(a.get("description")) or ""
                education.append({
                    "institution": inst_name,
                    "degree": deg_name,
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
            is_auth_walled=False,
            raw_json_ld=person_data,
        )

    async def fetch_company(self, url: str) -> CompanyProfile | None:
        """Fetch and parse public LinkedIn company profile."""
        profile, _ = await self.fetch_company_with_diagnostic(url)
        return profile

    async def fetch_company_with_diagnostic(self, url: str) -> tuple[CompanyProfile | None, SourceDiagnostic]:
        """Fetch and parse public LinkedIn company profile with diagnostics."""
        now_iso = datetime.now(timezone.utc).isoformat()
        normalized_url = normalize_linkedin_url(url)

        if await self._circuit_breaker.is_open():
            return CompanyProfile(
                url=normalized_url,
                retrieved_at=now_iso,
                is_auth_walled=True,
            ), SourceDiagnostic(
                url=normalized_url,
                outcome="circuit_breaker_open",
                bytes_fetched=0,
                fields_extracted=[],
                error_details="LinkedIn skipped: circuit breaker open after 3 consecutive bot protection blocks (30-minute cooldown)",
            )

        res = await self._fetch_html(normalized_url)
        if len(res) == 5:
            status, final_url, html, is_auth_walled, is_bot_blocked = res
        else:
            status, final_url, html, is_auth_walled = res  # type: ignore[misc]
            is_bot_blocked = status in (403, 429) or ("challenges.cloudflare.com" in html) or ("just a moment..." in html[:1000].lower())

        bytes_count = len(html.encode("utf-8")) if html else 0

        if is_bot_blocked:
            await self._circuit_breaker.record_block()
            return CompanyProfile(
                url=normalized_url,
                retrieved_at=now_iso,
                is_auth_walled=True,
            ), SourceDiagnostic(
                url=normalized_url,
                outcome="blocked_by_bot_protection",
                bytes_fetched=bytes_count,
                fields_extracted=[],
                error_details="Blocked by Cloudflare bot protection (HTTP 403 / challenge)",
            )

        if not html:
            outcome = "auth_wall" if is_auth_walled else ("http_error:0" if status == 0 else f"http_error:{status}")
            return CompanyProfile(
                url=normalized_url,
                retrieved_at=now_iso,
                is_auth_walled=is_auth_walled,
            ), SourceDiagnostic(
                url=normalized_url,
                outcome=outcome,
                bytes_fetched=0,
                error_details="No HTML returned",
            )

        profile = self.parse_company_html(
            url=normalized_url,
            html=html,
            is_auth_walled=is_auth_walled,
            status=status,
            retrieved_at=now_iso,
        )

        fields: list[str] = []
        if profile.name:
            fields.append("name")
        if profile.description:
            fields.append("description")
        if profile.industry:
            fields.append("industry")
        if profile.headquarters:
            fields.append("headquarters")
        if profile.website:
            fields.append("website")
        if profile.founded_year:
            fields.append("founded_year")
        if profile.company_size:
            fields.append("company_size")

        outcome = "auth_wall" if profile.is_auth_walled else ("ok" if fields else "empty_text")
        if outcome == "ok":
            await self._circuit_breaker.record_success()

        return profile, SourceDiagnostic(
            url=normalized_url,
            outcome=outcome,
            bytes_fetched=bytes_count,
            fields_extracted=fields,
            error_details="Auth wall / login redirect encountered" if profile.is_auth_walled else None,
        )

    async def fetch_person(self, url: str) -> PersonProfile | None:
        """Fetch and parse public LinkedIn person profile."""
        profile, _ = await self.fetch_person_with_diagnostic(url)
        return profile

    async def fetch_person_with_diagnostic(self, url: str) -> tuple[PersonProfile | None, SourceDiagnostic]:
        """Fetch and parse public LinkedIn person profile with diagnostics."""
        now_iso = datetime.now(timezone.utc).isoformat()
        normalized_url = normalize_linkedin_url(url)

        if await self._circuit_breaker.is_open():
            return PersonProfile(
                url=normalized_url,
                retrieved_at=now_iso,
                is_auth_walled=True,
            ), SourceDiagnostic(
                url=normalized_url,
                outcome="circuit_breaker_open",
                bytes_fetched=0,
                fields_extracted=[],
                error_details="LinkedIn skipped: circuit breaker open after 3 consecutive bot protection blocks (30-minute cooldown)",
            )

        res = await self._fetch_html(normalized_url)
        if len(res) == 5:
            status, final_url, html, is_auth_walled, is_bot_blocked = res
        else:
            status, final_url, html, is_auth_walled = res  # type: ignore[misc]
            is_bot_blocked = status in (403, 429) or ("challenges.cloudflare.com" in html) or ("just a moment..." in html[:1000].lower())

        bytes_count = len(html.encode("utf-8")) if html else 0

        if is_bot_blocked:
            await self._circuit_breaker.record_block()
            return PersonProfile(
                url=normalized_url,
                retrieved_at=now_iso,
                is_auth_walled=True,
            ), SourceDiagnostic(
                url=normalized_url,
                outcome="blocked_by_bot_protection",
                bytes_fetched=bytes_count,
                fields_extracted=[],
                error_details="Blocked by Cloudflare bot protection (HTTP 403 / challenge)",
            )

        if not html:
            outcome = "auth_wall" if is_auth_walled else ("http_error:0" if status == 0 else f"http_error:{status}")
            return PersonProfile(
                url=normalized_url,
                retrieved_at=now_iso,
                is_auth_walled=is_auth_walled,
            ), SourceDiagnostic(
                url=normalized_url,
                outcome=outcome,
                bytes_fetched=0,
                error_details="No HTML returned",
            )

        profile = self.parse_person_html(
            url=normalized_url,
            html=html,
            is_auth_walled=is_auth_walled,
            status=status,
            retrieved_at=now_iso,
        )

        fields: list[str] = []
        if profile.name:
            fields.append("name")
        if profile.headline:
            fields.append("headline")
        if profile.summary:
            fields.append("summary")
        if profile.location:
            fields.append("location")
        if profile.experience:
            fields.append("experience")
        if profile.education:
            fields.append("education")

        outcome = "auth_wall" if profile.is_auth_walled else ("ok" if fields else "empty_text")
        if outcome == "ok":
            await self._circuit_breaker.record_success()

        return profile, SourceDiagnostic(
            url=url,
            outcome=outcome,
            bytes_fetched=bytes_count,
            fields_extracted=fields,
            error_details="Auth wall / login redirect encountered" if profile.is_auth_walled else None,
        )
