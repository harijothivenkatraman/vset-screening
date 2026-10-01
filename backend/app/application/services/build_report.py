"""Use case: build a screening report from collected evidence.

Orchestrates: scraping → extraction → canonical JSON assembly → import.
This is the background work that runs after a job is started.
"""
from __future__ import annotations

import logging
from typing import Any

from app.application.ports.job_store_port import JobStorePort
from app.application.ports.page_fetcher_port import PageFetcherPort
from app.application.ports.profile_scraper_port import ProfileScraperPort
from app.application.ports.report_extractor_port import ReportExtractorPort
from app.application.ports.report_import_port import ReportImportPort
from app.domain.entities.discovery import (
    DiscoveryJob,
    Evidence,
    EvidenceSource,
    JobState,
    generate_source_id,
)
from app.domain.exceptions import SourceUnavailableError

logger = logging.getLogger(__name__)


class BuildReportService:
    """Orchestrate the full discovery pipeline as a background task.
    
    Steps:
    1. Scrape LinkedIn company profile
    2. Scrape LinkedIn founder profiles
    3. Fetch website pages
    4. Fetch news articles
    5. Extract structured report data
    6. Import report via ReportImportPort
    
    Each source failure is isolated (adds a warning, continues).
    """
    
    def __init__(
        self,
        job_store: JobStorePort,
        profile_scraper: ProfileScraperPort,
        page_fetcher: PageFetcherPort,
        report_extractor: ReportExtractorPort,
        report_import: ReportImportPort,
    ) -> None:
        self._job_store = job_store
        self._profile_scraper = profile_scraper
        self._page_fetcher = page_fetcher
        self._report_extractor = report_extractor
        self._report_import = report_import
    
    async def execute(self, job: DiscoveryJob) -> None:
        """Run the full discovery pipeline. Updates job state as it progresses."""
        try:
            job.transition_to(JobState.RUNNING)
            await self._job_store.update(job)
            
            evidence = Evidence()
            
            # Step 1: Scrape LinkedIn company
            await self._scrape_company(job, evidence)
            
            # Step 2: Scrape LinkedIn founders
            await self._scrape_founders(job, evidence)
            
            # Step 3: Fetch website pages
            await self._fetch_website(job, evidence)
            
            # Step 4: Fetch news articles
            await self._fetch_news(job, evidence)
            
            # Step 5: Extract report
            job.update_progress("Extracting report data", 0.7)
            await self._job_store.update(job)
            
            report_json = await self._report_extractor.extract(
                evidence=evidence,
                company_name=job.company_name,
                founder_names=job.founder_names,
            )
            
            # Step 6: Import report
            job.update_progress("Saving report", 0.9)
            await self._job_store.update(job)
            
            result = await self._report_import.import_report(report_json)
            job.result_slug = result.company_slug
            
            # Determine final state
            if job.warnings:
                job.transition_to(JobState.PARTIAL)
            else:
                job.transition_to(JobState.SUCCEEDED)
            
            job.update_progress("Complete", 1.0)
            await self._job_store.update(job)
            
            logger.info(
                "Discovery job %s completed: status=%s slug=%s warnings=%d",
                job.id, job.state.value, result.company_slug, len(job.warnings),
            )
        
        except Exception as exc:
            logger.error("Discovery job %s failed: %s", job.id, exc, exc_info=True)
            job.error_message = str(exc)
            try:
                job.transition_to(JobState.FAILED)
            except ValueError:
                job.state = JobState.FAILED  # Force if transition invalid
            job.update_progress("Failed", job.progress)
            await self._job_store.update(job)
    
    async def _scrape_company(self, job: DiscoveryJob, evidence: Evidence) -> None:
        url = job.confirmed_urls.get("company_linkedin")
        if not url:
            job.add_warning("No company LinkedIn URL provided")
            return
        
        job.update_progress("Scraping company LinkedIn", 0.1)
        await self._job_store.update(job)
        
        try:
            profile = await self._profile_scraper.fetch_company(url)
            if profile:
                evidence.company_profile = profile
                evidence.sources.append(EvidenceSource(
                    source_id=generate_source_id(url),
                    url=url,
                    publisher="linkedin.com",
                    source_type="SOCIAL_MEDIA",
                    retrieved_at=profile.retrieved_at,
                ))
                if profile.is_auth_walled:
                    job.add_warning(f"Company LinkedIn page is auth-walled: {url}")
            else:
                job.add_warning(f"Could not fetch company LinkedIn: {url}")
        except Exception as exc:
            job.add_warning(f"Error scraping company LinkedIn: {exc}")
    
    async def _scrape_founders(self, job: DiscoveryJob, evidence: Evidence) -> None:
        job.update_progress("Scraping founder profiles", 0.2)
        await self._job_store.update(job)
        
        for name in job.founder_names:
            slug_key = f"founder_linkedin_{_slugify(name)}"
            url = job.confirmed_urls.get(slug_key)
            if not url:
                job.add_warning(f"No LinkedIn URL for founder: {name}")
                continue
            
            try:
                profile = await self._profile_scraper.fetch_person(url)
                if profile:
                    evidence.founder_profiles.append(profile)
                    evidence.sources.append(EvidenceSource(
                        source_id=generate_source_id(url),
                        url=url,
                        publisher="linkedin.com",
                        source_type="SOCIAL_MEDIA",
                        retrieved_at=profile.retrieved_at,
                    ))
                    if profile.is_auth_walled:
                        job.add_warning(f"Founder LinkedIn auth-walled: {name} ({url})")
                else:
                    job.add_warning(f"Could not fetch LinkedIn for {name}: {url}")
            except Exception as exc:
                job.add_warning(f"Error scraping LinkedIn for {name}: {exc}")
    
    async def _fetch_website(self, job: DiscoveryJob, evidence: Evidence) -> None:
        url = job.confirmed_urls.get("website")
        if not url:
            job.add_warning("No website URL provided")
            return
        
        job.update_progress("Fetching website", 0.4)
        await self._job_store.update(job)
        
        # Fetch multiple pages: home, about, product/services
        paths = ["", "/about", "/about-us", "/product", "/products", "/services"]
        base = url.rstrip("/")
        if not base.startswith("http"):
            base = f"https://{base}"
        
        fetched_any = False
        for path in paths:
            page_url = f"{base}{path}"
            try:
                page = await self._page_fetcher.fetch(page_url)
                if page and page.text.strip():
                    evidence.website_pages.append(page)
                    if not fetched_any:
                        evidence.sources.append(EvidenceSource(
                            source_id=generate_source_id(base),
                            url=base,
                            publisher=_extract_domain(base),
                            source_type="COMPANY_WEBSITE",
                            retrieved_at=page.retrieved_at,
                        ))
                        fetched_any = True
            except Exception:
                pass  # Non-home pages failing is expected
        
        if not fetched_any:
            job.add_warning(f"Could not fetch any website pages from: {url}")
    
    async def _fetch_news(self, job: DiscoveryJob, evidence: Evidence) -> None:
        job.update_progress("Fetching news articles", 0.5)
        await self._job_store.update(job)
        
        news_urls = [
            v for k, v in job.confirmed_urls.items()
            if k.startswith("news_")
        ]
        
        for url in news_urls:
            try:
                page = await self._page_fetcher.fetch(url)
                if page and page.text.strip():
                    evidence.news_articles.append(page)
                    evidence.sources.append(EvidenceSource(
                        source_id=generate_source_id(url),
                        url=url,
                        publisher=_extract_domain(url),
                        title=page.title,
                        source_type="NEWS",
                        retrieved_at=page.retrieved_at,
                    ))
            except Exception as exc:
                job.add_warning(f"Could not fetch news article: {url} — {exc}")


import re

def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")

def _extract_domain(url: str) -> str:
    match = re.search(r"(?:https?://)?(?:www\.)?([^/]+)", url)
    return match.group(1) if match else url
