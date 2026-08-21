# Implementation Plan: Input Connectors View

**Branch**: `022-input-connectors-view` | **Date**: 2026-08-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/022-input-connectors-view/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add a new, read-only "Input Connectors" page to the existing React SPA that lists all 14
known data sources grouped into three static status groups — Live (1: Transcripts),
Simulated (6: Gmail, Zendesk, Warehouse, Slack, CSAT, Calendar), and Planned (7: Jira,
Intercom, Microsoft 365, Teams, NPS, Salesforce, Contracts) — matching
`base/mockupInputConectors.jpg` pixel-for-pixel in layout. The page is purely
presentational: a typed, local static data module (mirroring the existing
`nav/destinations.ts` single-source-of-truth pattern) feeds a grouped card list, with real
downloaded brand marks for connectors that have an official public icon and `lucide-react`
generic icons everywhere else. No backend endpoint, database change, or existing pipeline
is touched (spec FR-009).

## Technical Context

**Language/Version**: TypeScript 6 (frontend), matching the existing `frontend/` app — no backend change.

**Primary Dependencies**: React 18, react-router 7, Tailwind CSS + Radix/shadcn (`frontend/src/components/ui/`), `lucide-react` for all generic/UI icons, TanStack Query (not needed for data fetching here, since the page has no server data — kept only if a future iteration wires real connector health into this same page).

**Storage**: N/A — connector list and grouping are a local static TypeScript data module, not persisted anywhere; no schema, migration, or API endpoint is introduced.

**Testing**: Vitest + React Testing Library, consistent with existing page tests (e.g. `frontend/src/coverage/coverage-page.tsx`'s test sibling, `frontend/src/nav/*.test.tsx`).

**Target Platform**: Web — existing single-page app (`frontend/`), same browser support as the rest of the app.

**Project Type**: Web application (existing `backend/` + `frontend/` split); this feature is frontend-only.

**Performance Goals**: Page renders 14 static entries with no network round-trip; no measurable performance target beyond the app's existing SPA route-transition feel.

**Constraints**: Must not add a new icon or component library (constitution P11 / "UI & Styling" — `lucide-react` and Tailwind/Radix are closed choices); brand marks are sourced as static SVG assets, not as a new npm icon-library dependency, so this stays inside the existing rule rather than requesting an exception to it. Only four of the originally-planned eight brand marks (Gmail, Zendesk, Jira, Intercom) turned out to be safely sourceable this way — Slack, Microsoft 365, Teams, and Salesforce were found delisted from the source's actively-maintained CC0 index during implementation and render as brand-tinted `lucide-react` icons instead (research.md Decision 1 addendum). Must not alter any existing ingestion/scoring/backend behavior (spec FR-009).

**Scale/Scope**: One new page, one new static data module (14 connector entries across 3 groups), one new primary-navigation destination, ~8 downloaded brand SVG assets. No new backend surface.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **P8 (Clean Architecture) / P10 (YAGNI)** — PASS. This is a static, presentational
  frontend feature with no domain logic, no use case, and no adapter: there is nothing to
  layer. Introducing `domain/application/adapters` folders for a static list would itself
  violate P10 (speculative structure for behavior the feature doesn't have). Data lives as
  a plain typed module, exactly like the existing `nav/destinations.ts`.
- **P11 (Frontend: Feature-Oriented, Typed, Spec-Driven)** — PASS. New code is organized
  as its own feature directory (`frontend/src/input-connectors/`), strongly typed, no `any`,
  and reuses the existing design system (Tailwind/Radix, `lucide-react`) rather than adding
  a new one. Status is conveyed by label text as well as color (spec FR-008), satisfying
  the "never color-only" accessibility rule.
- **"UI & Styling" icon rule** — PASS with a documented approach (not a violation): brand
  logos are static SVG assets bundled into the app, not a second icon *library*/dependency.
  `lucide-react` remains the only icon *library* used, for every generic/UI icon (nav plug
  icon, chevrons, the "Add Connector" plus icon, and the handful of connectors with no
  official public mark). See `research.md` Decision 1.
- **P4 / P6 / P2 / P1** — N/A. This page has no send capability, doesn't compute or
  display a score, doesn't call an LLM, and cites no findings — none of these principles
  are engaged by a static connector catalog.
- **P9 (Test-First Determinism)** — N/A for this feature (no ledger/scoring code touched);
  standard frontend unit/component tests apply instead (P11's own testing bullet).

No violations requiring justification. **Complexity Tracking is not filled in.**

## Project Structure

### Documentation (this feature)

```text
specs/022-input-connectors-view/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

No `contracts/` directory: this feature adds no backend endpoint or other external
interface (spec FR-009, Assumptions). The typed shape of the connector data is instead
captured in `data-model.md`, the same way `nav/destinations.ts`'s `Destination` type is
today's single source of truth with no separate contract file.

### Source Code (repository root)

```text
backend/                          # UNCHANGED — no backend work in this feature

frontend/
├── public/
│   └── icons/
│       └── connectors/           # NEW — downloaded brand SVGs (gmail, slack, zendesk,
│                                  #   microsoft365, teams, salesforce, jira, intercom)
├── src/
│   ├── nav/
│   │   ├── destinations.ts       # MODIFIED — add the new "Input Connectors" destination
│   │   │                         #   (plug icon), same array Sidebar + Breadcrumb both read
│   │   └── app-shell.tsx         # UNCHANGED — new page wraps in the existing <AppShell>
│   └── input-connectors/         # NEW feature directory (P11 feature-oriented structure)
│       ├── input-connectors-page.tsx      # page component, route target
│       ├── input-connectors-page.test.tsx
│       ├── connectors-data.ts             # static typed data: 3 groups × 14 connectors
│       ├── connectors-data.test.ts        # asserts group counts match entry counts (edge case)
│       ├── connector-card.tsx             # one connector entry (icon, name, description, badge)
│       ├── connector-card.test.tsx
│       ├── status-badge.tsx               # Live/Simulated/Planned badge (label + color, FR-008)
│       ├── brand-icon.tsx                 # renders a downloaded SVG from public/icons/connectors/
│       └── types.ts                       # Connector, ConnectorGroup, ConnectorStatus types
└── App.tsx                       # MODIFIED — register the new protected route
```

**Structure Decision**: Web application, frontend-only change. The new page follows the
same feature-oriented, single-source-of-truth pattern already established for navigation
(`nav/destinations.ts` feeding both `Sidebar` and `Breadcrumb`, per feature
018-logout-nav-breadcrumb) and for pages (`AppShell`-wrapped, `frontend/src/<feature>/`
directory, per `coverage/coverage-page.tsx`). No backend directories are touched.
