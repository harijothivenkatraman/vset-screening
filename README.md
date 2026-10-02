# vSET Startup Screening Dashboard

A professional B2B platform presenting startup screening reports and automated **Company Discovery**, built with Clean Architecture. All data lives in a database and is served via a versioned REST API. The frontend is entirely data-driven with no hard-coded company or report content.

---

## Key Features

- **Standard 9-Tab Screening Dashboard**: Comprehensive startup analysis covering Company, Team, Product, Validation, Market, Competition, Funding, Actions (Due Diligence questions & documents), and Evidence Sources.
- **Automated Company Discovery**: Input a company name and founder name(s) to harvest public footprints across LinkedIn, company websites, and news coverage.
- **Strict Anti-Hallucination & Grounding**: Information not established from public sources is never fabricated; it is explicitly marked *"Not established from public sources"* and tracked under *"Information to prepare"*.
- **Extensible Block Renderer Registry**: Open/Closed frontend component registry rendering paragraphs, key-value tables, founder profile cards, matrices, and structured comparisons.
- **Resilient Multi-Provider Fallback**: Search fallback chain (SearXNG $\rightarrow$ DuckDuckGo $\rightarrow$ Manual URL override) with circuit breakers and rate limiting.
- **Privacy-Preserving & Resource-Bounded**: No cloud LLM subscriptions required. Runs local LLM inference (e.g. Ollama via Tailscale), unauthenticated public scrapers, SSRF protection, and memory bounds suitable for budget cloud instances (AWS Lightsail).

---

## Architecture & Tech Stack

### Backend
- **Framework:** FastAPI (Python 3.12+ / 3.13)
- **Architecture:** Clean Architecture with 4 distinct inward-facing layers:
  - **Domain:** Pure Python entities and dataclasses (`Company`, `Report`, `Section`, `ActionItem`, `Source`, `DiscoveryJob`, `CompanyProfile`, `PersonProfile`, `Evidence`), zero framework dependencies.
  - **Application:** Use cases (`ListCompanies`, `GetSection`, `ImportReport`, `ResolveCandidates`, `StartDiscoveryJob`, `GetDiscoveryJob`, `BuildReport`), repository and service port interfaces (ABCs), and mappers.
  - **Infrastructure:** SQLAlchemy 2.0 (async), Alembic migrations, PostgreSQL / SQLite engines, version gate, and discovery adapters:
    - *Search*: `FallbackSearchAdapter`, `SearXNGSearchAdapter`, `DuckDuckGoSearchAdapter`, with `CircuitBreaker`.
    - *Scrapers*: `LinkedInPublicScraper` (unauthenticated JSON-LD + OpenGraph), `WebsiteFetcherAdapter` (SSRF guard, 2MB cap, robots.txt), `NewsFetcherAdapter`.
    - *LLM & Extraction*: `OpenAICompatibleLlmAdapter` (Ollama/vLLM), `SectionBySectionExtractor` (rules-first baseline + LLM summary enrichment).
    - *Cache & Job Store*: `InMemoryTtlCache` (TTL, bounded), `InMemoryJobStore` (memory-capped for low-RAM hosts).
  - **Presentation:** FastAPI versioned routers, Pydantic v2 schemas, `api_key_guard` authentication, image proxy, and dependency injection composition root.
- **Idempotency & Auditing:** Ingestion keyed on `canonical_screen_id` with `final_fingerprint` change detection.

### Frontend
- **Framework:** React 19 + TypeScript (strict mode) + Vite
- **Styling:** Tailwind CSS + CSS custom properties (design tokens) in `tokens.css` (professional B2B palette with restrained `#1e2a3a` navy accent and neutral slate greys).
- **Routing:** React Router v7 with deep links (`/companies/:slug/:sectionKey`, `/companies/:slug/actions`, `/companies/:slug/sources`, `/discover`).
- **Data Fetching:** TanStack React Query with cache factories, background polling, and error retry states.
- **Discovery Wizard:** Multi-step wizard (`DiscoveryForm` $\rightarrow$ `CandidateReview` with confidence scores $\rightarrow$ `JobProgress` with live status tracking and stage checklists).

---

## Directory Structure

```
├── backend/
│   ├── alembic/                 # Database migrations
│   ├── app/
│   │   ├── application/         # Use cases, 8 Port ABCs, mappers
│   │   │   ├── mappers/         # evidence_to_report_mapper, action_mapper, etc.
│   │   │   ├── ports/           # WebSearchPort, ProfileScraperPort, LlmPort, etc.
│   │   │   └── services/        # BuildReport, ResolveCandidates, StartDiscoveryJob, etc.
│   │   ├── domain/              # Pure entities, discovery models, exception hierarchy
│   │   ├── infrastructure/      # DB persistence, ingestion, and discovery adapters
│   │   │   ├── discovery/       # search, scrapers, llm, cache, jobs, http (SSRF guard)
│   │   │   ├── ingestion/       # import_service, version_gate, schema_validator
│   │   │   └── persistence/     # SQLAlchemy models and repositories
│   │   ├── presentation/        # FastAPI routers, schemas, dependencies, guards
│   │   │   ├── routers/         # companies, sections, actions, discovery, image_proxy
│   │   │   └── schemas/         # Pydantic request/response models
│   │   ├── config.py            # Typed settings (Pydantic Settings)
│   │   └── main.py              # Application entry point, lifespan, CORS
│   ├── tests/
│   │   ├── fakes/               # In-memory test doubles for all 8 ports
│   │   ├── unit/                # Domain, services, golden mapper, adapters, contracts
│   │   └── integration/         # Discovery API, 9-tab screening, import idempotency
│   ├── requirements.txt         # Python dependencies
│   └── seed.py                  # Seed script importing reference reports
│
├── frontend/
│   ├── src/
│   │   ├── app/                 # AppShell layout, router, QueryClient
│   │   ├── core/                # apiClient with auth headers
│   │   ├── features/
│   │   │   ├── companies/       # CompanySwitcher, hooks, API
│   │   │   ├── discovery/       # DiscoveryForm, CandidateReview, JobProgress, hooks
│   │   │   └── report/          # Shell, block renderers, sections, actions, sources
│   │   └── shared/              # Design tokens and shared UI primitives
│   └── tests/                   # Vitest unit tests (38 tests)
│
├── docs/
│   ├── adr/                     # Architecture Decision Records (001, 002)
│   ├── discovery.md             # Complete guide to Company Discovery & SearXNG/Ollama
│   ├── deployment-guide.md      # Zero-cost cloud deployment guide (Render/Vercel/Neon)
│   └── ui-guidelines.md         # UI tokens, typography, and block registry guide
│
├── aws-deployment-guide.md      # AWS Lightsail click-by-click deployment walkthrough
├── docker-compose.yml           # Production Compose stack (PostgreSQL, Backend, Caddy/Web)
└── reference/                   # Reference reports (TerraSpark & Mysa canonical JSON/PDFs)
```

---

## Quick Start Guide

### 1. Prerequisites
- Python 3.12+ (Python 3.13 recommended)
- Node.js 18+ and npm
- Docker (optional, for PostgreSQL and containerized production stack)

### 2. Backend Setup & Run

```powershell
# Navigate to backend
cd backend

# Create & activate virtual environment (Windows PowerShell)
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run database seed (imports TerraSpark and Mysa reference files)
python seed.py

# Start the backend server (runs on http://localhost:8000)
uvicorn app.main:app --reload --port 8000
```

Interactive OpenAPI documentation is available at:
👉 **`http://localhost:8000/docs`**

### 3. Frontend Setup & Run

```powershell
# Navigate to frontend (in a separate terminal)
cd frontend

# Install dependencies
npm install

# Start Vite development server (runs on http://localhost:5173)
npm run dev
```

Visit **`http://localhost:5173`** to access the dashboard, or click **"Discover Company"** in the top navigation bar to access the discovery wizard at **`http://localhost:5173/discover`**.

---

## Running Automated Tests

### Backend Test Suite (Pytest)
Executes **168 automated tests** covering domain state machines, use case logic, golden evidence-to-canonical report mapping, port contract tests for all real and fake adapters, SSRF/rate limiter security checks, architecture layer isolation, and end-to-end API integration tests:

```powershell
cd backend
.\.venv\Scripts\pytest -v
```

### Architecture Rule Enforcement
Ensures strict compliance with Clean Architecture dependency rules (domain and application layers cannot import from infrastructure, presentation, or external web frameworks):

```powershell
cd backend
.\.venv\Scripts\pytest tests/unit/test_architecture.py -v
```

### Frontend Test Suite (Vitest)
Executes **38 tests** verifying all block renderers (`para`, `kv`, `olist`, `list`, `table`, `cards`, `comparison` shapes), UI primitives, date formatters, and discovery components (`DiscoveryForm`, `CandidateReview`, `JobProgress`):

```powershell
cd frontend
npm test
```

### Production Build & Typecheck
```powershell
cd frontend
npx tsc --noEmit
npm run build
```

---

## API Endpoints Reference

All endpoints are versioned under `/api/v1`:

### Dashboard & Reporting Endpoints
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/companies` | List all available companies with stage/sector summary |
| `GET` | `/api/v1/companies/{slug}` | Cover metadata, ribbon chips, audience label, report date |
| `GET` | `/api/v1/companies/{slug}/sections` | Section navigation list for sidebar tabs (Tabs 1–7) |
| `GET` | `/api/v1/companies/{slug}/sections/{key}` | Section content blocks + "Information to prepare" |
| `GET` | `/api/v1/companies/{slug}/actions` | Tab 8: Investor questions (Part A) & documents (Part B) |
| `GET` | `/api/v1/companies/{slug}/sources` | Tab 9: Methodology, limitations, and evidence register |
| `POST` | `/api/v1/reports/import` | Ingest raw report JSON (guarded by `X-API-Key` header) |

### Company Discovery Endpoints
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/discovery/resolve` | Query web search for company/founder candidate URLs (`X-API-Key`) |
| `POST` | `/api/v1/discovery/jobs` | Enqueue background discovery & report build job (Returns `202 Accepted`) |
| `GET` | `/api/v1/discovery/jobs/{job_id}` | Poll real-time discovery job progress and stage status (`X-API-Key`) |
| `GET` | `/api/v1/discovery/health` | Public probe for discovery readiness, disk space, and LLM reachability |
| `GET` | `/api/v1/image-proxy` | Secure image proxy with host allowlist for external LinkedIn avatars |

---

## Deployment & Documentation

- ☁️ **[AWS Lightsail Deployment Guide](aws-deployment-guide.md)**: Production deployment on AWS Lightsail using Docker Compose (PostgreSQL, Backend, Caddy with automatic HTTPS) and Tailscale remote LLM connectivity.
- 🔍 **[Company Discovery Architecture & Setup](docs/discovery.md)**: Deep dive into the discovery pipeline, SearXNG Docker Compose setup, and Ollama configuration.
- 🏛️ **[Architecture Decision Records](docs/adr/)**:
  - [ADR 001: Company Discovery Architecture](docs/adr/001-company-discovery-architecture.md)
  - [ADR 002: Search Fallback Strategy & Resilience](docs/adr/002-search-fallback-strategy.md)
- 🚀 **[Free Cloud Deployment Guide](docs/deployment-guide.md)**: Zero-cost deployment on Render, Vercel, and Neon.
- 🎨 **[UI & Design System Guidelines](docs/ui-guidelines.md)**: Color tokens, typography, and instructions for registering custom block renderers.
