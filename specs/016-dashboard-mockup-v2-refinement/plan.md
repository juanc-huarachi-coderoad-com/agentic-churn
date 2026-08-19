# Implementation Plan: Dashboard Mockup V2 Refinement

**Branch**: `016-dashboard-mockup-v2-refinement` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/016-dashboard-mockup-v2-refinement/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Restructure `dashboard-page.tsx`'s two-column grid (Signal Stream | Churn Risk Overview +
Action & Draft Hub, with the Assistant as a floating overlay) into the mockup's three
columns: a new first column (company title + a band-colored gradient "AURA" risk orb +
the Assistant, now a permanently docked, always-expanded panel instead of a floating
launcher), the existing Signal Stream as column two (dual-channel entry icons — shape by
real signal type, color by severity — plus a connecting timeline line, with
`NarratorPanel`/`StakeholderCards`/`CoverageLine` kept, unmoved in function, appended
below it), and the existing Churn Risk Overview + Action & Draft Hub as column three
(larger band-colored score, explicitly axis-labeled trend chart). Each column scrolls
independently within the viewport; the page itself does not scroll.

Technical approach: this is the first dashboard-redesign feature since 012 that also
touches `backend/` — the mockup's per-entry signal type (Activity/Email/Chat/…) requires
surfacing the `events.event_type` enum column, which is already stored but never selected
by `SqlAlchemyPulseEventReader.list_recent` or exposed on `PulseEvent`. That one column is
threaded through unchanged, layer by layer (query → `PulseEventRecord` →
`PulseEventResult` → the `PulseEvent` Pydantic schema), as a raw enum string — the
frontend, not the backend, maps it to a display label/icon, mirroring how `severity`
already works today (P3, P7). `EvidencePanel` and `DraftComposerPanel` move from a
hand-rolled right-docked overlay `<div>` to a new, minimal `components/ui/dialog.tsx`
built on `@radix-ui/react-dialog` (centered, focus-trapped, Esc-to-close) — the first
feature whose spec requires real dialog semantics, matching 012's "build only the
Radix/shadcn primitive a feature actually needs, when it needs it" precedent. No database
migration, no new endpoint, no change to score computation, banding, ranking, or draft
generation.

## Technical Context

**Language/Version**: TypeScript ~6.0 / React 18.3 (frontend, unchanged); Python 3.12 /
FastAPI (backend, unchanged) — this feature edits existing backend files but adds no new
backend dependency or service.

**Primary Dependencies**: Existing — Vite, Tailwind CSS v4, TanStack Query, Zustand, React
Hook Form + Zod, `@radix-ui/react-slot`, `class-variance-authority`, `clsx` +
`tailwind-merge`, `recharts`, `lucide-react`. New — `@radix-ui/react-dialog` (the Dialog
primitive from the design system the constitution already names — P11 — activated now
because this is the first feature whose spec (FR-013) requires a true centered, dismissible
modal rather than a docked side panel).

**Storage**: PostgreSQL 16, unchanged schema — `events.event_type` (`data-base/
10-ddl-appendix.md` lines 124-127) already exists; this feature only adds it to an existing
`SELECT`, no migration.

**Testing**: Vitest + `@testing-library/react` + `@testing-library/user-event` (frontend,
matching `score-block.test.tsx`/`dashboard-page.test.tsx`); `@playwright/test` for the
column-scroll/modal/docked-assistant end-to-end checks in `quickstart.md`; pytest +
`httpx.AsyncClient` against a real Postgres via `app.db.engine` (backend, matching
`backend/tests/unit/test_dashboard_route.py`'s existing fixture pattern).

**Target Platform**: Web SPA (existing), desktop/laptop viewport primary, per spec
Assumptions.

**Project Type**: Web application (frontend + backend) — unlike 012/015, this feature
touches `backend/`: `dashboard_router.py`, `use_cases.py`, `ports.py`,
`sqlalchemy_repository.py`, each gaining one additive field on an existing type. No new
route, no new module.

**Performance Goals**: No new target. The pulse-event query's join/filter shape is
unchanged; one extra selected column is negligible. Client-side icon mapping is a constant
lookup, not a computation.

**Constraints**: Must not change score computation, band classification, risk-driver
ranking, action prioritization, or draft content (spec FR-015) — the only backend-visible
change is the additive `event_type` passthrough (FR-006). Icons MUST use `lucide-react`;
charts MUST use Recharts (unchanged, P11). The new Dialog must reach at least today's
accessibility parity — keyboard reachability, screen-reader labeling, and now an explicit
focus-trap/Esc-to-close it didn't reliably have before (FR-016).

**Scale/Scope**: One page (`dashboard-page.tsx`) restructured from two columns to three;
one new component (`aura-risk-orb.tsx`) and one converted component (`ask-bar.tsx`,
launcher removed); one new shared primitive (`components/ui/dialog.tsx`) consumed by two
existing overlays (`EvidencePanel`, `DraftComposerPanel`); one existing component extended
with a second icon-selection axis (`pulse-timeline.tsx` + new `signal-type.ts`); one chart
gains explicit axes (`score-block.tsx`). Backend: four existing files each gain one field
on an existing type — no new table, no new endpoint, no new route.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **P1 — Evidence or It Does Not Exist**: PASS. Every Signal Stream entry and Action &
  Draft Hub item still opens through its real `score_contribution_id` into (now-modal)
  `EvidencePanel` — the modal conversion changes framing, not the evidence link itself.
- **P2 — The Model Interprets, Code Calculates**: PASS (N/A). No LLM/scoring path is
  touched; `event_type` is a stored enum column read verbatim, never computed or guessed.
- **P3 — Each Component Refuses to Do the Next One's Job**: PASS. The backend passes
  `event_type` through as the raw enum string; the *frontend* owns the type→label/icon
  mapping — the same division already governing `severity` today. The backend does not
  start deciding icons; the frontend does not start deciding what counts as a "ticket."
- **P5 — Admit What We Cannot See**: PASS. `CoverageLine` is explicitly preserved
  (Clarifications 2026-08-18, FR-019) — relocated within column 2, never dropped, never
  visually diminished relative to today.
- **P6 — Silence Is a Success State**: PASS. The `healthy_quiet` near-empty branch in
  `dashboard-page.tsx` (FR-017) is untouched; no new column manufactures content when the
  account has nothing to show.
- **P7 — Context Over Sentiment**: PASS, and reinforced. FR-008 explicitly forbids a
  sentiment-style label, keeping severity (already baseline/context-derived, not a generic
  sentiment scale) as the only sentiment-adjacent signal shown.
- **P8 — Clean Architecture: the Dependency Rule Is Law**: PASS. `event_type` is added at
  every existing ring in place — adapter (`dashboard_router.py`'s Pydantic schema),
  application (`use_cases.py`'s `PulseEventResult`, `ports.py`'s `PulseEventRecord`) — with
  no new cross-ring import and no ring skipped. `dialog.tsx` lives in
  `frontend/src/components/ui/`, a presentation-only primitive with no data dependency.
- **P9 — Test-First Determinism**: PASS (N/A). No `backend/app/ledger/` or
  `backend/app/scoring/` file is touched; golden-replay/monotonicity/reconciliation are
  unaffected.
- **P10 — Simplicity Over Speculative Generality (YAGNI)**: PASS. `signal-type.ts`'s
  type→icon/label map is a fixed, closed 7-entry table (the enum's real values), not a
  pluggable/extensible registry; `dialog.tsx` wraps only what `EvidencePanel`/
  `DraftComposerPanel` need (no dropdown/table/tooltip primitives added speculatively).
- **P11 — Frontend: Feature-Oriented, Typed, Spec-Driven**: PASS. TypeScript throughout, no
  `any`; server state via the existing `useQuery`/`useMutation` calls, unchanged; the new
  Dialog primitive is exactly the "Radix-based component system (shadcn/ui)" P11 already
  requires, not a new library; accessibility parity is extended, not relaxed.
- **Full-Stack Engineering §5 — Zero Trust Validation**: PASS (N/A). `event_type` is a
  read-only, server-stored value never accepted as client input; no new request payload is
  introduced anywhere in this feature.

No violations. Complexity Tracking table is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/016-dashboard-mockup-v2-refinement/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── dashboard.md      # Phase 1 output — the one additive API field
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── checklists/
│   └── requirements.md   # /speckit-specify output, re-validated by /speckit-clarify
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
frontend/
├── package.json                              # MODIFIED — add @radix-ui/react-dialog
└── src/
    ├── dashboard/
    │   ├── dashboard-page.tsx                # MODIFIED — three-column grid; company
    │   │                                       title/days-to-renewal moved into column 1;
    │   │                                       one shared "active detail modal" state
    │   │                                       driving both EvidencePanel and
    │   │                                       DraftComposerPanel (research.md Decision 3)
    │   ├── dashboard-page.test.tsx           # MODIFIED
    │   ├── aura-risk-orb.tsx                 # NEW — band-colored gradient risk circle
    │   ├── aura-risk-orb.test.tsx            # NEW
    │   ├── signal-type.ts                    # NEW — TYPE_ICON / TYPE_LABEL closed maps
    │   ├── signal-type.test.ts               # NEW
    │   ├── pulse-timeline.tsx                # MODIFIED — dual-channel icon (shape=type,
    │   │                                       color=severity), connecting timeline line
    │   ├── pulse-timeline.test.tsx           # MODIFIED
    │   ├── score-block.tsx                   # MODIFIED — labeled X/Y axes, larger
    │   │                                       band-colored score treatment
    │   ├── score-block.test.tsx              # MODIFIED
    │   ├── churn-risk-overview-card.tsx      # MODIFIED — larger score number sizing
    │   └── types.ts                          # MODIFIED — PulseEvent gains `event_type`
    ├── ask/
    │   ├── ask-bar.tsx                       # MODIFIED — always-expanded docked panel,
    │   │                                       launcher/collapse state removed
    │   └── ask-bar.test.tsx                  # MODIFIED
    ├── evidence/
    │   ├── evidence-panel.tsx                # MODIFIED — renders via Dialog/DialogContent
    │   └── evidence-panel.test.tsx           # MODIFIED
    ├── draft-composer/
    │   ├── draft-composer-panel.tsx          # MODIFIED — renders via Dialog/DialogContent
    │   └── draft-composer-panel.test.tsx     # MODIFIED
    └── components/ui/
        ├── dialog.tsx                        # NEW — Radix Dialog wrapper (Dialog,
        │                                       DialogContent, DialogOverlay, DialogClose)
        └── dialog.test.tsx                   # NEW

backend/
├── app/experience/
│   ├── adapters/dashboard_router.py          # MODIFIED — PulseEvent gains event_type: str
│   ├── application/
│   │   ├── ports.py                          # MODIFIED — PulseEventRecord gains
│   │   │                                       event_type: str
│   │   └── use_cases.py                      # MODIFIED — PulseEventResult gains
│   │                                           event_type; execute() passes it through
│   └── adapters/sqlalchemy_repository.py     # MODIFIED — list_recent SELECTs e.event_type
└── tests/unit/test_dashboard_route.py        # MODIFIED — asserts event_type present and
                                                 within the 7-value enum

architecture/07-api-spec.md                   # MODIFIED — PulseEvent OpenAPI schema gains
                                                 event_type (constitution's "fix stale docs
                                                 everywhere" rule)
```

**Structure Decision**: Web application, frontend + backend — the first dashboard-redesign
feature since 012 to touch `backend/`, scoped to one additive field threaded through
existing layers with no migration and no new endpoint. Frontend work stays feature-oriented
inside the existing `dashboard/`, `ask/`, `evidence/`, and `draft-composer/` folders (P11),
plus one new shared primitive in `components/ui/` — following 012's precedent of growing
that directory only when a feature has a real, immediate need for it.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified

No violations — table intentionally omitted.
