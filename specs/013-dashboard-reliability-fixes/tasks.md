---

description: "Task list for feature implementation"
---

# Tasks: Dashboard Reliability Fixes

**Input**: Design documents from `/specs/013-dashboard-reliability-fixes/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md (all present; no `contracts/`)

**Tests**: Included — US1 is a genuine app-code bug and gets a new regression test; US2/US3 fixes are themselves tests.

**Organization**: Tasks are grouped by user story (spec.md P1/P2/P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- File paths are exact and relative to the repository root

## Path Conventions

Web app — this feature touches exactly 4 files in `frontend/`, no `backend/` paths. If any task seems to require one, stop — it violates FR-007.

<!-- Sample tasks from the template have been replaced with this feature's actual tasks. -->

## Phase 1: Setup

**Purpose**: Confirm a clean baseline before touching anything, so any failure surfaced later is attributable to this feature's changes.

- [X] T001 Run `pnpm typecheck && pnpm lint && pnpm test` in `frontend/` and confirm all green before making any change

*(No Foundational phase — the three user stories touch entirely disjoint files with no shared setup beyond T001.)*

---

## Phase 2: User Story 1 - The Ask agent's answer never warns about or risks losing duplicate-finding-type rows (Priority: P1) 🎯 MVP

**Goal**: `DeltaBreakdown` and `RankedIssues` key their rows by the already-unique `score_contribution_id`, not the repeatable `finding_type`.

**Independent Test**: Render an answer with two causes sharing a `finding_type` but different `score_contribution_id`s; confirm both rows render, each opens evidence for its own finding, and no duplicate-key console warning fires.

### Tests for User Story 1

- [X] T002 [P] [US1] Create `frontend/src/ask/components/answer-renderer.test.tsx`: render `DeltaBreakdown` (via `AnswerRenderer` with `component: 'delta_breakdown'`) with two `causes` sharing `finding_type: 'broken_response_promise'` but distinct `score_contribution_id`s; assert both rows render with their own point values, assert clicking each calls `onOpenEvidence` with its own `score_contribution_id`, and assert `console.error`/`console.warn` is never called with a message matching `/unique.*key/i` during the render (spy on console before render, restore after)

### Implementation for User Story 1

- [X] T003 [US1] In `frontend/src/ask/components/answer-renderer.tsx`, change `DeltaBreakdown`'s `<li key={cause.finding_type}>` to `<li key={cause.score_contribution_id}>` (research.md Decision 1)
- [X] T004 [US1] In `frontend/src/ask/components/answer-renderer.tsx`, change `RankedIssues`'s `<li key={issue.finding_type}>` to `<li key={issue.score_contribution_id}>` (research.md Decision 1)

**Checkpoint**: T002 fails before T003/T004 and passes after — confirms the fix and the regression test both work.

---

## Phase 3: User Story 2 - The evidence-panel end-to-end test passes regardless of duplicate quoted text in the dataset (Priority: P2)

**Goal**: `dashboard-to-evidence.spec.ts`'s pulse-event locator resolves to exactly one element even when the seeded database has multiple events with identical quoted text.

**Independent Test**: Run the affected e2e test against the live shared dev database; confirm it passes without a Playwright strict-mode violation.

### Implementation for User Story 2

- [X] T005 [US2] In `frontend/e2e/dashboard-to-evidence.spec.ts`, change `const event = page.getByText('"Slow API response"')` to `const event = page.getByText('"Slow API response"').first()` (research.md Decision 2 — matches the existing `.first()` pattern already used elsewhere in this same file)

**Checkpoint**: `pnpm test:e2e e2e/dashboard-to-evidence.spec.ts` passes (all three tests in the file).

---

## Phase 4: User Story 3 - The login end-to-end test passes regardless of which valid dashboard state the seeded account is currently in (Priority: P3)

**Goal**: `login-to-dashboard.spec.ts`'s "reaches the dashboard shell" test no longer depends on the seeded account being in the `learning` state specifically.

**Independent Test**: Run the affected e2e test against the live shared dev database in its current (possibly-progressed) state; confirm it passes.

### Implementation for User Story 3

- [X] T006 [US3] In `frontend/e2e/login-to-dashboard.spec.ts`, replace `await expect(page.getByText(/still learning/i)).toBeVisible()` with `await expect(page.getByRole('navigation', { name: 'Primary' })).toBeVisible()`, keeping the existing `getByRole('heading', { name: 'Meridian Logistics' })` assertion unchanged (research.md Decision 3 — reuses feature 012's sidebar landmark)

**Checkpoint**: `pnpm test:e2e e2e/login-to-dashboard.spec.ts` passes (all three tests in the file).

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Full regression pass and the FR-007 scope guard.

- [X] T007 [P] Run `pnpm typecheck && pnpm lint && pnpm test` in `frontend/` — all must pass
- [X] T008 Run `pnpm test:e2e` (full suite) at least 3 times in a row to build confidence against SC-002/SC-003's "consecutive runs" claim, given the shared dev database is live and mutating during a real dev session
- [X] T009 Run `git diff --stat` and confirm the only files touched are `frontend/src/ask/components/answer-renderer.tsx`, `frontend/src/ask/components/answer-renderer.test.tsx`, `frontend/e2e/dashboard-to-evidence.spec.ts`, and `frontend/e2e/login-to-dashboard.spec.ts` (FR-007)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **User Story 1 (Phase 2)**: Depends only on T001 — touches `answer-renderer.tsx`/`.test.tsx` only
- **User Story 2 (Phase 3)**: Depends only on T001 — touches `dashboard-to-evidence.spec.ts` only, zero file overlap with US1/US3
- **User Story 3 (Phase 4)**: Depends only on T001 — touches `login-to-dashboard.spec.ts` only, zero file overlap with US1/US2
- **Polish (Phase 5)**: Depends on all three user stories being complete

### Parallel Opportunities

All three user stories can run fully in parallel after T001 — they share no files. A single developer can also just do them in priority order (P1 → P2 → P3) sequentially without any cross-story blocking.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001 (baseline)
2. Phase 2 (US1: the real app bug)
3. **STOP and VALIDATE**: `pnpm test src/ask/components/answer-renderer.test.tsx`
4. This alone fixes the one issue with real user-facing risk; US2/US3 are test-suite hygiene and can land separately if needed

### Incremental Delivery

1. T001 → baseline confirmed
2. US1 → validate → the app bug is fixed
3. US2 → validate → evidence e2e is reliable again
4. US3 → validate → login e2e is reliable again
5. Polish → full regression + FR-007 guard

---

## Notes

- [P] tasks = different files, no dependencies between them
- Every task names the exact file and exact line-level change per research.md — there is no ambiguity left to resolve during implementation
- Commit after each user story (or all together, given the total diff is 4 files)
