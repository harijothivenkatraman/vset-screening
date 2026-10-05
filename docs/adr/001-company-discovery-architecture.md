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

4. **LinkedIn Best-Effort & Datacenter vs. Residential IP Policy**:
   - LinkedIn public profile extraction relies on public Schema.org JSON-LD and OpenGraph tags, which parse cleanly from residential IPs.
   - Datacenter IPs (such as AWS Lightsail, EC2, GCP) are immediately presented with Cloudflare challenges (HTTP 403, `challenges.cloudflare.com`). The system strictly forbids attempting to solve or bypass challenges.
   - LinkedIn is treated as best-effort: failures yield outcome `blocked_by_bot_protection` with no retries beyond one. A circuit breaker pauses LinkedIn calls for 30 minutes after 3 consecutive blocks (`circuit_breaker_open`), and Tab 9 limitations plainly declare `"LinkedIn could not be retrieved from this server."`
   - When LinkedIn is unavailable, the pipeline falls back to deep website extraction (sitemap, /team, /about), ICANN RDAP registration date, structured news/GDELT, and user-supplied manual evidence.

5. **Dedicated "Founder profiles" Tab (Reversal of "Source Only" Decision)**:
   - Earlier design treated LinkedIn purely as an evidence source feeding other sections without its own tab.
   - This decision is REVERSED: a dedicated "Founder profiles" tab (`founder_profiles`) is introduced adjacent to "Founder & team".
   - Each founder of a discovered company gets a structured profile card (headline, location, about, experience timeline, education, skills, certifications) with clear provenance (source and retrieval timestamp).
   - When LinkedIn is blocked by bot protection on datacenter IPs, an honest empty state is presented with an invitation to provide evidence manually via Candidate Review text/PDF upload.
   - Strict identity verification requires strong signals (website near name, domain links, user confirmed) to auto-attach, preventing same-name false matches (e.g. thermostat company named Mysa).
   - Cross-checks between website claims and LinkedIn profiles normalize titles (e.g. CEO == Chief Executive Officer) and report discrepancies with low-severity label "Differences found - verify".

6. **Audit Snapshot Sanitization for Privacy & Data Protection**:
   - Earlier design stored untouched raw JSON payloads in the `raw_snapshots` audit table.
   - Decision: Audit snapshots are now explicitly SANITIZED before persistence to eliminate sensitive PII (emails, mobile phone numbers, personal contact blocks, profile photos/avatars, or unparsed raw CV text/PDF base64 payloads).
   - Non-PII business metrics (dates, currency amounts, identifiers, version strings, and schema definitions) are rigorously preserved without alteration.
   - The canonical content fingerprint (`final_fingerprint` and `canonical_content_fingerprint`) is computed before snapshot sanitization, guaranteeing report import idempotency remains intact.

## Consequences
- Clean separation of concerns allows swapping search providers, scrapers, or LLMs via configuration without rewriting application logic.
- Automated architecture test (`test_architecture.py`) ensures no outer layer leaks into domain or application layers.
- Production deployments on Lightsail remain reliable and transparent when datacenter bot protection blocks LinkedIn, without stalling jobs or generating false failures.
- Analysts and founders have immediate visibility into founder operating track records with explicit provenance.
- Audit records adhere strictly to data privacy standards without storing untracked PII.

