"""Use case: build a screening report from collected evidence.

Orchestrates: scraping → extraction → canonical JSON assembly → import.
This is the background work that runs after a job is started.
"""
from __future__ import annotations

import hashlib
import logging
import re
import urllib.parse
from typing import Any

import base64
from datetime import datetime, timezone

from app.application.ports.evidence_source_port import (
    DiscoveryContext,
    EvidenceRegistryPort,
)
from app.application.ports.job_store_port import JobStorePort
from app.application.ports.page_fetcher_port import PageFetcherPort
from app.application.ports.profile_scraper_port import ProfileScraperPort
from app.application.ports.report_extractor_port import ReportExtractorPort
from app.application.ports.report_import_port import ReportImportPort
from app.application.services.pdf_extractor import (
    extract_pdf_text,
    parse_manual_profile_text,
    sanitize_text,
)
from app.domain.entities.discovery import (
    CompanyProfile,
    DiscoveryJob,
    Evidence,
    EvidenceSource,
    JobState,
    PersonProfile,
    SourceDiagnostic,
    generate_source_id,
)
from app.domain.exceptions import SourceUnavailableError

logger = logging.getLogger(__name__)


def _canonicalize_url(url: str) -> str:
    """Canonicalize a URL: lowercase scheme/host, strip www., query params, fragment, trailing slash."""
    if not url:
        return ""
    try:
        u = url.strip()
        if not u.startswith(("http://", "https://")):
            u = f"https://{u}"
        parsed = urllib.parse.urlsplit(u)
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        path = parsed.path.rstrip("/")
        return urllib.parse.urlunsplit((scheme, netloc, path, "", ""))
    except Exception:
        return url.strip()


def _content_hash(text: str | None) -> str:
    """Return SHA-256 hex digest of normalized whitespace text."""
    if not text:
        return ""
    norm = " ".join(text.split())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest() if norm else ""


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
        source_registry: EvidenceRegistryPort | None = None,
    ) -> None:
        self._job_store = job_store
        self._profile_scraper = profile_scraper
        self._page_fetcher = page_fetcher
        self._report_extractor = report_extractor
        self._report_import = report_import
        self._source_registry = source_registry
    
    async def execute(self, job: DiscoveryJob) -> None:
        """Run the full discovery pipeline. Updates job state as it progresses."""
        try:
            job.transition_to(JobState.RUNNING)
            await self._job_store.update(job)
            
            evidence = Evidence()
            
            # Step 1: Fetch website pages (discovers sitemap, about/team pages, company & founder LinkedIn URLs)
            await self._fetch_website(job, evidence)
            
            # Step 2: Scrape LinkedIn company (using confirmed or newly discovered LinkedIn URL, or slugified fallback on name match)
            await self._scrape_company(job, evidence)
            
            # Step 3: Scrape LinkedIn founders (using confirmed or discovered URLs from website team page)
            await self._scrape_founders(job, evidence)
            
            # Step 4: Fetch news articles
            await self._fetch_news(job, evidence)

            # Step 4b: Multi-source evidence collection (RDAP, Wikidata, News, Wayback)
            await self._collect_multi_sources(job, evidence)

            # Step 4c: Apply manual evidence if provided (text / PDF)
            self._apply_manual_evidence(job, evidence)
            
            # Check LLM availability and record explicit warning if unavailable
            if hasattr(self._report_extractor, "_llm") and self._report_extractor._llm:
                try:
                    if not await self._report_extractor._llm.is_available():
                        job.add_warning("LLM enrichment unavailable: model not found")
                        evidence.warnings.append("LLM enrichment unavailable: model not found")
                except Exception:
                    job.add_warning("LLM enrichment unavailable: model not found")
                    evidence.warnings.append("LLM enrichment unavailable: model not found")

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
            job.result_slug = getattr(result, "company_slug", str(result))
            
            # Determine final state: A job where every source failed must end PARTIAL (or FAILED), never SUCCEEDED.
            successful_sources = [d for d in job.diagnostics if d.outcome == "ok"]
            if not successful_sources or job.warnings:
                if not successful_sources and not any("source" in w.lower() for w in job.warnings):
                    job.add_warning("All external data sources failed or returned empty content.")
                job.transition_to(JobState.PARTIAL)
            else:
                job.transition_to(JobState.SUCCEEDED)
            
            job.update_progress("Complete", 1.0)
            await self._job_store.update(job)
            
            logger.info(
                "Discovery job %s completed: status=%s slug=%s warnings=%d diagnostics=%d",
                job.id, job.state.value, result.company_slug, len(job.warnings), len(job.diagnostics),
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
    
    async def _fetch_website(self, job: DiscoveryJob, evidence: Evidence) -> None:
        url = job.confirmed_urls.get("website")
        if not url:
            job.add_warning("No website URL provided")
            diag = SourceDiagnostic(
                url="website:official",
                outcome="empty_text",
                error_details="No website URL provided",
            )
            job.add_diagnostic(diag)
            evidence.diagnostics.append(diag)
            return

        job.update_progress("Fetching website", 0.1)
        await self._job_store.update(job)

        base = url.rstrip("/")
        if not base.startswith("http"):
            base = f"https://{base}"

        fetched_any = False
        home_page = None
        seen_content_hashes: dict[str, str] = {}
        seen_canonical_urls: set[str] = set()
        duplicate_count = 0

        # 1. Fetch homepage
        try:
            home_page, diag = await self._page_fetcher.fetch_with_diagnostic(base)
            job.add_diagnostic(diag)
            evidence.diagnostics.append(diag)
            if home_page and (home_page.text.strip() or home_page.description or home_page.json_ld):
                evidence.website_pages.append(home_page)
                h_url = home_page.url or base
                canon_home = _canonicalize_url(h_url)
                if canon_home:
                    seen_canonical_urls.add(canon_home)

                h_hash = _content_hash(home_page.text)
                if h_hash:
                    seen_content_hashes[h_hash] = h_url

                evidence.sources.append(EvidenceSource(
                    source_id=generate_source_id(h_url),
                    url=h_url,
                    publisher=_extract_domain(h_url),
                    source_type="COMPANY_WEBSITE",
                    retrieved_at=home_page.retrieved_at,
                ))
                fetched_any = True

                # Discovered company LinkedIn from homepage
                if "company_linkedin" not in job.confirmed_urls and home_page.social_links.get("linkedin"):
                    job.confirmed_urls["company_linkedin"] = home_page.social_links["linkedin"]
                    logger.info("Discovered company LinkedIn from website: %s", job.confirmed_urls["company_linkedin"])

                # Discovered founder LinkedIn links from homepage
                for founder in job.founder_names:
                    f_key = f"founder_linkedin_{_slugify(founder)}"
                    if f_key not in job.confirmed_urls:
                        for k, v in home_page.social_links.items():
                            if k.startswith("linkedin_person_") and _slugify(founder) in k.lower():
                                job.confirmed_urls[f_key] = v
                                break
        except Exception as exc:
            diag = SourceDiagnostic(url=base, outcome="http_error:0", error_details=str(exc))
            job.add_diagnostic(diag)
            evidence.diagnostics.append(diag)

        # 2. Gather candidate subpages: in-page links + sitemap.xml
        candidate_urls: list[str] = []
        has_nav_links = bool(home_page and home_page.links)
        if has_nav_links:
            candidate_urls.extend(home_page.links)

        has_sitemap = False
        try:
            sitemap_links = await self._page_fetcher.fetch_sitemap_urls(base)
            if sitemap_links:
                has_sitemap = True
                for sm_link in sitemap_links:
                    if sm_link not in candidate_urls and sm_link != base:
                        candidate_urls.append(sm_link)
        except Exception:
            pass

        # Stop guessing paths when sitemap.xml or nav links exist!
        if not candidate_urls and not has_sitemap and not has_nav_links:
            candidate_urls = [f"{base}{p}" for p in ["/about", "/product", "/services", "/team"]]

        # Filter out /blog, /glossary, /dev-, /v2-, /tag, /category paths
        skip_pattern = re.compile(r"/(?:blog|blogs|glossary|dev-|v2-|tag|category)", re.I)
        filtered_candidates = [
            u for u in candidate_urls
            if not skip_pattern.search(urllib.parse.urlsplit(u).path)
        ]

        # Prioritize: about, team, product, solution, customers, press, pricing, careers
        def _priority_score(u: str) -> int:
            path = urllib.parse.urlsplit(u).path.lower()
            if "about" in path:
                return 0
            if "team" in path or "people" in path or "leadership" in path:
                return 1
            if "product" in path or "feature" in path or "platform" in path:
                return 2
            if "customer" in path or "client" in path:
                return 3
            if "solution" in path:
                return 4
            if "press" in path:
                return 5
            if "pricing" in path:
                return 6
            if "career" in path:
                return 7
            return 8

        # Deduplicate candidates using canonicalize_url
        unique_candidates: list[str] = []
        for u in filtered_candidates:
            canon = _canonicalize_url(u)
            if canon and canon not in seen_canonical_urls:
                seen_canonical_urls.add(canon)
                unique_candidates.append(u)

        unique_candidates.sort(key=_priority_score)

        # Check robots.txt BEFORE queueing so blocked URLs don't consume the ~8-page budget
        subpages_to_fetch: list[str] = []
        for cand in unique_candidates:
            if len(subpages_to_fetch) >= 7:
                break
            try:
                allowed = await self._page_fetcher.is_allowed(cand)
            except Exception:
                allowed = True
            if not allowed:
                diag = SourceDiagnostic(
                    url=cand,
                    outcome="robots_blocked",
                    bytes_fetched=0,
                    error_details="Blocked by robots.txt rules (pre-check)",
                )
                job.add_diagnostic(diag)
                evidence.diagnostics.append(diag)
                continue
            subpages_to_fetch.append(cand)

        for page_url in subpages_to_fetch:
            try:
                sub_page, diag = await self._page_fetcher.fetch_with_diagnostic(page_url)
                if not sub_page or not (sub_page.text.strip() or sub_page.description or sub_page.json_ld):
                    job.add_diagnostic(diag)
                    evidence.diagnostics.append(diag)
                    continue

                # Content hash deduplication (detect catch-all/SPA pages)
                sub_hash = _content_hash(sub_page.text)
                if sub_hash and sub_hash in seen_content_hashes:
                    first_url = seen_content_hashes[sub_hash]
                    duplicate_count += 1
                    dup_diag = SourceDiagnostic(
                        url=page_url,
                        outcome=f"duplicate_of:{first_url}",
                        bytes_fetched=diag.bytes_fetched,
                        fields_extracted=[],
                        error_details=f"Identical content to {first_url} (SPA catch-all)",
                    )
                    job.add_diagnostic(dup_diag)
                    evidence.diagnostics.append(dup_diag)
                    continue

                if sub_hash:
                    seen_content_hashes[sub_hash] = page_url

                # Distinct page! Add to evidence and register source
                job.add_diagnostic(diag)
                evidence.diagnostics.append(diag)
                evidence.website_pages.append(sub_page)
                fetched_any = True

                evidence.sources.append(EvidenceSource(
                    source_id=generate_source_id(page_url),
                    url=page_url,
                    publisher=_extract_domain(page_url),
                    source_type="COMPANY_WEBSITE",
                    retrieved_at=sub_page.retrieved_at,
                ))

                # Link discovery from subpage
                if "company_linkedin" not in job.confirmed_urls and sub_page.social_links.get("linkedin"):
                    job.confirmed_urls["company_linkedin"] = sub_page.social_links["linkedin"]

                for founder in job.founder_names:
                    f_key = f"founder_linkedin_{_slugify(founder)}"
                    if f_key not in job.confirmed_urls:
                        for k, v in sub_page.social_links.items():
                            if k.startswith("linkedin_person_") and _slugify(founder) in k.lower():
                                job.confirmed_urls[f_key] = v
                                break
            except Exception as exc:
                diag = SourceDiagnostic(url=page_url, outcome="http_error:0", error_details=str(exc))
                job.add_diagnostic(diag)
                evidence.diagnostics.append(diag)

        if duplicate_count >= 2 or (duplicate_count > 0 and len(evidence.website_pages) <= 1):
            spa_warning = "site appears JavaScript-rendered; limited content"
            if spa_warning not in job.warnings:
                job.add_warning(spa_warning)
                evidence.warnings.append(spa_warning)

        if not fetched_any:
            job.add_warning(f"Could not fetch any website pages from: {url}")

    async def _scrape_company(self, job: DiscoveryJob, evidence: Evidence) -> None:
        url = job.confirmed_urls.get("company_linkedin")

        # Link discovery fallback: try linkedin.com/company/<slugified-name> and accept ONLY on name match
        if not url:
            slug_url = f"https://www.linkedin.com/company/{_slugify(job.company_name).replace('_', '-')}"
            try:
                cand_profile, cand_diag = await self._profile_scraper.fetch_company_with_diagnostic(slug_url)
                if cand_profile and cand_profile.name and _is_name_match(cand_profile.name, job.company_name):
                    logger.info("Accepted slug LinkedIn match for %s: %s", job.company_name, slug_url)
                    url = slug_url
                    job.confirmed_urls["company_linkedin"] = url
                    job.add_diagnostic(cand_diag)
                    evidence.diagnostics.append(cand_diag)
                    evidence.company_profile = cand_profile
                    evidence.sources.append(EvidenceSource(
                        source_id=generate_source_id(url),
                        url=url,
                        publisher="linkedin.com",
                        source_type="SOCIAL_MEDIA",
                        retrieved_at=cand_profile.retrieved_at,
                    ))
                    if cand_profile.is_auth_walled:
                        job.add_warning(f"Company LinkedIn page is auth-walled: {url}")
                        self._apply_company_snippet_fallback(job, evidence)
                    return
                else:
                    logger.info("Rejected slug LinkedIn candidate %s: entity mismatch", slug_url)
            except Exception:
                pass

        if not url:
            job.add_warning("No company LinkedIn URL provided")
            diag = SourceDiagnostic(
                url="linkedin:company",
                outcome="empty_text",
                error_details="No company LinkedIn URL provided",
            )
            job.add_diagnostic(diag)
            evidence.diagnostics.append(diag)
            self._apply_company_snippet_fallback(job, evidence)
            return
        
        job.update_progress("Scraping company LinkedIn", 0.3)
        await self._job_store.update(job)
        
        try:
            profile, diag = await self._profile_scraper.fetch_company_with_diagnostic(url)
            job.add_diagnostic(diag)
            evidence.diagnostics.append(diag)
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
                    self._apply_company_snippet_fallback(job, evidence)
            else:
                job.add_warning(f"Could not fetch company LinkedIn: {url}")
                self._apply_company_snippet_fallback(job, evidence)
        except Exception as exc:
            diag = SourceDiagnostic(url=url, outcome="http_error:0", error_details=str(exc))
            job.add_diagnostic(diag)
            evidence.diagnostics.append(diag)
            job.add_warning(f"Error scraping company LinkedIn: {exc}")
            self._apply_company_snippet_fallback(job, evidence)

    def _apply_company_snippet_fallback(self, job: DiscoveryJob, evidence: Evidence) -> None:
        """When company LinkedIn is auth-walled or missing, use search snippet as labelled weaker source."""
        snippet = getattr(job, "search_snippets", {}).get("company")
        if snippet:
            evidence.search_snippets["company"] = snippet
            src_id = f"src_snippet_{_slugify(job.company_name)[:8]}"
            evidence.sources.append(EvidenceSource(
                source_id=src_id,
                url=job.confirmed_urls.get("company_linkedin", f"search:snippet:{_slugify(job.company_name)}"),
                publisher="Search snippet",
                title=f"{job.company_name} (Search snippet)",
                source_type="SEARCH_SNIPPET",
                retrieved_at=datetime.now(timezone.utc).isoformat(),
            ))
    
    async def _scrape_founders(self, job: DiscoveryJob, evidence: Evidence) -> None:
        job.update_progress("Scraping founder profiles", 0.5)
        await self._job_store.update(job)
        
        for name in job.founder_names:
            slug_key = f"founder_linkedin_{_slugify(name)}"
            url = job.confirmed_urls.get(slug_key)
            if not url:
                job.add_warning(f"No LinkedIn URL for founder: {name}")
                diag = SourceDiagnostic(
                    url=f"linkedin:founder:{name}",
                    outcome="empty_text",
                    error_details=f"No LinkedIn URL for founder: {name}",
                )
                job.add_diagnostic(diag)
                evidence.diagnostics.append(diag)
                self._apply_founder_snippet_fallback(job, evidence, name)
                continue
            
            try:
                profile, diag = await self._profile_scraper.fetch_person_with_diagnostic(url)
                job.add_diagnostic(diag)
                evidence.diagnostics.append(diag)
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
                        self._apply_founder_snippet_fallback(job, evidence, name)
                else:
                    job.add_warning(f"Could not fetch LinkedIn for {name}: {url}")
                    self._apply_founder_snippet_fallback(job, evidence, name)
            except Exception as exc:
                diag = SourceDiagnostic(url=url, outcome="http_error:0", error_details=str(exc))
                job.add_diagnostic(diag)
                evidence.diagnostics.append(diag)
                job.add_warning(f"Error scraping LinkedIn for {name}: {exc}")
                self._apply_founder_snippet_fallback(job, evidence, name)

    def _apply_founder_snippet_fallback(self, job: DiscoveryJob, evidence: Evidence, name: str) -> None:
        """When founder LinkedIn is auth-walled or missing, use search snippet as labelled weaker source."""
        snippet = getattr(job, "search_snippets", {}).get(f"founder_{_slugify(name)}")
        if snippet:
            evidence.search_snippets[f"founder_{_slugify(name)}"] = snippet
            src_id = f"src_snippet_{_slugify(name)[:8]}"
            evidence.sources.append(EvidenceSource(
                source_id=src_id,
                url=job.confirmed_urls.get(f"founder_linkedin_{_slugify(name)}", f"search:snippet:{_slugify(name)}"),
                publisher="Search snippet",
                title=f"{name} (Search snippet)",
                source_type="SEARCH_SNIPPET",
                retrieved_at=datetime.now(timezone.utc).isoformat(),
            ))
    
    async def _fetch_news(self, job: DiscoveryJob, evidence: Evidence) -> None:
        job.update_progress("Fetching news articles", 0.5)
        await self._job_store.update(job)
        
        news_urls = [
            v for k, v in job.confirmed_urls.items()
            if k.startswith("news_")
        ]
        
        for url in news_urls:
            try:
                page, diag = await self._page_fetcher.fetch_with_diagnostic(url)
                job.add_diagnostic(diag)
                evidence.diagnostics.append(diag)
                logger.info(
                    "Discovery job %s diagnostic: source=%s outcome=%s bytes=%d fields=%s",
                    job.id, diag.url, diag.outcome, diag.bytes_fetched, diag.fields_extracted,
                )
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
                diag = SourceDiagnostic(url=url, outcome="http_error:0", error_details=str(exc))
                job.add_diagnostic(diag)
                evidence.diagnostics.append(diag)
                logger.info(
                    "Discovery job %s diagnostic: source=%s outcome=%s bytes=%d fields=%s",
                    job.id, diag.url, diag.outcome, diag.bytes_fetched, diag.fields_extracted,
                )
                job.add_warning(f"Could not fetch news article: {url} — {exc}")

    async def _collect_multi_sources(self, job: DiscoveryJob, evidence: Evidence) -> None:
        if not self._source_registry:
            return

        job.update_progress("Collecting multi-source evidence", 0.6)
        await self._job_store.update(job)

        context = DiscoveryContext(
            company_name=job.company_name,
            founder_names=job.founder_names,
            website_url=job.confirmed_urls.get("website"),
            confirmed_urls=job.confirmed_urls,
            job_id=job.id,
        )

        try:
            items, diags = await self._source_registry.collect_all(context)
            for d in diags:
                job.add_diagnostic(d)
                evidence.diagnostics.append(d)
                logger.info(
                    "Discovery job %s multi-source diagnostic: source=%s outcome=%s bytes=%d fields=%s",
                    job.id, d.url, d.outcome, d.bytes_fetched, d.fields_extracted,
                )

            for item in items:
                evidence.sources.append(EvidenceSource(
                    source_id=item.source_id,
                    url=item.url,
                    publisher=item.publisher or "Multi-Source Registry",
                    title=item.title,
                    source_type=item.source_type,
                    retrieved_at=item.retrieved_at,
                ))

                for fld in item.extracted_fields:
                    existing = evidence.multi_source_fields.get(fld.field_name)
                    if existing is None or fld.confidence > existing.confidence:
                        evidence.multi_source_fields[fld.field_name] = fld

                        if fld.field_name == "founded_year":
                            if evidence.company_profile and not evidence.company_profile.founded_year:
                                evidence.company_profile = CompanyProfile(
                                    name=evidence.company_profile.name,
                                    description=evidence.company_profile.description,
                                    industry=evidence.company_profile.industry,
                                    company_size=evidence.company_profile.company_size,
                                    headquarters=evidence.company_profile.headquarters,
                                    website=evidence.company_profile.website,
                                    founded_year=str(fld.value),
                                    specialties=evidence.company_profile.specialties,
                                    followers=evidence.company_profile.followers,
                                    logo_url=evidence.company_profile.logo_url,
                                    tagline=evidence.company_profile.tagline,
                                    url=evidence.company_profile.url,
                                    retrieved_at=evidence.company_profile.retrieved_at,
                                    is_auth_walled=evidence.company_profile.is_auth_walled,
                                    raw_json_ld=evidence.company_profile.raw_json_ld,
                                )
        except Exception as exc:
            logger.warning("Discovery job %s multi-source error: %s", job.id, exc)
            job.add_warning(f"Multi-source collection encountered warning: {exc}")

    def _apply_manual_evidence(self, job: DiscoveryJob, evidence: Evidence) -> None:
        """Apply user-provided manual evidence (text/PDF), labelled 'provided by user (unverified)'."""
        if not job.manual_evidence:
            return

        evidence.manual_evidence = job.manual_evidence
        now_iso = datetime.now(timezone.utc).isoformat()

        for category, item in job.manual_evidence.items():
            if not isinstance(item, dict):
                continue

            text_part = item.get("text") or ""
            pdf_b64 = item.get("pdf_base64")
            pdf_filename = item.get("pdf_filename") or "manual_document.pdf"
            pdf_text = ""

            if pdf_b64:
                try:
                    pdf_bytes = base64.b64decode(pdf_b64)
                    pdf_text = extract_pdf_text(pdf_bytes)
                except Exception as exc:
                    logger.warning("Failed to parse manual PDF for %s: %s", category, exc)
                    job.add_warning(f"Could not extract text from uploaded PDF for {category}")

            combined_text = sanitize_text(f"{text_part}\n{pdf_text}".strip())
            if not combined_text:
                continue

            parsed = parse_manual_profile_text(combined_text)

            src_id = generate_source_id(f"manual_{category}_{job.id}")
            src = EvidenceSource(
                source_id=src_id,
                url=f"manual:{category}",
                publisher="provided by user (unverified)",
                title=pdf_filename if pdf_b64 else f"User-provided text ({category})",
                source_type="USER_SUPPLIED",
                retrieved_at=now_iso,
            )
            evidence.sources.append(src)

            diag = SourceDiagnostic(
                url=f"manual:{category}",
                outcome="ok",
                bytes_fetched=len(combined_text.encode("utf-8")),
                fields_extracted=[k for k, v in parsed.items() if v],
            )
            job.add_diagnostic(diag)
            evidence.diagnostics.append(diag)

            if category in ("company_linkedin", "website"):
                desc = parsed.get("description") or combined_text[:800]
                if not evidence.company_profile:
                    evidence.company_profile = CompanyProfile(
                        name=job.company_name,
                        tagline=parsed.get("headline"),
                        description=desc,
                        url=f"manual:{category}",
                    )
                elif not evidence.company_profile.description:
                    evidence.company_profile = CompanyProfile(
                        name=evidence.company_profile.name or job.company_name,
                        description=desc,
                        industry=evidence.company_profile.industry,
                        company_size=evidence.company_profile.company_size,
                        headquarters=evidence.company_profile.headquarters,
                        website=evidence.company_profile.website,
                        founded_year=evidence.company_profile.founded_year,
                        specialties=evidence.company_profile.specialties,
                        followers=evidence.company_profile.followers,
                        logo_url=evidence.company_profile.logo_url,
                        tagline=evidence.company_profile.tagline or parsed.get("headline"),
                        url=evidence.company_profile.url or f"manual:{category}",
                        retrieved_at=evidence.company_profile.retrieved_at,
                        is_auth_walled=evidence.company_profile.is_auth_walled,
                        raw_json_ld=evidence.company_profile.raw_json_ld,
                    )
            else:
                matched_founder = None
                for fname in job.founder_names:
                    slug = re.sub(r"[^a-z0-9]+", "_", fname.lower()).strip("_")
                    if slug in category.lower() or fname.lower() in category.lower():
                        matched_founder = fname
                        break
                if not matched_founder and job.founder_names:
                    matched_founder = job.founder_names[0]

                if matched_founder:
                    existing_p = next(
                        (p for p in evidence.founder_profiles if p.name and p.name.lower() == matched_founder.lower()),
                        None
                    )
                    edu = parsed.get("education") or []
                    exp = parsed.get("experience") or []
                    headline = parsed.get("headline") or "provided by user (unverified)"
                    summary = parsed.get("summary") or combined_text[:400]

                    if existing_p:
                        evidence.founder_profiles.remove(existing_p)
                        merged_p = PersonProfile(
                            name=existing_p.name or matched_founder,
                            headline=existing_p.headline or headline,
                            location=existing_p.location,
                            summary=existing_p.summary or summary,
                            education=existing_p.education if existing_p.education else edu,
                            experience=existing_p.experience if existing_p.experience else exp,
                            follower_count=existing_p.follower_count,
                            connection_count=existing_p.connection_count,
                            avatar_url=existing_p.avatar_url,
                            url=existing_p.url or f"manual:{category}",
                            retrieved_at=existing_p.retrieved_at,
                            is_auth_walled=existing_p.is_auth_walled,
                            raw_json_ld=existing_p.raw_json_ld,
                        )
                        evidence.founder_profiles.append(merged_p)
                    else:
                        new_p = PersonProfile(
                            name=matched_founder,
                            headline=headline,
                            summary=summary,
                            education=edu,
                            experience=exp,
                            url=f"manual:{category}",
                        )
                        evidence.founder_profiles.append(new_p)



import re

def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")

def _extract_domain(url: str) -> str:
    match = re.search(r"(?:https?://)?(?:www\.)?([^/]+)", url)
    return match.group(1) if match else url


def _is_name_match(scraped_name: str | None, target_name: str) -> bool:
    """Check if scraped company name matches target entity name."""
    if not scraped_name or not target_name:
        return False
    s_clean = re.sub(r"[^a-z0-9]", "", scraped_name.lower())
    t_clean = re.sub(r"[^a-z0-9]", "", target_name.lower())
    return s_clean == t_clean or s_clean in t_clean or t_clean in s_clean
