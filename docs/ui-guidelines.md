# vSET UI & Design System Guidelines

This document outlines the visual design system, token definitions, typography rules, accessibility standards, and component architecture for the vSET Startup Screening Dashboard.

---

## 1. Design Tokens & Visual Language

The dashboard uses a clean, professional B2B visual direction with a light theme, confident navy primary brand tones, neutral slates, and semantic accents compliant with **WCAG AA contrast ratios (≥ 4.5:1)**.

### Color Tokens

| Token | CSS Variable | Hex / Tailwind | Contrast Ratio | Usage |
|---|---|---|---|---|
| **Navy Primary** | `--color-navy-primary` | `#1e2a3a` | 13.8:1 | Page titles, primary badges, navigation accents |
| **Navy Muted** | `--color-navy-muted` | `#2c3e56` | 9.4:1 | Secondary headers, hover states |
| **Text Primary** | `--color-text-primary` | `#0f172a` (slate-900) | 16.1:1 | Body headings, hero numbers, primary text |
| **Text Secondary** | `--color-text-secondary`| `#334155` (slate-700) | 9.6:1 | Narrative paragraphs, table text |
| **Text Muted** | `--color-text-muted` | `#64748b` (slate-500) | **4.6:1 (AA)** | Micro kickers, field labels, metadata timestamps |
| **Links / Accent** | `--color-link` | `#0369a1` (sky-700) | **4.7:1 (AA)** | Interactive URLs, external links, active focal indicators |
| **Emerald Confirmed** | `--color-emerald-text` | `#047857` (emerald-700) | **4.9:1 (AA)** | Confirmed positive signals, verification states |
| **Amber Warning** | `--color-amber-text` | `#92400e` (amber-800) | **5.1:1 (AA)** | Items requiring diligence, gaps to clarify |
| **Canvas Background** | `--color-bg-canvas` | `#f8fafc` (slate-50) | — | Main application background |
| **Card Surface** | `--color-surface` | `#ffffff` | — | Cards, containers, fact panels |
| **Border Neutral** | `--color-border-subtle`| `#e2e8f0` (slate-200) | — | Structural dividers, card borders |
| **Decorative Border** | `--color-border-decor` | `#94a3b8` (slate-400) | — | *Decorative borders & lines only (never for text)* |

### Typography Scale

- **Display Title (H1)**: 28px–32px, `font-bold`, tracking tight (`#0f172a`)
- **Section Title (H2)**: 20px–24px, `font-bold`, tracking tight (`#1e2a3a`)
- **Block Header (H3)**: 14px–16px, `font-semibold` (`#0f172a`)
- **Micro Kicker / Field Label**: **Minimum 11px** (never smaller), `font-bold`, uppercase, tracking wider (`#64748b`)
- **Reading Body (Narrative)**: 15px, `line-height: 1.6`, constrained line-length (`max-w-3xl`, 65–75 characters)
- **Tabular Figures**: `tabular-nums` applied to dates, financial amounts, metrics, and source IDs

### Spacing & Layout

- **4/8px Spacing Grid**: `space-y-2` (8px), `space-y-4` (16px), `space-y-6` (24px), `space-y-8` (32px)
- **Breakpoints**:
  - `390px` (Mobile): Single-column stacked fact bar, sticky top navigation with drawer toggle
  - `1024px` (Tablet): Two-column grids for fact panels and cards
  - `1440px+` (Desktop & Wide): Multi-column layouts, 3-wide founder/funding cards, and sticky right-rail "On this page" mini table of contents

---

## 2. Core UX & Presentation Principles

1. **Gestalt Grouping & Whitespace**:
   - Related facts are grouped into cards (`FactGrid`, `FounderCard`, `FundingCards`) with subtle background tones and 1px borders, avoiding heavy black borders.
2. **Scannability (F-Pattern)**:
   - Field labels sit directly above their values (left-aligned) rather than pushed to opposite ends.
   - Important metric amounts and round names are prominent hero text.
3. **Chunking & Progressive Disclosure**:
   - Diligence questions in Tab 8 are chunked by topic into collapsible accordions with item counts and an "Expand all / Collapse all" master toggle.
   - Long tables provide horizontal scroll containers with sticky headers and sticky left columns.
4. **Zero Data Invention**:
   - Dates are formatted via `formatDisplayDate()` strictly for `YYYY-MM-DD` strings into UTC `en-GB` (`"28 September 2026"`), passing descriptive phrases (`"March 2026"`, `"Undated"`) through unchanged.
   - Empty, undisclosed, or unverified values render via `<MutedValue />` showing muted text and a clarifying tooltip: `"Not established from public sources"`.
   - Investor names in funding rounds are split strictly on commas (never dropping text).
   - Funding totals in summary banners preserve verbatim source sentences without synthetic math.

---

## 3. Component Architecture & Block Registry

The frontend implements Clean Architecture with a strict separation between presentation blocks and domain data.

### Block Registry (`src/features/report/ui/blocks/registry.ts`)

Every block in the report response is parsed as a tuple `[type, title, payload, ...]`:

| Block Type | Presentation Component | Responsive Presentation |
|---|---|---|
| `para` | `ParaBlock.tsx` | Standard reading paragraph (`max-w-3xl`) or `Callout` for designated position titles |
| `kv` | `KvBlock.tsx` | `FactGrid` (2–3 column grid, label above value) |
| `olist` | `OlistBlock.tsx` | Numbered pills for short lists; `NumberedList` with bold prefixes for long lists |
| `list` | `ListBlock.tsx` | Chip pills for short lists (e.g. target markets); `BulletList` for diligence items |
| `table` | `TableBlock.tsx` | Automatically routes to `FundingCards` (for round history), `Timeline` (for Date/Event), or `DataTable` |
| `cards` | `CardsBlock.tsx` | `FounderCard` (2–3 column responsive cards with initials avatar and fit panel) |
| `comparison`| `ComparisonBlock.tsx`| Shape (a): 2-column criterion + position; Shape (b): sticky matrix table with highlighted subject column |
| `*` (unknown) | `UnknownBlock.tsx` | Non-crashing graceful fallback banner logging a diagnostic warning |

### Registering a New Block Renderer

To introduce a new block type into the vSET dashboard:

1. **Create the Component**:
   Create `src/features/report/ui/blocks/MyNewBlock.tsx`:
   ```tsx
   import React from "react";
   interface MyNewBlockProps {
     block: [string, string, ...unknown[]];
   }
   export const MyNewBlock: React.FC<MyNewBlockProps> = ({ block }) => {
     const [, title, payload] = block;
     return (
       <div className="my-5 space-y-2">
         {title && <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">{title}</h3>}
         {/* Render payload using shared/ui primitives */}
       </div>
     );
   };
   ```

2. **Register in Registry**:
   Add to `src/features/report/ui/blocks/registry.ts`:
   ```ts
   import { MyNewBlock } from "./MyNewBlock";
   // In BLOCK_REGISTRY map:
   my_new_type: MyNewBlock,
   ```

3. **Add Tests**:
   Add a unit test in `frontend/tests/blocks.test.tsx` verifying proper rendering and data binding.

---

## 4. Shared UI Primitives (`src/shared/ui/`)

- `Avatar`: Generates initials badge with consistent background styling.
- `Badge`: WCAG AA badge variants (`navy`, `blue`, `outline`, `success`, `warning`).
- `Button`: Accessible interactive buttons with distinct hover and focus rings.
- `Callout`: Styled callouts with neutral icons (`Compass` for position, `Lightbulb` for analyst view).
- `Collapsible`: Accessible disclosure component with item count badges and animated chevrons.
- `DataTable`: Clean data table with sticky headers, sticky first columns, and right-aligned numbers.
- `FactBar`: Compact ribbon bar for top-level company facts (label above value).
- `FactGrid`: Responsive 2–3 column grid replacing wide key-value gaps.
- `FounderCard`: Complete founder profile card with role badges, education/experience lines, and fit panel.
- `FundingCards`: Financing event cards with hero amounts, date badges, and comma-split investor chips.
- `Timeline`: Vertical chronologic timeline preserving strict source order.
- `MutedValue`: Accessible placeholder for unavailable or undisclosed data with clarifying tooltip.
