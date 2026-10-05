"""Application service for discovering founder public profile URLs across three priorities:
1. User-confirmed / provided URL
2. Company website team/about page link located adjacent to the founder's name
3. Public search candidate fallback (SearXNG / DuckDuckGo)
"""
from __future__ import annotations

from dataclasses import dataclass
import logging
import re
import urllib.parse
from typing import Any

from app.application.ports.page_fetcher_port import PageFetcherPort
from app.application.ports.web_search_port import WebSearchPort
from app.domain.entities.discovery import PageContent

logger = logging.getLogger(__name__)


def _slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"[\s_-]+", "_", s).strip("_")


@dataclass(frozen=True)
class DiscoveredFounderUrl:
    """Result of founder LinkedIn URL discovery with explicit provenance."""
    founder_name: str
    url: str | None
    source_type: str  # "user_confirmed" | "website_near_name" | "search_discovery" | "none"
    source_page_url: str | None = None
    supporting_quote: str | None = None


class FounderUrlDiscoveryService:
    """Discovers founder LinkedIn URLs adhering to strict priority tiers."""

    @classmethod
    async def discover(
        cls,
        founder_name: str,
        company_name: str | None = None,
        profile_url: str | None = None,
        company_website: str | None = None,
        page_fetcher: PageFetcherPort | None = None,
        search_adapter: WebSearchPort | None = None,
    ) -> DiscoveredFounderUrl:
        name_clean = founder_name.strip()
        if not name_clean:
            return DiscoveredFounderUrl(founder_name="", url=None, source_type="none")

        # ── Priority 1: User-confirmed / provided URL ─────────────────────────
        if profile_url and profile_url.strip():
            return DiscoveredFounderUrl(
                founder_name=name_clean,
                url=profile_url.strip(),
                source_type="user_confirmed",
            )

        # ── Priority 2: Company website team/about page ───────────────────────
        if company_website and company_website.strip() and page_fetcher:
            discovered = await cls._discover_from_website(
                name_clean, company_website.strip(), page_fetcher
            )
            if discovered and discovered.url:
                return discovered

        # ── Priority 3: Search discovery fallback ─────────────────────────────
        if search_adapter:
            discovered = await cls._discover_from_search(
                name_clean, company_name.strip() if company_name else "", search_adapter
            )
            if discovered and discovered.url:
                return discovered

        return DiscoveredFounderUrl(
            founder_name=name_clean,
            url=None,
            source_type="none",
        )

    @classmethod
    async def _discover_from_website(
        cls,
        founder_name: str,
        company_website: str,
        fetcher: PageFetcherPort,
    ) -> DiscoveredFounderUrl | None:
        try:
            main_page = await fetcher.fetch(company_website)
            if not main_page:
                return None

            pages: list[PageContent] = [main_page]

            # Look for subpages with team/about/leadership
            team_keywords = ("team", "about", "people", "leadership", "founder")
            subpage_urls: list[str] = []
            for link in main_page.links:
                link_lower = link.lower()
                if any(kw in link_lower for kw in team_keywords):
                    if link not in subpage_urls and link != company_website:
                        subpage_urls.append(link)
                if len(subpage_urls) >= 3:
                    break

            for sub_url in subpage_urls:
                sub_page = await fetcher.fetch(sub_url)
                if sub_page:
                    pages.append(sub_page)

            found_url, source_page, quote = cls._find_url_on_pages(founder_name, pages)
            if found_url:
                return DiscoveredFounderUrl(
                    founder_name=founder_name,
                    url=found_url,
                    source_type="website_near_name",
                    source_page_url=source_page,
                    supporting_quote=quote,
                )
        except Exception as exc:
            logger.warning("Error discovering founder from website '%s': %s", company_website, exc)

        return None

    @classmethod
    def _find_url_on_pages(
        cls, founder_name: str, pages: list[PageContent]
    ) -> tuple[str | None, str | None, str | None]:
        name_parts = [p.lower() for p in founder_name.split() if len(p) > 2]
        first_name = name_parts[0] if name_parts else founder_name.lower()
        last_name = name_parts[-1] if len(name_parts) > 1 else first_name

        for page in pages:
            # 1. Check social_links mapped during page fetch
            for k, url in getattr(page, "social_links", {}).items():
                if k.startswith("linkedin_person_") and "linkedin.com/in/" in url:
                    u_lower = url.lower()
                    if (first_name in u_lower and last_name in u_lower) or last_name in u_lower:
                        return url, page.url, f"Found on {page.url} matching {founder_name}"

            # 2. Check in-page links matching linkedin.com/in/
            for link in getattr(page, "links", []):
                if "linkedin.com/in/" in link:
                    link_lower = link.lower()
                    if first_name in link_lower and last_name in link_lower:
                        return link, page.url, f"Link discovered on {page.url}"

            # 3. Check text proximity
            text = getattr(page, "text", "") or ""
            if founder_name.lower() in text.lower():
                for link in getattr(page, "links", []):
                    if "linkedin.com/in/" in link:
                        link_slug = link.split("/in/")[-1].split("/")[0].lower()
                        if any(part in link_slug for part in name_parts):
                            return link, page.url, f"Proximity link on {page.url}"

        return None, None, None

    @classmethod
    async def _discover_from_search(
        cls,
        founder_name: str,
        company_name: str,
        search_adapter: WebSearchPort,
    ) -> DiscoveredFounderUrl | None:
        try:
            if company_name:
                query = f'"{founder_name}" "{company_name}" linkedin'
            else:
                query = f'"{founder_name}" linkedin'

            results = await search_adapter.search(query, max_results=5)
            li_pattern = re.compile(r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/in/[\w-]+", re.I)

            for res in results:
                m = li_pattern.search(res.url)
                if m:
                    return DiscoveredFounderUrl(
                        founder_name=founder_name,
                        url=m.group(0),
                        source_type="search_discovery",
                        supporting_quote=res.snippet[:200] if res.snippet else None,
                    )
                if res.snippet:
                    m_snip = li_pattern.search(res.snippet)
                    if m_snip:
                        return DiscoveredFounderUrl(
                            founder_name=founder_name,
                            url=m_snip.group(0),
                            source_type="search_discovery",
                            supporting_quote=res.snippet[:200],
                        )
        except Exception as exc:
            logger.warning("Search discovery failed for founder '%s': %s", founder_name, exc)

        return None
