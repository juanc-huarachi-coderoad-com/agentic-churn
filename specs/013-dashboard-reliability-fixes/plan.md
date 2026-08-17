# Implementation Plan: Dashboard Reliability Fixes

**Branch**: `design/apply-new-mockup` | **Date**: 2026-08-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/013-dashboard-reliability-fixes/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Fix three small, independent reliability issues discovered while implementing and testing feature 012: (1) `answer-renderer.tsx`'s `DeltaBreakdown` and `RankedIssues` components key their list rows by `finding_type`, which real backend data can legitimately repeat across rows — swap to the already-present, genuinely unique `score_contribution_id`; (2) `dashboard-to-evidence.spec.ts`'s pulse-event locator breaks once two seeded events share identical quoted text — scope it to a single unambiguous element; (3) `login-to-dashboard.spec.ts` asserts a `"still learning"` dashboard state that the seeded account has since progressed past — replace with a state-independent assertion that still proves a successful login reached real dashboard content. All three are narrow, surgical diffs in already-identified files; no new dependencies, no new components, no backend changes.

## Technical Context

**Language/Version**: TypeScript ~6.0, React 18.3 (unchanged, matches feature 012)

**Primary Dependencies**: None new — uses only what's already imported in the three affected files (`answer-renderer.tsx` has no new imports needed; the two e2e specs use `@playwright/test`, already a dependency)

**Storage**: N/A — no data-layer change; fix #1 reads a field (`score_contribution_id`) the backend already returns and the frontend already types, just doesn't yet use for keying

**Testing**: `vitest` + `@testing-library/react` for a new regression test covering FR-001/FR-002 (duplicate `finding_type` rendering); `@playwright/test` for the two e2e fixes themselves, verified by re-running them repeatedly against the live shared dev database (SC-002/SC-003)

**Target Platform**: Web SPA (existing), no change

**Project Type**: Web application — this feature touches `frontend/src/ask/components/answer-renderer.tsx` and `frontend/e2e/*.spec.ts` only; zero `backend/` changes

**Performance Goals**: N/A — not a performance-sensitive change

**Constraints**: FR-007 (CRITICAL CONSTRAINT, carried from the spec): no dashboard visual/layout change, no business-logic/scoring change, no backend change. FR-006: the two e2e fixes must keep verifying the same real behavior, not be weakened until they merely stop failing.

**Scale/Scope**: 3 files touched (`answer-renderer.tsx`, `dashboard-to-evidence.spec.ts`, `login-to-dashboard.spec.ts`), 1 new test file (`answer-renderer.test.tsx`, which does not exist today)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies how | Status |
|---|---|---|
| P1 Evidence or It Does Not Exist | Each cause/issue row still cites its own real `score_contribution_id` — the fix strengthens this (each row now provably maps to its own evidence), doesn't touch it | Pass |
| P3 Each Component Refuses to Do the Next One's Job | `AnswerRenderer` still only renders what the backend already computed; the key change is presentational identity, not new interpretation | Pass |
| P9 Test-First Determinism | N/A — `backend/app/ledger/`, `backend/app/scoring/` untouched | Pass (N/A) |
| P10 Simplicity Over Speculative Generality | Fix uses the field already on the wire (`score_contribution_id`) — no new abstraction, no generic "unique key generator" utility for a problem this narrow | Pass |
| P11 Frontend: Feature-Oriented, Typed, Spec-Driven | Fix stays inside the existing `ask/` feature folder; TypeScript's existing `Cause` interface already types the field being adopted as the key | Pass |
| Full-Stack Engineering §4 "Comprehensive Testing Strategy" | New regression test added for the actual app-code bug (US1); both e2e fixes keep testing real behavior per FR-006 | Pass |

No violations requiring justification. Complexity Tracking table below is intentionally empty.

## Project Structure

### Documentation (this feature)

```text
specs/013-dashboard-reliability-fixes/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

No `contracts/` directory — no new interface is introduced; this is entirely an internal rendering-identity and test-locator fix.

### Source Code (repository root)

```text
frontend/
├── src/ask/components/
│   ├── answer-renderer.tsx       # MODIFIED — DeltaBreakdown/RankedIssues key by
│   │                              #   cause.score_contribution_id instead of finding_type
│   └── answer-renderer.test.tsx  # NEW — regression test for duplicate finding_type rendering
└── e2e/
    ├── dashboard-to-evidence.spec.ts  # MODIFIED — scope the pulse-event locator to one element
    └── login-to-dashboard.spec.ts     # MODIFIED — replace the state-dependent assertion

backend/                          # UNTOUCHED
```

**Structure Decision**: No structural change — fixes land in place inside the existing `frontend/src/ask/` feature folder and `frontend/e2e/`. No new directories, no new routes, no backend involvement.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified

*(no entries — no violations)*
