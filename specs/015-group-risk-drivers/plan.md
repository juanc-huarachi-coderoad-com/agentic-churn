# Implementation Plan: Group Repeated Risk Drivers

**Branch**: `015-group-risk-drivers` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/015-group-risk-drivers/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

"Top Risk Drivers" (part of the Churn Risk Overview card) renders `contribution_bars`
1:1 — one row per `score_contributions` row, per the evidence-trace contract feature
006 established and feature 012's redesign inherited unchanged. When a client's latest
score run has several findings of the same `finding_type` (e.g. three separate
`contractual_reference` findings), that 1:1 rendering surfaces the same label several
times with different point deltas, which reads as a duplication bug even though every
row is a distinct, real signal.

Technical approach: group same-label bars into one row **client-side only**, in a new
pure function (`frontend/src/dashboard/group-contribution-bars.ts`) consumed by
`frontend/src/dashboard/contribution-bars.tsx`. The grouped row shows the net summed
point value and, when more than one signal contributed, a count badge; expanding it
reveals each original signal as its own sub-row, each still calling the existing
`onSelect(score_contribution_id)` callback unchanged. `contribution_bars` itself, the
`ContributionBar` type, `DashboardResponse`, the backend (`use_cases.py`,
`sqlalchemy_repository.py`), and `EvidencePanel`/`useEvidence` are untouched — this
keeps feature 006's "every bar traces to a real row, no extra, no missing" contract
exactly as tested today. As a side effect, the grouped list is sorted by
`Math.abs(points)` descending, which feature 012's `data-model.md` already documented
as the intended sort for this list but which `contribution-bars.tsx` never actually
implemented.

## Technical Context

**Language/Version**: TypeScript 5 / React 18 (existing frontend stack, no change)

**Primary Dependencies**: None added. Reuses React's built-in `useState` for local
expand/collapse UI state (no Zustand — this is ephemeral, component-local state, not
shared/global, consistent with P11's "no global state by default").

**Storage**: N/A — presentation-only; no persisted data is read, written, or reshaped.

**Testing**: Vitest + `@testing-library/react` + `@testing-library/user-event`, matching
the existing pattern in `frontend/src/dashboard/score-block.test.tsx`.

**Target Platform**: Web (existing React 18 + Vite frontend, unchanged)

**Project Type**: Web application (frontend + backend) — this feature touches
`frontend/` only; no `backend/` file is read, written, or otherwise affected.

**Performance Goals**: No new goal. Grouping runs client-side, once per render, over an
already-small array (bounded by how many findings exist for one client's latest score
run — never a large N); negligible cost, no memoization introduced.

**Constraints**: Must not change the `contribution_bars` API shape or the 1:1
evidence-trace contract feature 006 tests (`specs/006-dashboard-evidence-trace/quickstart.md`);
must not introduce a new UI/icon/chart/state library (P11, Full-Stack Engineering §2 —
closed technology choices); the expand/collapse control must remain keyboard-accessible
(P11 Accessibility).

**Scale/Scope**: One dashboard card ("Churn Risk Overview" → "Top Risk Drivers"). Three
frontend files added, one modified, no backend/database/API changes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **P1 — Evidence or It Does Not Exist**: PASS. Every individual finding remains
  independently selectable and opens its own real evidence via its own
  `score_contribution_id` (FR-006); grouping never blends or summarizes evidence itself,
  only the point-value display.
- **P2 — The Model Interprets, Code Calculates**: PASS (N/A). No LLM/model call is
  involved; the sum is plain arithmetic over already-calculated `points` values, done in
  the presentation layer, not scoring.
- **P3 — Each Component Refuses to Do the Next One's Job**: PASS. The grouping function
  performs no calculation the scoring engine doesn't already own (points are read, never
  recomputed with new logic) — it only re-presents an existing array.
- **P5 — Admit What We Cannot See**: PASS (N/A). No change to degraded-state handling.
- **P6 — Silence Is a Success State**: PASS. The empty-state behavior
  (`bars.length === 0` → render nothing) is unchanged.
- **P8 — Clean Architecture**: PASS (N/A for frontend-only, presentation-layer change).
  No backend ring is touched; the new file lives alongside its consumer in
  `frontend/src/dashboard/`, matching P11's feature-oriented colocation.
- **P10 — Simplicity Over Speculative Generality**: PASS. One small pure function, no
  new abstraction layer, no configurability beyond what the spec requires (e.g. no
  configurable grouping strategy, no cap parameter nobody asked for).
- **P11 — Frontend standards**: PASS. TypeScript throughout, no `any`; local `useState`
  for local-only UI state; unit test for the pure function + component test for
  render/interaction, matching the existing test hierarchy; no new styling/icon/chart
  library introduced.

No violations. Complexity Tracking table is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/015-group-risk-drivers/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

No `contracts/` directory: this feature exposes no interface to another system or
module — it only changes how an already-fetched, already-typed array
(`DashboardResponse.contribution_bars`) is presented inside one component. (Feature 012,
the last purely-presentational dashboard feature, made the same choice for the same
reason.)

### Source Code (repository root)

```text
frontend/
├── src/
│   └── dashboard/
│       ├── group-contribution-bars.ts        # NEW — pure grouping function
│       ├── group-contribution-bars.test.ts   # NEW — unit tests
│       ├── contribution-bars.tsx             # MODIFIED — renders grouped rows,
│       │                                       expand/collapse for multi-signal groups
│       └── contribution-bars.test.tsx        # NEW — component tests
```

**Structure Decision**: Web application, frontend-only change, feature-oriented
placement inside the existing `frontend/src/dashboard/` feature folder (P11) — no new
top-level directory, no `backend/` path touched (this feature has no
`## Path Conventions` "stop if a backend path seems required" trip-wire to worry about,
since none is touched).

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified

No violations — table intentionally omitted.
