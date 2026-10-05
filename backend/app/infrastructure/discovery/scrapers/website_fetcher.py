"""Website fetcher implementing PageFetcherPort with SSRF protection and robots.txt checking."""
from __future__ import annotations

import json
import logging
import re
from typing import Any
import urllib.parse
import urllib.robotparser
from datetime import datetime, timezone
import httpx
from bs4 import BeautifulSoup

from app.application.ports.page_fetcher_port import PageFetcherPort
from app.domain.entities.discovery import PageContent, SourceDiagnostic
from app.infrastructure.discovery.http.rate_limiter import HostRateLimiter
from app.infrastructure.discovery.http.ssrf_guard import validate_safe_url
from app.infrastructure.discovery.scrapers.normalizer import (
    clean_text,
    canonicalize_url,
    is_boilerplate_line,
)

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = "vSET-DiscoveryBot/1.0 (+https://github.com/vset/screening)"
MAX_CONTENT_BYTES = 2 * 1024 * 1024  # 2MB cap to protect memory


class WebsiteFetcherAdapter(PageFetcherPort):
    """Fetches public website content with SSRF filtering, polite rate limiting, and size boundaries."""

    def __init__(
        self,
        rate_limiter: HostRateLimiter | None = None,
        timeout_seconds: float = 10.0,
        check_robots: bool = True,
        validate_ssrf_dns: bool = True,
    ) -> None:
        self._rate_limiter = rate_limiter or HostRateLimiter(min_interval_seconds=2.0)
        self._timeout = timeout_seconds
        self._check_robots = check_robots
        self._validate_ssrf_dns = validate_ssrf_dns
        self._robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}

    async def _is_allowed_by_robots(self, url: str) -> bool:
        if not self._check_robots:
            return True

        parsed = urllib.parse.urlsplit(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"

        if origin in self._robots_cache:
            rp = self._robots_cache[origin]
            return rp.can_fetch(DEFAULT_USER_AGENT, url)

        robots_url = f"{origin}/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(robots_url)
                if resp.status_code == 200:
                    rp.parse(resp.text.splitlines())
                else:
                    setattr(rp, "allow_all", True)
        except Exception:
            setattr(rp, "allow_all", True)

        self._robots_cache[origin] = rp
        return rp.can_fetch(DEFAULT_USER_AGENT, url)

    async def is_allowed(self, url: str) -> bool:
        """Public check if URL is allowed by robots.txt."""
        return await self._is_allowed_by_robots(url)

    async def fetch(self, url: str) -> PageContent | None:
        """Fetch and extract text content from a web page."""
        content, _ = await self.fetch_with_diagnostic(url)
        return content

    async def fetch_with_diagnostic(self, url: str) -> tuple[PageContent | None, SourceDiagnostic]:
        """Fetch and extract text content from a web page with detailed diagnostics."""
        try:
            # 1. SSRF prevention
            validate_safe_url(url, resolve_dns=self._validate_ssrf_dns)
        except ValueError as exc:
            logger.warning("SSRF guard blocked URL '%s': %s", url, exc)
            return None, SourceDiagnostic(
                url=url,
                outcome="ssrf_blocked",
                bytes_fetched=0,
                error_details=str(exc),
            )

        # 2. Check robots.txt
        if not await self._is_allowed_by_robots(url):
            logger.info("URL '%s' disallowed by robots.txt", url)
            return None, SourceDiagnostic(
                url=url,
                outcome="robots_blocked",
                bytes_fetched=0,
                error_details="Blocked by robots.txt rules",
            )

        # 3. Rate limiting
        await self._rate_limiter.wait(url)

        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                headers=headers,
            ) as client:
                async with client.stream("GET", url) as resp:
                    if resp.status_code >= 400:
                        logger.warning("HTTP %d error fetching '%s'", resp.status_code, url)
                        return None, SourceDiagnostic(
                            url=url,
                            outcome=f"http_error:{resp.status_code}",
                            bytes_fetched=0,
                            error_details=f"HTTP status {resp.status_code}",
                        )

                    content_type = resp.headers.get("content-type", "").lower()
                    if "text" not in content_type and "html" not in content_type:
                        logger.info("Skipping non-text content-type '%s' for '%s'", content_type, url)
                        return None, SourceDiagnostic(
                            url=url,
                            outcome="parse_empty",
                            bytes_fetched=0,
                            error_details=f"Non-text content-type: {content_type}",
                        )

                    chunks: list[bytes] = []
                    total_bytes = 0
                    async for chunk in resp.aiter_bytes():
                        chunks.append(chunk)
                        total_bytes += len(chunk)
                        if total_bytes > MAX_CONTENT_BYTES:
                            logger.info("Response truncated at %d bytes for '%s'", MAX_CONTENT_BYTES, url)
                            break

                    raw_bytes = b"".join(chunks)
                    html_text = raw_bytes.decode(resp.encoding or "utf-8", errors="replace")
                    resp_url_val = getattr(resp, "url", None)
                    final_resp_url = str(resp_url_val) if resp_url_val else url
                    canonical_page_url = canonicalize_url(final_resp_url) or canonicalize_url(url)

            page_content = extract_page_content(
                url=canonical_page_url,
                html_text=html_text,
                status_code=resp.status_code,
                content_type=content_type,
            )

            fields: list[str] = []
            if page_content.title:
                fields.append("title")
            if page_content.description:
                fields.append("description")
            if page_content.text:
                fields.append("text")
            if page_content.og_tags:
                fields.append("og_tags")
            if page_content.json_ld:
                fields.append("json_ld")
            if page_content.social_links:
                fields.append("social_links")
            if page_content.links:
                fields.append("links")

            outcome = "ok" if (page_content.text or page_content.description or page_content.og_tags or page_content.json_ld) else "empty_text"

            return page_content, SourceDiagnostic(
                url=canonical_page_url,
                outcome=outcome,
                bytes_fetched=total_bytes,
                fields_extracted=fields,
            )

        except httpx.TimeoutException as exc:
            logger.warning("Timeout fetching website URL '%s': %s", url, exc)
            return None, SourceDiagnostic(
                url=url,
                outcome="timeout",
                bytes_fetched=0,
                error_details="Request timed out",
            )
        except Exception as exc:
            logger.warning("Error fetching website URL '%s': %s", url, exc)
            return None, SourceDiagnostic(
                url=url,
                outcome="empty_text",
                bytes_fetched=0,
                error_details=str(exc),
            )

    async def fetch_sitemap_urls(self, base_url: str) -> list[str]:
        """Fetch and extract high-value candidate URLs from sitemap.xml."""
        parsed = urllib.parse.urlsplit(base_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        sitemap_url = f"{origin}/sitemap.xml"

        try:
            validate_safe_url(sitemap_url, resolve_dns=self._validate_ssrf_dns)
            if not await self._is_allowed_by_robots(sitemap_url):
                return []
            await self._rate_limiter.wait(sitemap_url)
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                resp = await client.get(sitemap_url, headers={"User-Agent": DEFAULT_USER_AGENT})
                if resp.status_code != 200:
                    return []
                xml_text = resp.text
                locs = re.findall(r"<loc>(https?://[^<]+)</loc>", xml_text, re.IGNORECASE)
                priority_keywords = ["about", "team", "people", "leadership", "product", "services", "company", "career", "press"]
                matched: list[str] = []
                for loc in locs:
                    clean_loc = loc.strip().rstrip("/")
                    loc_lower = clean_loc.lower()
                    if any(kw in loc_lower for kw in priority_keywords):
                        if clean_loc not in matched:
                            matched.append(clean_loc)
                    if len(matched) >= 8:
                        break
                return matched
        except Exception:
            return []


def extract_page_content(
    url: str,
    html_text: str,
    status_code: int = 200,
    content_type: str = "text/html",
    retrieved_at: str | None = None,
) -> PageContent:
    """Extract structured data, JSON-LD, links, and readable text from raw HTML."""
    soup = BeautifulSoup(html_text, "html.parser")

    # Extract title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    # Extract description
    desc = ""
    meta_desc = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    if meta_desc:
        desc = str(meta_desc.get("content") or "").strip()

    # Extract OG tags
    og_tags: dict[str, str] = {}
    for tag in soup.find_all("meta"):
        p = str(tag.get("property") or tag.get("name") or "")
        c = str(tag.get("content") or "")
        if p and c and (p.startswith("og:") or p.startswith("twitter:")):
            og_tags[p.lower()] = c.strip()

    if not desc and "og:description" in og_tags:
        desc = og_tags["og:description"]

    # 1. Extract JSON-LD scripts BEFORE decomposing
    json_lds: list[dict[str, Any]] = []
    for s in soup.find_all("script", attrs={"type": re.compile(r"application/ld\+json", re.I)}):
        try:
            if s.string:
                data = json.loads(s.string.strip())
                if isinstance(data, list):
                    json_lds.extend([d for d in data if isinstance(d, dict)])
                elif isinstance(data, dict):
                    if "@graph" in data and isinstance(data["@graph"], list):
                        json_lds.extend([d for d in data["@graph"] if isinstance(d, dict)])
                    else:
                        json_lds.append(data)
        except Exception:
            pass

    # 2. Extract links and social links BEFORE decomposing nav/footer/header
    social_links: dict[str, str] = {}
    nav_links: list[str] = []
    parsed_origin = urllib.parse.urlsplit(url)
    origin = f"{parsed_origin.scheme}://{parsed_origin.netloc}"

    # Check JSON-LD sameAs first
    for item in json_lds:
        same_as = item.get("sameAs")
        if isinstance(same_as, str):
            same_as = [same_as]
        if isinstance(same_as, list):
            for sa in same_as:
                if isinstance(sa, str):
                    sa_str = sa.strip()
                    if "linkedin.com/company/" in sa_str:
                        social_links["linkedin"] = sa_str
                    elif "github.com/" in sa_str and not any(x in sa_str for x in ["/features", "/pricing"]):
                        social_links["github"] = sa_str
                    elif "twitter.com/" in sa_str or "x.com/" in sa_str:
                        social_links["twitter"] = sa_str

    for a in soup.find_all("a", href=True):
        raw_href = a.get("href")
        href = str(raw_href).strip() if raw_href is not None else ""
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        full_url = urllib.parse.urljoin(url, href)
        full_url = urllib.parse.urldefrag(full_url)[0].rstrip("/")

        if "linkedin.com/company/" in full_url and "linkedin" not in social_links:
            social_links["linkedin"] = full_url
        elif "linkedin.com/in/" in full_url:
            founder_key = f"linkedin_person_{full_url.split('/in/')[-1].split('/')[0]}"
            social_links[founder_key] = full_url
        elif "github.com/" in full_url and "github" not in social_links and not any(x in full_url for x in ["/features", "/pricing", "/about"]):
            social_links["github"] = full_url

        # Check if internal navigation candidate
        if full_url.startswith(origin) and full_url != origin and full_url != url.rstrip("/"):
            path = urllib.parse.urlsplit(full_url).path.lower()
            if any(kw in path for kw in [
                "about", "team", "people", "leadership", "founder",
                "product", "service", "feature", "platform", "solution",
                "career", "press", "company"
            ]):
                if full_url not in nav_links:
                    nav_links.append(full_url)

    # 3. Remove boilerplate and non-content elements
    for tag_name in [
        "script", "style", "nav", "footer", "header",
        "noscript", "svg", "form", "iframe", "button", "dialog",
    ]:
        for el in soup.find_all(tag_name):
            el.decompose()

    # Decompose chat widgets, cookie banners, modals, popups, and form error states
    widget_selector = re.compile(
        r"(?:^|[-_ ])(chat|intercom|drift|hubspot|crisp|tidio|zendesk|livechat|tawk|cookie|consent|gdpr|modal|popup|toast|w-form-fail|w-form-done)(?:[-_ ]|$)",
        re.I,
    )
    for el in soup.find_all(name=None, attrs={"class": widget_selector}):
        el.decompose()
    for el in soup.find_all(name=None, attrs={"id": widget_selector}):
        el.decompose()
    for el in soup.find_all(name=None, attrs={"role": re.compile(r"^(dialog|alertdialog)$", re.I)}):
        el.decompose()

    # Extract readable text and strip individual boilerplate lines
    body_text = soup.get_text(separator="\n")
    cleaned_body = clean_text(body_text)
    filtered_lines = [
        line for line in cleaned_body.splitlines()
        if not is_boilerplate_line(line)
    ]
    final_text = "\n".join(filtered_lines).strip()

    now_iso = retrieved_at or datetime.now(timezone.utc).isoformat()
    return PageContent(
        url=canonicalize_url(url) or url,
        title=title,
        description=desc,
        text=final_text,
        og_tags=og_tags,
        retrieved_at=now_iso,
        content_type=content_type,
        status_code=status_code,
        json_ld=json_lds,
        links=nav_links,
        social_links=social_links,
    )
