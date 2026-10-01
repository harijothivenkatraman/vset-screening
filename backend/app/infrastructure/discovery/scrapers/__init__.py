"""Scraper infrastructure package."""
from app.infrastructure.discovery.scrapers.linkedin_public import LinkedInPublicScraper
from app.infrastructure.discovery.scrapers.news_fetcher import NewsFetcherAdapter
from app.infrastructure.discovery.scrapers.normalizer import (
    clean_text,
    clean_url,
    deduplicate_list,
    extract_year,
)
from app.infrastructure.discovery.scrapers.website_fetcher import WebsiteFetcherAdapter

__all__ = [
    "LinkedInPublicScraper",
    "NewsFetcherAdapter",
    "WebsiteFetcherAdapter",
    "clean_text",
    "clean_url",
    "deduplicate_list",
    "extract_year",
]
