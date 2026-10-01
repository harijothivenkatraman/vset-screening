"""Discovery infrastructure package."""
from app.infrastructure.discovery.cache.ttl_cache import InMemoryTtlCache
from app.infrastructure.discovery.http.rate_limiter import HostRateLimiter
from app.infrastructure.discovery.http.ssrf_guard import is_safe_url, validate_safe_url
from app.infrastructure.discovery.jobs.in_memory_job_store import InMemoryJobStore
from app.infrastructure.discovery.llm.openai_compatible import OpenAICompatibleLlmAdapter
from app.infrastructure.discovery.llm.report_extractor import SectionBySectionExtractor
from app.infrastructure.discovery.report_import_adapter import ReportImportAdapter
from app.infrastructure.discovery.scrapers.linkedin_public import LinkedInPublicScraper
from app.infrastructure.discovery.scrapers.news_fetcher import NewsFetcherAdapter
from app.infrastructure.discovery.scrapers.normalizer import clean_text, clean_url
from app.infrastructure.discovery.scrapers.website_fetcher import WebsiteFetcherAdapter
from app.infrastructure.discovery.search.circuit_breaker import CircuitBreaker
from app.infrastructure.discovery.search.duckduckgo_search import DuckDuckGoSearchAdapter
from app.infrastructure.discovery.search.fallback_search import FallbackSearchAdapter
from app.infrastructure.discovery.search.searxng_search import SearXNGSearchAdapter

__all__ = [
    "CircuitBreaker",
    "DuckDuckGoSearchAdapter",
    "FallbackSearchAdapter",
    "HostRateLimiter",
    "InMemoryJobStore",
    "InMemoryTtlCache",
    "LinkedInPublicScraper",
    "NewsFetcherAdapter",
    "OpenAICompatibleLlmAdapter",
    "ReportImportAdapter",
    "SearXNGSearchAdapter",
    "SectionBySectionExtractor",
    "WebsiteFetcherAdapter",
    "clean_text",
    "clean_url",
    "is_safe_url",
    "validate_safe_url",
]
