"""Scraper infrastructure package."""
from app.infrastructure.discovery.scrapers.linkedin_public import LinkedInPublicScraper
from app.infrastructure.discovery.scrapers.normalizer import (
    clean_text,
    clean_url,
    deduplicate_list,
    extract_year,
)

__all__ = [
    "LinkedInPublicScraper",
    "clean_text",
    "clean_url",
    "deduplicate_list",
    "extract_year",
]
