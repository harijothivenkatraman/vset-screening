# ADR 001: Company Discovery Feature Architecture

## Status
Accepted

## Context
vSET requires an automated discovery workflow allowing analysts or founders to input a company name and founder name(s), automatically harvest public digital footprints across LinkedIn, company websites, and news coverage, extract verified facts without fabrication, and output a standard 9-tab screening report that seamlessly fits the existing screening dashboard.

The application runs on resource-constrained infrastructure (AWS Lightsail with ~412MB RAM and 152MB available).

## Decision
1. **Clean Architecture with Inward Dependency Rule**:
   - `domain/entities/discovery.py` defines pure data structures (`DiscoveryJob`, `CompanyProfile`, `PersonProfile`, `PageContent`, `Evidence`, `SearchResult`) with zero framework dependencies.
   - `application/ports/` defines ABC interfaces for external concerns: `WebSearchPort`, `ProfileScraperPort`, `PageFetcherPort`, `LlmPort`, `ReportExtractorPort`, `CachePort`, `JobStorePort`, `ReportImportPort`.
   - `application/services/` holds use cases (`ResolveCandidatesService`, `StartDiscoveryJobService`, `GetDiscoveryJobService`, `BuildReportService`).
   - `infrastructure/` implements concrete adapters.
   - `presentation/` exposes REST endpoints and handles dependency injection.

2. **Rules-First Extraction with Remote LLM Enhancement**:
   - Primary report mapping is a deterministic pure function (`build_canonical_report`) that structures evidence into the canonical schema.
   - Information not present in public sources is recorded as `"Not established from public sources"` and tracked as an action gap.
   - Remote LLM (Ollama / vLLM over Tailscale) is queried only for concise summarization and sector tagging. If the remote LLM is unreachable or times out, the system gracefully falls back to the deterministic baseline without breaking or halting the job.

3. **Capped In-Memory Stores**:
   - Job store (`InMemoryJobStore`) is bounded (max 20 jobs) to respect strict 412MB RAM limits on Lightsail.
   - Page downloads are capped at 2MB with content-type verification.

## Consequences
- Clean separation of concerns allows swapping search providers, scrapers, or LLMs via configuration without rewriting application logic.
- Automated architecture test (`test_architecture.py`) ensures no outer layer leaks into domain or application layers.
- System is resilient to external network outages and strict hosting constraints.
