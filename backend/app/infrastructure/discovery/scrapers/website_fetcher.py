"""Website fetcher implementing PageFetcherPort with SSRF protection and robots.txt checking."""
from __future__ import annotations

import logging
import re
import urllib.parse
import urllib.robotparser
from datetime import datetime, timezone
import httpx
from bs4 import BeautifulSoup

from app.application.ports.page_fetcher_port import PageFetcherPort
from app.domain.entities.discovery import PageContent
from app.infrastructure.discovery.http.rate_limiter import HostRateLimiter
from app.infrastructure.discovery.http.ssrf_guard import validate_safe_url
from app.infrastructure.discovery.scrapers.normalizer import clean_text

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
                    rp.allow_all = True
        except Exception:
            rp.allow_all = True

        self._robots_cache[origin] = rp
        return rp.can_fetch(DEFAULT_USER_AGENT, url)

    async def fetch(self, url: str) -> PageContent | None:
        """Fetch and extract text content from a web page."""
        try:
            # 1. SSRF prevention
            validate_safe_url(url, resolve_dns=self._validate_ssrf_dns)
        except ValueError as exc:
            logger.warning("SSRF guard blocked URL '%s': %s", url, exc)
            return None

        # 2. Check robots.txt
        if not await self._is_allowed_by_robots(url):
            logger.info("URL '%s' disallowed by robots.txt", url)
            return None

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
                        return None

                    content_type = resp.headers.get("content-type", "").lower()
                    if "text" not in content_type and "html" not in content_type:
                        logger.info("Skipping non-text content-type '%s' for '%s'", content_type, url)
                        return None

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
                p = tag.get("property") or tag.get("name") or ""
                c = tag.get("content") or ""
                if p and c and (p.startswith("og:") or p.startswith("twitter:")):
                    og_tags[p.lower()] = c.strip()

            if not desc and "og:description" in og_tags:
                desc = og_tags["og:description"]

            # Remove boilerplate and non-content elements
            for tag_name in [
                "script", "style", "nav", "footer", "header",
                "noscript", "svg", "form", "iframe", "button",
            ]:
                for el in soup.find_all(tag_name):
                    el.decompose()

            # Extract readable text
            body_text = soup.get_text(separator="\n")
            cleaned_body = clean_text(body_text)

            now_iso = datetime.now(timezone.utc).isoformat()
            return PageContent(
                url=url,
                title=title,
                description=desc,
                text=cleaned_body,
                og_tags=og_tags,
                retrieved_at=now_iso,
                content_type=content_type,
                status_code=resp.status_code,
            )

        except Exception as exc:
            logger.warning("Error fetching website URL '%s': %s", url, exc)
            return None
