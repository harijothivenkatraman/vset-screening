"""Application service for discovering founder LinkedIn profile URLs across three priorities:
1. User-confirmed / provided URL
2. Company website team/about page link located adjacent to the founder's name
3. Public search candidate fallback
"""
from __future__ import annotations

from dataclasses import dataclass
import re
import urllib.parse
from typing import Any

from app.domain.entities.discovery import PageContent


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
    """Discovers founder LinkedIn URLs adhering to three strict priority tiers."""

    @classmethod
    def discover_url(
        cls,
        founder_name: str,
        company_name: str,
        confirmed_urls: dict[str, str],
        website_pages: list[PageContent],
        search_snippets: dict[str, str] | None = None,
    ) -> DiscoveredFounderUrl:
        name_clean = founder_name.strip()
        slug = _slugify(name_clean)
        slug_key = f"founder_linkedin_{slug}"

        # ── Priority 1: User-confirmed / provided URL ─────────────────────────
        if slug_key in confirmed_urls and confirmed_urls[slug_key]:
            return DiscoveredFounderUrl(
                founder_name=name_clean,
                url=confirmed_urls[slug_key],
                source_type="user_confirmed",
            )
        if name_clean in confirmed_urls and confirmed_urls[name_clean]:
            return DiscoveredFounderUrl(
                founder_name=name_clean,
                url=confirmed_urls[name_clean],
                source_type="user_confirmed",
            )

        # ── Priority 2: Team/About page links near the founder's name ────────
        website_url, source_page, quote = cls._find_url_on_website_pages(name_clean, website_pages)
        if website_url:
            return DiscoveredFounderUrl(
                founder_name=name_clean,
                url=website_url,
                source_type="website_near_name",
                source_page_url=source_page,
                supporting_quote=quote,
            )

        # ── Priority 3: Search discovery fallback ─────────────────────────────
        search_url, search_quote = cls._find_url_in_search(name_clean, search_snippets)
        if search_url:
            return DiscoveredFounderUrl(
                founder_name=name_clean,
                url=search_url,
                source_type="search_discovery",
                supporting_quote=search_quote,
            )

        return DiscoveredFounderUrl(
            founder_name=name_clean,
            url=None,
            source_type="none",
        )

    @classmethod
    def _find_url_on_website_pages(
        cls, founder_name: str, pages: list[PageContent]
    ) -> tuple[str | None, str | None, str | None]:
        """Find a LinkedIn profile link adjacent to founder name on crawled website pages."""
        if not pages or not founder_name:
            return None, None, None

        # Sort pages: team/about pages first
        def _page_prio(p: PageContent) -> int:
            u = p.url.lower()
            if any(k in u for k in ("team", "people", "leadership", "founder", "about")):
                return 0
            return 1

        sorted_pages = sorted(pages, key=_page_prio)
        name_parts = [p.lower() for p in founder_name.split() if len(p) > 2]
        first_name = name_parts[0] if name_parts else founder_name.lower()
        last_name = name_parts[-1] if len(name_parts) > 1 else first_name

        for page in sorted_pages:
            # 1. Check social_links mapped during page fetch
            for k, url in getattr(page, "social_links", {}).items():
                if k.startswith("linkedin_person_") and "linkedin.com/in/" in url:
                    u_lower = url.lower()
                    if (first_name in u_lower and last_name in u_lower) or last_name in u_lower:
                        quote = f"Found on {page.url} matching {founder_name}"
                        return url, page.url, quote

            # 2. Check in-page links matching linkedin.com/in/
            for link in getattr(page, "links", []):
                if "linkedin.com/in/" in link:
                    link_lower = link.lower()
                    if first_name in link_lower and last_name in link_lower:
                        return link, page.url, f"Link {link} discovered on {page.url}"

            # 3. Check proximity in page text if available
            text = getattr(page, "text", "") or ""
            if founder_name.lower() in text.lower():
                # Extract paragraph or segment near name
                idx = text.lower().find(founder_name.lower())
                snippet = text[max(0, idx - 100) : min(len(text), idx + 200)].strip()
                # Check if an in-page link appears in the same page
                for link in getattr(page, "links", []):
                    if "linkedin.com/in/" in link:
                        link_slug = link.split("/in/")[-1].split("/")[0].lower()
                        if any(part in link_slug for part in name_parts):
                            return link, page.url, snippet

        return None, None, None

    @classmethod
    def _find_url_in_search(
        cls, founder_name: str, search_snippets: dict[str, str] | None
    ) -> tuple[str | None, str | None]:
        """Extract a LinkedIn profile URL from public search snippets."""
        if not search_snippets:
            return None, None

        slug = _slugify(founder_name)
        candidate_snippets = [
            search_snippets.get(f"founder_{slug}"),
            search_snippets.get(f"founder_linkedin_{slug}"),
            search_snippets.get(slug),
        ]

        li_re = re.compile(r"https?://(?:www\.)?linkedin\.com/in/[\w-]+", re.I)

        for snip in candidate_snippets:
            if not snip:
                continue
            m = li_re.search(snip)
            if m:
                return m.group(0), snip[:200]

        return None, None
