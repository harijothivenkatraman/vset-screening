# vSET Startup Screening Dashboard

A professional B2B dashboard presenting startup screening reports, built with Clean Architecture. All data lives in a database and is served via a versioned REST API. The frontend is entirely data-driven with no hard-coded company or report content.

---

## Architecture & Tech Stack

### Backend
- **Framework:** FastAPI (Python 3.12+)
- **Architecture:** Clean Architecture with 4 distinct layers:
  - **Domain:** Pure Python dataclasses (`Company`, `Report`, `Section`, `ActionItem`, `Source`), zero framework dependencies.
  - **Application:** Use cases (`ListCompanies`, `GetReportHeader`, `GetSectionNav`, `GetSection`, `GetActions`, `GetSources`, `ImportReport`), repository port interfaces (ABCs), and mappers.
  - **Infrastructure:** SQLAlchemy 2.0 (async), Alembic migrations, PostgreSQL / SQLite (`aiosqlite`) engines, version gate, and Pydantic schema validation.
  - **Presentation:** FastAPI routers, Pydantic v2 response schemas, API key security guard, and error handlers.
- **Data Store:** SQLite (default for development/tests) and PostgreSQL (via Docker Compose). Stores structured tables plus untouched raw JSON snapshots for audit trails.
- **Idempotency:** Ingestion keyed on `canonical_screen_id` with `final_fingerprint` change detection.

### Frontend
- **Framework:** React 19 + TypeScript (strict mode) + Vite
- **Styling:** Tailwind CSS + CSS custom properties (tokens) in `tokens.css` (B2B palette with restrained `#1e2a3a` navy accent and neutral slate greys).
- **Routing:** React Router with deep-linkable URLs (`/companies/:slug/:sectionKey`, `/companies/:slug/actions`, `/companies/:slug/sources`).
- **Data Fetching:** TanStack React Query with caching, loading skeletons, and error-with-retry states.
- **Block Renderer Registry:** Extensible component registry implementing the Open/Closed Principle. Supports typed array blocks (`para`, `kv`, `olist`, `list`, `table`, `cards`, `comparison`, and unknown fallbacks). Handles both items-based and matrix comparison shapes.

---

## Directory Structure

```
├── backend/
│   ├── alembic/                 # Database migrations
│   ├── app/
│   │   ├── application/         # Ports (ABCs), use case services, mappers
│   │   ├── domain/              # Entities, block types, value objects
│   │   ├── infrastructure/      # Repositories, DB models, JSON ingestion
│   │   ├── presentation/        # FastAPI routers, schemas, dependencies, guards
│   │   ├── config.py            # Environment settings
│   │   └── main.py              # Application entry point, CORS, routers
│   ├── tests/
│   │   ├── conftest.py          # Async test client & in-memory DB fixtures
│   │   ├── unit/                # Mappers, version gate, schema validation tests
│   │   └── integration/         # Idempotency, 9-tab API, contract tests
│   ├── docker-compose.yml       # PostgreSQL service definition
│   ├── pyproject.toml           # Project dependencies & tool configs
│   ├── requirements.txt
│   └── seed.py                  # Seed script importing reference reports
│
├── frontend/
│   ├── src/
│   │   ├── app/                 # Shell layout, router, query provider
│   │   ├── core/                # HTTP client & TanStack Query client
│   │   ├── features/
│   │   │   ├── companies/       # CompanySwitcher, hooks, API
│   │   │   └── report/          # Shell, blocks registry, section/action/source pages
│   │   ├── shared/
│   │   │   ├── styles/          # Tokens and global styles
│   │   │   └── ui/              # Button, Card, Callout, Chip, DataTable, FounderCard, etc.
│   │   └── config/              # Callout titles configuration
│   ├── tests/                   # Vitest unit tests for all block renderers
│   ├── package.json
│   └── vite.config.ts
│
└── reference/
    ├── terraspark_founder_screen.json
    ├── terraspark_founder_screen.pdf
    ├── mysa_founder_screen.json
    └── mysa_founder_screen.pdf
```

---

## Quick Start Guide

### 1. Prerequisites
- Python 3.12+ (Python 3.13 recommended)
- Node.js 18+ and npm
- Docker (optional, for PostgreSQL)

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

Interactive OpenAPI Swagger documentation is available at:
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

Visit **`http://localhost:5173`** to access the dashboard.

---

## Running Automated Tests

### Backend Test Suite (Pytest)
Executes 17 comprehensive tests including unit tests for mappers and validators, integration tests asserting all 9 tabs for both companies, idempotency verification, and contract testing for third-party company variants with zero code changes:

```powershell
cd backend
.\.venv\Scripts\pytest -v
```

### Frontend Test Suite (Vitest)
Executes unit tests verifying every block renderer (`para`, `kv`, `olist`, `list`, `table`, `cards`, `comparison` shapes a & b, `unknown` fallback, and `MutedValue`):

```powershell
cd frontend
npm test
```

### Production Build
```powershell
cd frontend
npm run build
```

---

## Deployment & Documentation

- 🚀 **[Free-of-Cost Step-by-Step Deployment Guide](docs/deployment-guide.md)**: Full instructions to deploy the FastAPI backend on **Render** (free tier), frontend on **Vercel** (free edge tier), and database on **Neon.tech / SQLite** with **zero cost** and no credit card required.
- 🎨 **[UI & Design System Guidelines](docs/ui-guidelines.md)**: Comprehensive reference for color tokens, typography scales, WCAG AA compliance, and instructions on how to register new presentation block renderers.

---

## API Endpoints Reference

All endpoints are versioned under `/api/v1`:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/companies` | List all available companies with stage/sector summary |
| `GET` | `/api/v1/companies/{slug}` | Cover metadata, ribbon chips, audience label, report date |
| `GET` | `/api/v1/companies/{slug}/sections` | Section navigation list for sidebar tabs (Tabs 1–7) |
| `GET` | `/api/v1/companies/{slug}/sections/{key}` | Section content blocks + section-level "Information to prepare" |
| `GET` | `/api/v1/companies/{slug}/actions` | Tab 8: Investor questions (Part A) & documents (Part B) |
| `GET` | `/api/v1/companies/{slug}/sources` | Tab 9: Methodology, limitations, and evidence register sources |
| `POST` | `/api/v1/reports/import` | Ingest raw report JSON (guarded by `X-API-Key` header) |
