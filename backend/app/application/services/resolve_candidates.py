"""Use case: resolve search candidates for a company and its founders."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import cast

from app.application.ports.cache_port import CachePort
from app.application.ports.web_search_port import WebSearchPort
from app.domain.entities.discovery import SearchResult, SourceCandidate


@dataclass(frozen=True)
class ResolveInput:
    company_name: str
    founder_names: list[str]
    website_override: str | None = None
    company_linkedin_override: str | None = None
    founder_linkedin_overrides: dict[str, str] | None = None  # name -> url


@dataclass(frozen=True)
class ResolveOutput:
    candidates: dict[str, list[SourceCandidate]]  # category -> ranked candidates
    search_unavailable: bool  # True if search failed (user must paste URLs)
    error_message: str | None = None


class ResolveCandidatesService:
    """Search for candidate URLs for a company and its founders.
    
    Queries the web search port for:
    - Company LinkedIn page
    - Each founder's LinkedIn profile  
    - Official website (if not provided)
    - News/funding articles
    
    User-provided overrides skip the search for that category.
    """
    
    def __init__(self, web_search: WebSearchPort, cache: CachePort) -> None:
        self._web_search = web_search
        self._cache = cache
    
    async def execute(self, input_dto: ResolveInput) -> ResolveOutput:
        candidates: dict[str, list[SourceCandidate]] = {}
        search_failed = False
        error_msg: str | None = None
        
        # Company LinkedIn
        if input_dto.company_linkedin_override:
            candidates["company_linkedin"] = [
                SourceCandidate(
                    url=input_dto.company_linkedin_override,
                    title=f"{input_dto.company_name} (user-provided)",
                    snippet="",
                    domain=_extract_domain(input_dto.company_linkedin_override),
                    confidence=1.0,
                    category="company_linkedin",
                    search_query="",
                    entity_name=input_dto.company_name,
                )
            ]
        else:
            try:
                results = await self._cached_search(
                    f"{input_dto.company_name} LinkedIn company",
                    max_results=3,
                )
                candidates["company_linkedin"] = [
                    _score_candidate(r, input_dto.company_name, "company_linkedin",
                                     f"{input_dto.company_name} LinkedIn company")
                    for r in results
                    if "linkedin.com" in r.domain
                ]
            except Exception:
                search_failed = True
                candidates["company_linkedin"] = []
        
        # Founder LinkedIn profiles
        overrides = input_dto.founder_linkedin_overrides or {}
        for name in input_dto.founder_names:
            category = f"founder_linkedin_{_slugify(name)}"
            if name in overrides:
                candidates[category] = [
                    SourceCandidate(
                        url=overrides[name],
                        title=f"{name} (user-provided)",
                        snippet="",
                        domain=_extract_domain(overrides[name]),
                        confidence=1.0,
                        category=category,
                        search_query="",
                        entity_name=name,
                    )
                ]
            else:
                try:
                    query = f"{name} {input_dto.company_name} LinkedIn"
                    results = await self._cached_search(query, max_results=3)
                    candidates[category] = [
                        _score_candidate(r, name, category, query)
                        for r in results
                        if "linkedin.com" in r.domain
                    ]
                except Exception:
                    search_failed = True
                    candidates[category] = []
        
        # Official website
        if input_dto.website_override:
            candidates["website"] = [
                SourceCandidate(
                    url=input_dto.website_override,
                    title=f"{input_dto.company_name} (user-provided)",
                    snippet="",
                    domain=_extract_domain(input_dto.website_override),
                    confidence=1.0,
                    category="website",
                    search_query="",
                    entity_name=input_dto.company_name,
                )
            ]
        else:
            try:
                query = f"{input_dto.company_name} official website"
                results = await self._cached_search(query, max_results=5)
                candidates["website"] = [
                    _score_candidate(r, input_dto.company_name, "website", query)
                    for r in results
                    if "linkedin.com" not in r.domain
                ]
            except Exception:
                search_failed = True
                candidates["website"] = []
        
        # News articles
        try:
            query = f"{input_dto.company_name} startup funding news"
            results = await self._cached_search(query, max_results=5)
            candidates["news"] = [
                _score_candidate(r, input_dto.company_name, "news", query)
                for r in results
                if "linkedin.com" not in r.domain
            ]
        except Exception:
            search_failed = True
            candidates["news"] = []
        
        if search_failed and not any(candidates.values()):
            error_msg = "All search providers are unavailable. Please provide URLs manually."
        
        return ResolveOutput(
            candidates=candidates,
            search_unavailable=search_failed and not any(candidates.values()),
            error_message=error_msg,
        )
    
    async def _cached_search(self, query: str, max_results: int) -> list[SearchResult]:
        cache_key = f"search:{query}:{max_results}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cast(list[SearchResult], cached)
        results = await self._web_search.search(query, max_results=max_results)
        await self._cache.set(cache_key, results)
        return results


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    match = re.search(r"(?:https?://)?(?:www\.)?([^/]+)", url)
    return match.group(1) if match else url


def _slugify(name: str) -> str:
    """Simple slugify for use as dict keys."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _score_candidate(
    result: SearchResult,
    entity_name: str,
    category: str,
    query: str,
) -> SourceCandidate:
    """Score a search result by relevance to the entity."""
    name_lower = entity_name.lower()
    title_lower = result.title.lower()
    snippet_lower = result.snippet.lower()
    
    score = 0.3  # base
    
    # Name in title
    if name_lower in title_lower:
        score += 0.3
    
    # Name in snippet
    if name_lower in snippet_lower:
        score += 0.15
    
    # LinkedIn URL contains name parts
    name_parts = name_lower.split()
    url_lower = result.url.lower()
    matching_parts = sum(1 for part in name_parts if part in url_lower)
    if name_parts:
        score += 0.25 * (matching_parts / len(name_parts))
    
    return SourceCandidate(
        url=result.url,
        title=result.title,
        snippet=result.snippet,
        domain=result.domain,
        confidence=min(score, 1.0),
        category=category,
        search_query=query,
        entity_name=entity_name,
    )
