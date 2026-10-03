"""Script to evaluate live pipeline execution on dimdot and Mysa."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
import uuid

from app.application.ports.job_store_port import JobStorePort
from app.application.ports.report_import_port import ReportImportPort
from app.application.services.build_report import BuildReportService
from app.domain.entities.discovery import DiscoveryJob, JobState
from app.infrastructure.discovery.http.rate_limiter import HostRateLimiter
from app.infrastructure.discovery.llm.openai_compatible import OpenAICompatibleLlmAdapter
from app.infrastructure.discovery.llm.report_extractor import SectionBySectionExtractor
from app.infrastructure.discovery.scrapers.linkedin_public import LinkedInPublicScraper
from app.infrastructure.discovery.scrapers.website_fetcher import WebsiteFetcherAdapter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("eval")


from app.infrastructure.discovery.jobs.in_memory_job_store import InMemoryJobStore


from app.application.ports.report_import_port import ImportResult, ReportImportPort


class CapturingReportImportAdapter(ReportImportPort):
    def __init__(self) -> None:
        self.imported_reports: dict[str, dict] = {}

    async def import_report(self, report_json: dict) -> ImportResult:
        slug = report_json["canonical"]["meta"]["report_id"]
        self.imported_reports[slug] = report_json
        return ImportResult(status="created", company_slug=slug, message="Successfully imported")


async def run_discovery_eval(
    company_name: str,
    founder_names: list[str],
    confirmed_urls: dict[str, str],
    search_snippets: dict[str, str] | None = None,
) -> tuple[DiscoveryJob, dict | None]:
    job_id = f"job-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)
    job = DiscoveryJob(
        id=job_id,
        company_name=company_name,
        founder_names=founder_names,
        state=JobState.QUEUED,
        stage="Queued",
        progress=0.0,
        warnings=[],
        result_slug=None,
        created_at=now,
        updated_at=now,
        confirmed_urls=confirmed_urls,
        search_snippets=search_snippets or {},
    )

    job_store = InMemoryJobStore()
    await job_store.create(job)

    rate_limiter = HostRateLimiter(min_interval_seconds=1.0)
    profile_scraper = LinkedInPublicScraper(rate_limiter=rate_limiter, timeout_seconds=8.0)
    page_fetcher = WebsiteFetcherAdapter(rate_limiter=rate_limiter, timeout_seconds=8.0, check_robots=True)
    llm = OpenAICompatibleLlmAdapter(base_url="http://127.0.0.1:11434/v1", model="qwen2.5:7b-instruct", timeout_seconds=10.0)
    report_extractor = SectionBySectionExtractor(llm=llm)
    report_importer = CapturingReportImportAdapter()

    service = BuildReportService(
        job_store=job_store,
        profile_scraper=profile_scraper,
        page_fetcher=page_fetcher,
        report_extractor=report_extractor,
        report_import=report_importer,
    )

    await service.execute(job)
    final_job = await job_store.get(job_id)
    report = report_importer.imported_reports.get(final_job.result_slug) if final_job.result_slug else None
    return final_job, report


def print_evaluation_summary(label: str, job: DiscoveryJob, report: dict | None) -> None:
    print(f"\n{'='*70}\nEVALUATION: {label}\n{'='*70}")
    print(f"Job ID: {job.id}")
    print(f"Company: {job.company_name}")
    print(f"State: {job.state.value.upper()}")
    print(f"Result Slug: {job.result_slug}")
    print(f"Warnings ({len(job.warnings)}):")
    for w in job.warnings:
        print(f"  - {w}")

    print(f"\nRETRIEVAL LOG ({len(job.diagnostics)} sources attempted):")
    print(f"{'-'*70}")
    print(f"{'URL':<45} | {'Outcome':<14} | {'Bytes':<8} | {'Fields'}")
    print(f"{'-'*70}")
    for d in job.diagnostics:
        fields_str = ", ".join(d.fields_extracted) if d.fields_extracted else "-"
        print(f"{d.url[:45]:<45} | {d.outcome:<14} | {d.bytes_fetched:<8} | {fields_str}")
    print(f"{'-'*70}")

    if report:
        sections = report.get("canonical", {}).get("content", {}).get("sections", [])
        print("\nREPORT EXTRACTS:")
        for s in sections:
            print(f"\n--- Section: {s.get('title')} ({s.get('key')}) ---")
            for b in s.get("blocks", []):
                b_type, b_title = b[0], b[1]
                if b_type == "para":
                    print(f"  [{b_title}]: {b[2][:200] if isinstance(b[2], str) else b[2]}")
                elif b_type == "kv":
                    print(f"  [{b_title}]: {b[2]}")
                elif b_type == "cards":
                    print(f"  [{b_title}]: {len(b[2])} card(s)")
                    for card in b[2]:
                        print(f"    - {card.get('name')} | {card.get('role')} | lines: {card.get('lines')}")
                elif b_type == "list" and "Information gaps" in str(b_title):
                    print(f"  [{b_title}] ({len(b[2])} real gaps):")
                    for g in b[2]:
                        print(f"    * {g}")
    else:
        print("\nNO REPORT PRODUCED (Pipeline failed)")


async def main() -> None:
    # 1. Dimdot evaluation (no manual website passed, testing fallback & website-discovery)
    print("\n>>> Running Dimdot evaluation (Automatic / No confirmed URLs)...")
    job_dimdot, report_dimdot = await run_discovery_eval(
        company_name="dimdot",
        founder_names=["Alice"],
        confirmed_urls={},
    )
    print_evaluation_summary("dimdot (No confirmed URLs)", job_dimdot, report_dimdot)

    # 1b. Dimdot with website confirmed (dimdot.com)
    print("\n>>> Running Dimdot evaluation (With confirmed website https://dimdot.com)...")
    job_dimdot_site, report_dimdot_site = await run_discovery_eval(
        company_name="dimdot",
        founder_names=["Alice"],
        confirmed_urls={"website": "https://dimdot.com"},
    )
    print_evaluation_summary("dimdot (With https://dimdot.com)", job_dimdot_site, report_dimdot_site)

    # 2. Mysa evaluation (website mysa.io, founders Arpita Kapoor, Mohit Rangaraju, Ashutosh Panigrahi)
    print("\n>>> Running Mysa evaluation (With confirmed website https://mysa.io)...")
    job_mysa, report_mysa = await run_discovery_eval(
        company_name="Mysa",
        founder_names=["Arpita Kapoor", "Mohit Rangaraju", "Ashutosh Panigrahi"],
        confirmed_urls={"website": "https://mysa.io"},
    )
    print_evaluation_summary("Mysa (https://mysa.io)", job_mysa, report_mysa)


if __name__ == "__main__":
    asyncio.run(main())
