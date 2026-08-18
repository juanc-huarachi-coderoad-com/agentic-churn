---

description: "Task list for feature implementation"
---

# Tasks: Group Repeated Risk Drivers

**Input**: Design documents from `/specs/015-group-risk-drivers/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md (all present; no `contracts/` — this feature exposes no interface to another system, see plan.md's Project Structure)

**Tests**: Included — grouping is new presentation logic and gets unit + component regression tests (P11's test hierarchy).

**Organization**: Tasks are grouped by user story (spec.md P1/P1).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- File paths are exact and relative to the repository root

## Path Conventions

Web app — this feature touches exactly 4 files, all in `frontend/src/dashboard/`, no `backend/` paths. If any task seems to require one, stop — it violates FR-008.

<!-- Sample tasks from the template have been replaced with this feature's actual tasks. -->

## Phase 1: Setup

**Purpose**: Confirm a clean baseline before touching anything, so any failure surfaced later is attributable to this feature's changes.

- [X] T001 Run `pnpm typecheck && pnpm lint && pnpm test` in `frontend/` and confirm all green before making any change

*(No Foundational phase — both user stories are delivered by the same small set of files; there is no shared setup beyond T001.)*

---

## Phase 2: User Story 1 - A repeated driver label reads as one clear signal, not visual noise (Priority: P1) 🎯 MVP

**Goal**: "Top Risk Drivers" shows at most one row per distinct label, with a combined point value, a count indicator when more than one signal contributed, and rows ordered by combined impact (FR-001, FR-002, FR-003, FR-004, FR-007).

**Independent Test**: Load a client whose latest score run has multiple same-label signals with different point values; confirm the list shows one row per distinct label with the correct net value, count badge, and descending-impact order.

### Tests for User Story 1

- [X] T002 [P] [US1] Create `frontend/src/dashboard/group-contribution-bars.test.ts`: assert same-label bars sum into one group with the correct net signed points and full `contribution_ids` list (data-model.md's construction rule), assert a single-label bar passes through as a group of one, assert a group mixing risk-increasing and risk-reducing signals of the same label nets out correctly (Edge Cases), and assert groups sort by `Math.abs(points)` descending (research.md Decision 2)
- [X] T003 [P] [US1] Create `frontend/src/dashboard/contribution-bars.test.tsx`: assert duplicate labels collapse into one visible row with a `×N` badge, assert a label with a single signal shows no badge and calls `onSelect` directly on click (FR-004)

### Implementation for User Story 1

- [X] T004 [US1] Create `frontend/src/dashboard/group-contribution-bars.ts`: export `signedPoints()` (moved from the inline formula previously in `contribution-bars.tsx`) and `groupContributionBars()` implementing data-model.md's `GroupedContributionBar` construction rule (group by `label`, sum `signedPoints`, derive `is_positive`, collect `contribution_ids`, sort by `Math.abs(points)` descending) (research.md Decisions 1 and 2)
- [X] T005 [US1] Modify `frontend/src/dashboard/contribution-bars.tsx` to call `groupContributionBars(bars)` instead of rendering `bars` 1:1; render one `<li>` per group keyed by `label`, showing the label, a `×N` count badge when `contribution_ids.length > 1`, the bar width and color from the group's net `points`/`is_positive` (reusing the existing `barColorClass` logic), and the formatted net point value

**Checkpoint**: T002/T003 pass against T004/T005 — duplicate-label visual noise is gone, sort order matches spec.md's SC-004.

---

## Phase 3: User Story 2 - Every individual signal remains traceable to its own evidence (Priority: P1)

**Goal**: A grouped row can be expanded to reveal every contributing signal as its own sub-row, each independently selectable to open its own evidence (FR-005, FR-006).

**Independent Test**: Expand a grouped driver row with multiple contributing signals; confirm each sub-row, when selected, opens evidence for that exact signal and no other.

### Tests for User Story 2

- [X] T006 [US2] Add cases to `frontend/src/dashboard/contribution-bars.test.tsx` (same file as T003): assert clicking a grouped row expands it into one sub-row per `contribution_id`, assert clicking a specific sub-row calls `onSelect` with that sub-row's own `score_contribution_id` and not any other group member's id, assert a single-signal row's evidence still opens with no extra expand step (FR-004, unchanged behavior)

### Implementation for User Story 2

- [X] T007 [US2] Extend `frontend/src/dashboard/contribution-bars.tsx` with local `useState<string | null>` tracking which group label (if any) is expanded (research.md Decision 3); toggle it on click for a group with `contribution_ids.length > 1` instead of calling `onSelect` directly; render an expanded group's sub-rows (one per `contribution_id`, looked up in the original `bars` array) each wired to `onClick={() => onSelect(id)}`, unchanged `EvidencePanel`/`useEvidence` contract

**Checkpoint**: T006 passes — every individual signal, grouped or not, remains reachable to its own evidence (spec.md SC-003).

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Full regression pass and the FR-008/FR-009 scope guard.

- [X] T008 [P] Run `pnpm typecheck && pnpm lint && pnpm test` in `frontend/` — all must pass (8 new tests + all 23 existing `src/dashboard` tests green)
- [X] T009 Manual visual check per `quickstart.md`'s "Manual visual check" section against a client with repeated driver labels — confirm grouped rows, count badges, expand/collapse, and correct per-finding evidence linking
- [X] T010 Run `git diff --stat` (plus untracked new files) and confirm changes are confined to `frontend/src/dashboard/group-contribution-bars.ts`, `frontend/src/dashboard/group-contribution-bars.test.ts`, `frontend/src/dashboard/contribution-bars.tsx`, and `frontend/src/dashboard/contribution-bars.test.tsx` — no backend, `types.ts`, `evidence/`, `dashboard-page.tsx`, or `action-draft-hub.tsx` diff (FR-008, FR-009)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **User Story 1 (Phase 2)**: Depends only on T001
- **User Story 2 (Phase 3)**: Depends on Phase 2 (T004/T005) — expand/collapse (T007) is additive behavior on top of the grouped rendering US1 introduces; it cannot be built or tested against ungrouped rows
- **Polish (Phase 4)**: Depends on both user stories being complete

### Parallel Opportunities

T002 and T003 (different files) can be written in parallel. T004 has no dependents until T005, but T005 depends on T004 existing (it imports `groupContributionBars`). User Story 2 is not parallel with User Story 1 (see above) but is a small, additive extension of the same two files US1 touches, not a new file.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001 (baseline)
2. Phase 2 (US1: grouped, deduplicated, sorted rows)
3. **STOP and VALIDATE**: `pnpm test src/dashboard/group-contribution-bars.test.ts src/dashboard/contribution-bars.test.tsx`
4. This alone fixes the visual-duplication complaint; expand-to-evidence (US2) is what keeps the fix from regressing the evidence-trace guarantee, so in practice both shipped together — see Notes.

### Incremental Delivery

1. T001 → baseline confirmed
2. US1 → validate → duplicate rows are gone, sorted correctly
3. US2 → validate → every individual signal is still traceable to its own evidence
4. Polish → full regression + FR-008/FR-009 scope guard

---

## Notes

- [P] tasks = different files, no dependencies between them
- This tasks.md documents work already implemented on the current branch, retroactively, per this repository's spec-first convention (`AGENTS.md`) — T002–T010 describe what was built and verified, not a forward plan
- US1 and US2 were implemented and landed together in practice (same two files, same commit boundary) because shipping grouping without the expand-to-evidence escape hatch would itself violate P1 ("Evidence or It Does Not Exist") — the phase split above exists for traceability to spec.md's priorities, not because they were deployed separately
- Commit boundary: all four files (`group-contribution-bars.ts`, its test, `contribution-bars.tsx`, its test) in one change, matching T010's scope guard
