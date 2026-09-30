# Task: Build the vSET Startup Screening Dashboard (backend + frontend)

You are a senior full-stack engineer. Build a professional B2B dashboard that presents startup screening reports. Data must live in a backend database and be served through an API. The frontend must not hard-code any report content.

## Working method (follow this order)

1. Read everything in `F:\dev\Vset` first: the two PDFs and the two JSON files (listed below). Do not write code yet.
2. Produce an **implementation plan** (architecture, folder tree, data model, API contract, phases) and **stop for my approval**.
3. After approval, build in the phases listed at the end. Finish and verify one phase before starting the next.
4. Ask me before making any decision that is not covered here and is hard to undo.

## Reference files (in `F:\dev\Vset`)

- `1505be66-terraspark_founder_screen.pdf` and `ab0612a1-terraspark_founder_screen.json` (company: TerraSpark)
- `6e014cf9-mysa_founder_screen.pdf` and `fc83eeef-mysa_founder_screen.json` (company: Mysa)

Each PDF is the visual/content spec for one company's dashboard. Each JSON is the same report as structured data. Only these two companies exist today, but the system will hold many companies in production, so **nothing may be specific to TerraSpark or Mysa**.

## What the dashboard is

- **Sidebar tabs = the report's section headings.** Content under each heading appears in that tab's page.
- Tabs, in order: Key facts & context, Founder & team, Product & technology, Validation & market signals, Market opportunity, Competitive landscape, Funding history, Investor questions & information to prepare, About this screen & sources.
- A company switcher in the top bar changes which company's report is shown.
- The PDF cover (company name, website, research cut-off, report date, report reference) becomes the report header. The status ribbon (Base country, Founded, Stage, Sector, Customer model) is shown as chips under the header.

## Data facts already verified in the JSON (use these paths)

Both files share one schema: `canonical.meta.canonical_version = "commercial-screen-canonical.2"`, `canonical.content.final.meta.schema_version = "vset.screen.v2"`.

| Purpose | JSON path |
|---|---|
| Company/report identity | `canonical.meta` (`canonical_screen_id`, `company_name`, `website`, `report_id`, `research_cutoff`, `generated_at`, `version`, `final_fingerprint`) |
| Cover fields | `canonical.content.cover` (`company_name`, `report_reference`, `research_cutoff`, `website`) |
| Report date | `canonical.content.final.meta.as_of_date` |
| Audience and labels | top-level `meta.audience` (e.g. `FOUNDER`) and `presentation` (`audience_label`, `action_section_title`, `section_action_heading`, `about_screen_audience_text`, `action_intro`, `action_part_a_title`, `action_part_b_title`) |
| Tabs 1 to 7 | `canonical.content.sections[]` with `key`, `title`, `ribbon` (list of `[label, value]`), `blocks` |
| "Information to prepare" under each section | `canonical.content.actions[]` where `kind = "SECTION_REQUEST"`; matched to a section by `where` (equals the section title) |
| Tab 8, Part A (questions) | `canonical.content.action_requirements.topics[]` (`topic`, `items[]` with `id`, `text`, `why`); same data as `actions[]` with `kind = "DD_QUESTION"` |
| Tab 8, Part B (documents) | `canonical.content.action_requirements.documents[]` (`group`, `priority[]`, `secondary[]`) |
| Tab 8, concerns and conflicts | `canonical.content.final.concerns_conflicts` (`concerns[]`, `conflicts[]`); empty in both files, show "No public concern or source conflict is recorded in this baseline." |
| Tab 9 sources | `canonical.content.final.evidence_register.sources[]` (`source_id`, `title`, `publisher`, `published_date`, `display_url`, `canonical_url`) |
| Tab 9 about text | `canonical.content.final.report_basis` (`scope_statement`, `limitations[]`, `research_window.from/to`) |

### Section blocks are typed arrays, not objects: `[type, title, ...payload]`

| type | payload | Render as |
|---|---|---|
| `para` | text | paragraph; certain titles are highlighted callouts in the PDF (Current position, Validation position, Next validation milestone, Competitive position, Financing position, Product & technology differentiation, Current product maturity, Market opportunity analyst view, Team-market fit). Put the callout-title list in one config file, not in components |
| `kv` | `[[key, value], ...]` | two-column key/value grid |
| `olist` | `[string, ...]` | numbered list |
| `list` | `[string, ...]` | bullet list (also used for "To obtain from management") |
| `table` | `header[]`, `rows[][]` | data table |
| `cards` | `[{name, role, lines:[[k,v]], fit}]` | founder cards with a "Founder-market fit" note |
| `comparison` | object | **two shapes**: (a) `header: []` and `items: [[criterion, description, position], ...]`; (b) Mysa-style matrix with `header[]`, `rows[][]`, `mode`, `note`, and empty `items`. The renderer must handle both and show `note` when present |

Known differences between the two companies that prove the renderer must be generic: Mysa has a "Key management members" table in Founder & team; TerraSpark has an "External validation & strategic engagement" table in Validation; TerraSpark's comparison uses shape (a) twice, Mysa's uses shape (b) once. Some cells are `-` or "Not established"; render these as a muted "Not available" state, never as blank or as an error.

New block types will appear later. Unknown block types must render a safe fallback (labelled generic view) and log a warning, not crash.

## Architecture requirements

Follow **SOLID** and **Clean Architecture**. Make the principles concrete:

- **Single responsibility:** one class or component does one job (parse, validate, persist, map, render).
- **Open/closed:** new block types and new report sections are added by registering a new renderer or mapper, without editing existing ones (use a block-renderer registry on the frontend, a mapper registry on the backend).
- **Liskov:** every block renderer follows the same props contract and is substitutable.
- **Interface segregation:** small, focused interfaces (for example `ReportReader` and `ReportWriter` are separate).
- **Dependency inversion:** domain and application code depend on interfaces (ports). Database, HTTP and framework code implement them (adapters). Inject dependencies; no `new` of infrastructure inside use cases.
- Dependencies point inward only: presentation and infrastructure depend on application; application depends on domain; domain depends on nothing.

### Suggested stack (change only if you give a reason in the plan)

- Backend: Node.js + TypeScript + NestJS, PostgreSQL (JSONB), Prisma, Zod for validation, Jest, Docker Compose for the database.
- Frontend: React + TypeScript + Vite, React Router, TanStack Query, Tailwind CSS, Vitest + Testing Library.

### Backend folder structure

```
backend/
  src/
    domain/                     # entities and value objects; no framework imports
      company/  report/  section/  block/  source/  action-item/
    application/                # use cases and ports (interfaces)
      use-cases/                # ListCompanies, GetReportHeader, GetSection, GetActions, GetSources, ImportReport
      ports/                    # ReportRepository, CompanyRepository, ReportImporter, Clock
      mappers/                  # raw JSON -> domain (one mapper per concern)
    infrastructure/
      persistence/prisma/       # repository implementations, schema, migrations
      ingestion/                # JSON schema validation, version gate, import script
    presentation/
      http/                     # controllers, DTOs, response mappers, error filter
    config/  main.ts
  prisma/  test/  seed/         # seed script imports the two reference JSON files
```

### Frontend folder structure

```
frontend/
  src/
    app/                        # providers, router, layout shell
    core/                       # http client, env, error types, query client
    shared/
      ui/                       # design-system primitives: Button, Chip, Card, Callout, DataTable, KeyValueGrid, Skeleton, EmptyState, ErrorState
      lib/  styles/  tokens
    features/
      companies/                # switcher, company list
      report/
        domain/                 # TS types mirroring API responses
        data/                   # api functions, query hooks
        ui/
          shell/                # Sidebar, TopBar, ReportHeader
          blocks/               # one component per block type + registry.ts
          sections/             # SectionPage (data-driven, no per-section hard-coding)
          actions/              # InformationToPrepare, QuestionsAndDocuments
          sources/
    routes/
  tests/
```

## Backend requirements

- Import endpoint and a CLI/seed script that ingest a raw report JSON. Validate it with a schema; reject unsupported `canonical_version` or `schema_version` with a clear error.
- Import is **idempotent**: keyed on `canonical_screen_id` with `final_fingerprint` for change detection. Re-importing the same file changes nothing.
- Keep the **raw JSON snapshot** stored untouched (audit trail) in addition to the structured tables.
- Data model: `Company` 1-to-many `Report` (report has `audience`, `version`, `generated_at`, `research_cutoff`, fingerprint, `presentation` labels), `Report` 1-to-many `Section` (`key`, `title`, `position`, `ribbon` JSONB, `blocks` JSONB), plus `Source`, and `ActionItem` (`kind`, `where`, `text`, `why`, `group`, priority/secondary). Section order comes from the data, never from code.
- API (versioned, read-only for the UI):
  - `GET /api/v1/companies`
  - `GET /api/v1/companies/:slug` (header: cover fields, ribbon, audience label)
  - `GET /api/v1/companies/:slug/sections` (navigation: key, title, position)
  - `GET /api/v1/companies/:slug/sections/:key` (ribbon, blocks, section-level "information to prepare")
  - `GET /api/v1/companies/:slug/actions` (Part A questions grouped by topic, Part B documents grouped by group)
  - `GET /api/v1/companies/:slug/sources`
  - `POST /api/v1/reports/import` (admin; guard it behind a config flag or API key)
- Consistent error format, request validation, structured logging, CORS configured from env, OpenAPI docs.
- Authentication is out of scope now, but leave a clean seam (a guard interface) so it can be added.

## Frontend / UI requirements

- **Style:** B2B, professional, clean. Light theme, neutral slate greys, one restrained navy accent (matches the navy in the PDFs), generous whitespace, thin dividers, no decorative gradients or emoji. Typeface: Inter or system UI. Numbers and dates use tabular figures.
- **Layout:** fixed left sidebar (about 260px, collapsible) with the tab list; top bar with the vSET wordmark, company switcher and report meta; content area with a max reading width. Active tab clearly indicated. Tabs are **deep-linkable** routes: `/companies/:slug/:sectionKey`, and the browser back button works.
- **Components:** define design tokens (colours, spacing, type scale, radius) once; build the shared primitives first; every block renderer uses them.
- **States:** skeleton loading, empty ("nothing recorded"), and error-with-retry states for every data-driven view.
- **Accessibility:** WCAG AA contrast, full keyboard navigation, `aria-current` on the active tab, semantic tables and headings.
- **Responsive:** works from tablet width up; the sidebar becomes a drawer on narrow screens.
- **Fidelity:** each tab must contain everything the matching PDF pages contain. Compare against the PDFs when done.

## Quality bar

- TypeScript strict mode; no `any` in domain or application code.
- Unit tests for mappers, importer (including idempotency) and every block renderer; an integration test that imports **both** reference JSON files and asserts the API returns all nine tabs for each.
- A contract test proving that adding a third fake company JSON (a small variant) needs **no code change**.
- ESLint + Prettier configured; a `README.md` with setup, run, seed and test commands.

## Phases

1. **Plan** (stop for approval).
2. **Backend foundation:** project setup, database schema, migrations, domain entities, importer and seed for both files.
3. **API:** use cases, controllers, DTOs, OpenAPI, tests.
4. **Frontend foundation:** app shell, tokens, shared UI primitives, routing, company switcher.
5. **Report views:** block-renderer registry and all block types, section pages, actions tab, sources tab.
6. **Polish and verification:** states, accessibility pass, responsive pass, side-by-side check against both PDFs, README.

At the end of each phase, list what you built, what you verified and how, and anything you were unsure about.

## Out of scope for now

Authentication and user roles, editing report content in the UI, PDF export, and the `evidence_register.claims` (122 in TerraSpark, 168 in Mysa) with evidence-state badges. Design the data model so the last two can be added later.
