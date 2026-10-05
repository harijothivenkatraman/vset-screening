"""Website fetcher implementing PageFetcherPort with SSRF protection and polite rate limiting."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
import re
from typing import Any
import urllib.parse
import httpx
from bs4 import BeautifulSoup

from app.application.ports.page_fetcher_port import PageFetcherPort
from app.domain.entities.discovery import PageContent, SourceDiagnostic
from app.infrastructure.discovery.http.rate_limiter import HostRateLimiter
from app.infrastructure.discovery.http.ssrf_guard import validate_safe_url
from app.infrastructure.discovery.scrapers.normalizer import clean_text

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)


class WebsiteFetcher(PageFetcherPort):
    """Fetches public company web pages to discover founder and leadership links."""

    def __init__(
        self,
        rate_limiter: HostRateLimiter | None = None,
        timeout_seconds: float = 8.0,
        validate_ssrf_dns: bool = True,
    ) -> None:
        self._rate_limiter = rate_limiter or HostRateLimiter(min_interval_seconds=1.0)
        self._timeout = timeout_seconds
        self._validate_ssrf_dns = validate_ssrf_dns

    async def fetch(self, url: str) -> PageContent | None:
        content, _ = await self.fetch_with_diagnostic(url)
        return content

    async def fetch_with_diagnostic(self, url: str) -> tuple[PageContent | None, SourceDiagnostic]:
        try:
            validate_safe_url(url, resolve_dns=self._validate_ssrf_dns)
        except Exception as exc:
            logger.warning("SSRF check blocked URL '%s': %s", url, exc)
            return None, SourceDiagnostic(
                url=url,
                outcome="blocked_ssrf",
                bytes_fetched=0,
                error_details=str(exc),
            )

        await self._rate_limiter.wait(url)
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                headers=headers,
            ) as client:
                resp = await client.get(url)
                if resp.status_code >= 400:
                    return None, SourceDiagnostic(
                        url=url,
                        outcome=f"http_error:{resp.status_code}",
                        bytes_fetched=len(resp.content),
                    )
                html_text = resp.text
                page = extract_page_content(str(resp.url), html_text, resp.status_code)
                return page, SourceDiagnostic(
                    url=str(resp.url),
                    outcome="ok",
                    bytes_fetched=len(resp.content),
                    fields_extracted=["text", "links", "title"],
                )
        except Exception as exc:
            logger.warning("Error fetching URL '%s': %s", url, exc)
            return None, SourceDiagnostic(
                url=url,
                outcome="empty_text",
                bytes_fetched=0,
                error_details=str(exc),
            )


def extract_page_content(
    url: str,
    html_text: str,
    status_code: int = 200,
    retrieved_at: str | None = None,
) -> PageContent:
    """Extract links, structured metadata, and readable text from raw HTML."""
    soup = BeautifulSoup(html_text, "html.parser")

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    desc = ""
    meta_desc = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    if meta_desc:
        desc = str(meta_desc.get("content") or "").strip()

    social_links: dict[str, str] = {}
    links: list[str] = []

    for a in soup.find_all("a", href=True):
        raw_href = str(a.get("href") or "").strip()
        if not raw_href or raw_href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        full_url = urllib.parse.urljoin(url, raw_href)
        clean_url = urllib.parse.urldefrag(full_url)[0].rstrip("/")

        if "linkedin.com/in/" in clean_url:
            slug = clean_url.split("/in/")[-1].split("/")[0]
            social_links[f"linkedin_person_{slug}"] = clean_url
        elif "linkedin.com/company/" in clean_url:
            social_links["linkedin_company"] = clean_url

        if clean_url not in links:
            links.append(clean_url)

    # Decompose script, style, nav, footer, etc.
    for tag in soup.find_all(["script", "style", "nav", "footer", "noscript", "svg", "iframe"]):
        tag.decompose()

    body_text = clean_text(soup.get_text(separator="\n"))
    now_iso = retrieved_at or datetime.now(timezone.utc).isoformat()

    return PageContent(
        url=url,
        title=title,
        description=desc,
        text=body_text,
        retrieved_at=now_iso,
        status_code=status_code,
        links=links,
        social_links=social_links,
    )
