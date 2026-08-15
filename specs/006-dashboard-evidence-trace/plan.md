# Implementation Plan: Dashboard Evidence Trace

**Branch**: `006-dashboard-evidence-trace` | **Date**: 2026-08-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/006-dashboard-evidence-trace/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Fill in the rest of `architecture/07-api-spec.md`'s `DashboardResponse` schema —
score block, contribution bars, pulse timeline, stakeholder cards, coverage
line — that feature 002 deliberately left absent, and build the evidence trace
panel (`GET /api/evidence/{score_contribution_id}`) and system health screen
(`GET /api/coverage`). Technical approach: extend the already-scaffolded
`backend/app/experience/{application,adapters}/` module (feature 002) with a new
`domain/` ring for the evidence panel's per-finding-type comparison/arithmetic
formatting (the one piece of real logic this feature adds — everything else is
direct reads), reader-owned ports mirroring feature 004/005's established
cross-module convention (read `score_runs`/`score_contributions`/`findings`/
`events`/`coverage_reports`/`stakeholders` via `app.experience`'s own ports, never
by importing `app.scoring`/`app.readers`/`app.ingestion`'s adapters directly).
Frontend: extend `frontend/src/dashboard/` with the real component set and add a
new `frontend/src/evidence/` feature folder for the trace panel, both consuming
the extended `/api/dashboard` and new `/api/evidence/{id}`/`/api/coverage`
contracts via TanStack Query, matching feature 002's established pattern.

## Technical Context

**Language/Version**: Python 3.12 (backend); TypeScript 5.x (frontend) —
unchanged from features 001–005

**Primary Dependencies (new in this feature)**: None — no new package. Score/
finding/event/coverage reads use the same `sqlalchemy`/`asyncpg` stack every
prior feature already uses; the frontend evidence panel reuses the already-
adopted `@tanstack/react-query` (server state) and Tailwind/Radix design system
(`architecture/03-technology-stack.md`, constitution P11) — no new chart library,
since REQ-M8-09/FR-011 forbid the chart types a library would exist to draw
(the score trend/sparkline is a small inline SVG, matching "SVG-based charts
only," constitution's Technology and Data Standards).

**Storage**: PostgreSQL 16 — no schema change, no migration. Every field this
feature renders already exists: `score_runs`/`score_contributions`
(`data-base/06-schema-scoring.md`, feature 004), `findings`
(`data-base/05-schema-reasoning.md`, feature 005), `events`/`coverage_reports`/
`raw_envelopes`/`identity_map` (`data-base/02`/`03`, feature 003),
`stakeholders`/`client_profile_versions` (`data-base/04`, feature 003). This is
the first feature to read `score_contributions`/`coverage_reports`/
`identity_map` for a user-facing purpose rather than an internal computation.

**Testing**: pytest (backend) — one test module per new route
(`test_dashboard_route.py` extended, `test_evidence_route.py`,
`test_coverage_route.py`) against the real, already-ingested/scored Meridian
fixture (features 003–005's own worked data), plus pure unit tests for the
evidence panel's per-finding-type arithmetic-in-words formatting (no DB, plain
values, mirroring feature 004/005's domain-service testing pattern); Vitest +
React Testing Library (frontend) — dashboard component rendering per state,
evidence panel rendering; Playwright — one new end-to-end spec extending
feature 002's `login-to-dashboard.spec.ts` to click through a real contribution
bar into the evidence panel.

**Target Platform**: Same Docker Compose stack as features 001–005 — no new
service, no `docker-compose.yml` change.

**Project Type**: Web application (backend + frontend), same monorepo as
feature 002.

**Performance Goals**: `GET /api/dashboard` and `GET /api/evidence/{id}` both
under 1s against a warm database (REQ-NFR-01, SC-001) — every query in this
feature is a bounded read (a 14-day window, a single score run's contributions,
a small stakeholder list), no full-table scan.

**Constraints**: REQ-M8-P1 (no scoring/ranking/aggregation client- or server-side
beyond direct reads and formatting); REQ-M8-P2/REQ-M8-09/FR-011 (no manufactured-
concern UI, no forbidden chart types); FR-014 (no Ask bar, no feedback controls —
out of scope, see spec.md's Note on scope); `tone_trajectory` always `unknown`
(feature 007 not built yet); quarantine list always empty (feature 007's
`ValidationGate` not built yet).

**Scale/Scope**: Single client deployment (constitution's Isolation model) — the
14-day pulse-timeline/trend window and single-profile stakeholder list are both
small, bounded reads regardless of how large the ledger grows over a
deployment's lifetime.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies to this feature? | Status |
|---|---|---|
| **P1 Evidence or It Does Not Exist** | Yes — the evidence trace panel is this principle made visible: every rendered number traces to real `cited_event_ids` | **Pass** — FR-008, SC-003 |
| P2 The Model Interprets, Code Calculates | Yes — no LLM call anywhere in this feature; the "arithmetic in words" is deterministic template formatting over `score_contributions`' already-computed columns, never a generated sentence (`research.md`'s Decision) | **Pass** — matches the explicit Narrator exclusion in spec.md's Note on scope |
| **P3 Each Component Refuses to Do the Next One's Job** | Yes — this feature performs zero scoring/ranking/aggregation (REQ-M8-P1); it only reads and formats what `app.scoring`/`app.readers`/`app.ingestion` already computed | **Pass** — FR-001 |
| P4 A Human Always Sends | No send capability touched | N/A |
| **P5 Admit What We Cannot See** | Yes — Source down/Catching up/Unresolved person states, `tone_trajectory: unknown`, and an honestly-empty quarantine list all make incomplete/unavailable data visibly different from complete data | **Pass** — FR-006, FR-009, FR-010 |
| **P6 Silence Is a Success State** | Yes — the `healthy_quiet` state (`research.md`) renders the near-empty "Nothing needs you today" screen instead of the normal component set | **Pass** — FR-004 |
| P7 Context Over Sentiment | No sentiment computation in this feature (Tone is feature 007) | N/A |
| **P8 Clean Architecture: the Dependency Rule Is Law** | Yes — `app.experience/{domain,application,adapters}` follows the three-ring shape; new reader-owned ports read the same tables `app.scoring`/`app.readers`/`app.ingestion` already own, never a cross-module adapter import (feature 004/005's established convention) | **Pass** — `.importlinter`'s `global-dependency-rule` contract already lists `app.experience`; no config change needed |
| P9 Test-First Determinism | Not applicable — no ledger/scoring code touched, pure read layer | N/A |
| **P10 Simplicity Over Speculative Generality (YAGNI)** | Yes — no chart library for a sparkline that's a handful of SVG points; the evidence panel's per-finding-type formatting is a small, closed dispatch table (five finding types, `research.md`), not a generic templating engine | **Pass** |
| **P11 Frontend: Feature-Oriented, Typed, Spec-Driven** | Yes — `frontend/src/dashboard/` extended, new `frontend/src/evidence/` feature folder; TanStack Query for both, matching feature 002's established pattern | **Pass** |
| Full-Stack §4 Testing Strategy | Yes — new route-level tests, domain-level formatting tests, one new E2E spec | **Pass** — see Testing above |
| Full-Stack §5 Security & Quality Gates | Yes — every route requires the existing bearer-token dependency (`get_current_user`), no new auth surface | **Pass** — reuses feature 002's `get_current_user` dependency unchanged |

**No violations requiring justification.** Complexity Tracking table below is empty.

## Project Structure

### Documentation (this feature)

```text
specs/006-dashboard-evidence-trace/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output — state derivation, evidence dispatch table
├── quickstart.md         # Phase 1 output — dashboard + evidence validation guide
└── contracts/
    ├── dashboard.md        # GET /api/dashboard, full DashboardResponse
    ├── evidence.md         # GET /api/evidence/{score_contribution_id}
    └── coverage.md         # GET /api/coverage
```

No `tasks.md` yet — Phase 2 output, produced by `/speckit-tasks`, not this command.

### Source Code (repository root)

Extends the monorepo layout features 001–005 scaffolded — only files this
feature adds or changes are shown:

```text
backend/
├── app/
│   ├── experience/
│   │   ├── domain/
│   │   │   ├── entities.py           # PulseSeverity, DashboardStateKind, evidence
│   │   │   │                          #   comparison value objects — pure, no I/O
│   │   │   └── services.py           # State precedence resolver; per-finding-type
│   │   │                              #   evidence formatter (arithmetic-in-words,
│   │   │                              #   baseline/current comparison) — pure functions
│   │   ├── application/
│   │   │   ├── ports.py              # extended: ScoreReadPort, FindingReadPort,
│   │   │   │                          #   PulseEventPort, StakeholderReadPort,
│   │   │   │                          #   CoveragePort, IdentityGapPort — reader-
│   │   │   │                          #   owned, no cross-module adapter import
│   │   │   └── use_cases.py          # extended: GetDashboardUseCase (supersedes
│   │   │                              #   GetDashboardShellUseCase),
│   │   │                              #   GetEvidenceTraceUseCase,
│   │   │                              #   GetCoverageUseCase
│   │   └── adapters/
│   │       ├── sqlalchemy_repository.py  # extended: implements the new ports
│   │       ├── dashboard_router.py       # extended: full DashboardResponse
│   │       ├── evidence_router.py        # GET /api/evidence/{id}
│   │       └── coverage_router.py        # GET /api/coverage
│   └── main.py                        # wires the two new routers (updated)
└── tests/
    ├── unit/
    │   ├── test_dashboard_route.py    # extended: full response, all six states
    │   ├── test_evidence_route.py     # per-finding-type evidence, 404 case
    │   └── test_coverage_route.py     # source status, empty quarantine
    └── experience/
        └── test_state_and_evidence_services.py  # pure domain-service tests,
                                                    #   no DB — state precedence,
                                                    #   evidence formatting per
                                                    #   finding type

frontend/
└── src/
    ├── dashboard/
    │   ├── dashboard-page.tsx         # extended: full component set, state banners
    │   ├── score-block.tsx            # score number, band pill, inline SVG trend
    │   ├── contribution-bars.tsx
    │   ├── pulse-timeline.tsx         # serif client quotes (REQ-M8-04)
    │   ├── stakeholder-cards.tsx
    │   ├── coverage-line.tsx
    │   └── dashboard-page.test.tsx    # extended: one test per state
    ├── evidence/
    │   ├── evidence-panel.tsx         # opens from any clickable number
    │   ├── use-evidence.ts            # TanStack Query hook for GET /api/evidence/{id}
    │   └── evidence-panel.test.tsx
    ├── coverage/
    │   └── coverage-page.tsx          # the dedicated system health screen
    └── App.tsx                        # updated: /coverage route added

frontend/
└── e2e/
    └── dashboard-to-evidence.spec.ts  # click a contribution bar → evidence
                                         #   panel shows real cited-message text
                                         #   (corrected during implementation:
                                         #   feature 002's playwright.config.ts
                                         #   already sets testDir to frontend/e2e/,
                                         #   not frontend/src/e2e/ as first planned)
```

**Structure Decision**: Same web-application structure as features 001–002,
extending `app.experience` (backend) and `dashboard/` (frontend) — the module
folders those features already scaffolded — with real code for the first time;
`app.experience/domain/` is new (feature 002 needed no domain ring, being a pure
passthrough; this feature's evidence formatting is the first real domain logic
this module owns). Two new frontend feature folders (`evidence/`, `coverage/`),
consistent with constitution P11's feature-oriented structure. No new top-level
directories, no new Docker service.

## Complexity Tracking

*No entries — Constitution Check reported no violations requiring justification.*
