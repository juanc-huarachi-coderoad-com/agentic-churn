---

description: "Task list template for feature implementation"
---

# Tasks: Input Connectors View

**Input**: Design documents from `/specs/022-input-connectors-view/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Included. Constitution P11 ("every feature ships unit + component tests") applies
to this frontend feature, so test tasks are not optional here.

**Organization**: Tasks are grouped by user story (spec.md) to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Paths are frontend-only (`frontend/`) — this feature has no backend component (plan.md)

## Path Conventions

Web app, per plan.md's Project Structure: `frontend/src/input-connectors/` (new feature
directory), `frontend/src/nav/` (modified), `frontend/public/icons/connectors/` (new assets).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Acquire the one piece of infrastructure every story's UI depends on: real
brand icon assets (research.md Decision 1).

- [X] T001 [P] Source and add official brand SVG marks to `frontend/public/icons/connectors/`: `gmail.svg`, `slack.svg`, `zendesk.svg`, `microsoft365.svg`, `teams.svg`, `salesforce.svg`, `jira.svg`, `intercom.svg`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared types, static data catalog, and rendering primitives every user story's
page relies on. No user story work should begin until this phase is complete.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 [P] Define `Connector`, `ConnectorStatus`, `ConnectorGroup` types in `frontend/src/input-connectors/types.ts` per data-model.md
- [X] T003 [P] Create `status-badge.tsx` (Live/Simulated/Planned label + color, text-based not color-only per FR-008) in `frontend/src/input-connectors/status-badge.tsx`
- [X] T004 Create `brand-icon.tsx` wrapper rendering the assets from `frontend/public/icons/connectors/` in `frontend/src/input-connectors/brand-icon.tsx` (depends on T001, T002 — not parallelizable with either)
- [X] T005 Create the static catalog (14 connectors across 3 groups, per data-model.md's fixed table) in `frontend/src/input-connectors/connectors-data.ts` (depends on T002)
- [X] T006 [P] Create `connectors-data.test.ts` in `frontend/src/input-connectors/connectors-data.test.ts` asserting: each group's connector count matches the fixed table (1 live / 6 simulated / 7 planned), `id` is unique across the catalog, `pipeline` is present only when `status === 'live'`, and every `kind: 'brand'` connector's `asset` filename matches one of the files introduced in T001 (depends on T005)
- [X] T007 Add the "Input Connectors" destination (plug icon, path `/connectors`) to `frontend/src/nav/destinations.ts`, the same array `Sidebar` and `Breadcrumb` both read

**Checkpoint**: Foundation ready — types, data, shared badge/icon primitives, and the nav
entry exist. User story implementation can now begin.

---

## Phase 3: User Story 1 - See every data source and its readiness at a glance (Priority: P1) 🎯 MVP

**Goal**: A user opens the Input Connectors page and sees all 14 connectors correctly
grouped into Live / Simulated / Planned, each entry showing name, icon, description, and
status badge — matching `base/mockupInputConectors.jpg`.

**Independent Test**: Navigate to the page and confirm three labeled groups with accurate
counts (Live (1), Simulated (6), Planned (7)) render, each entry showing name + icon +
description + badge, per spec.md Acceptance Scenarios 1–3.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T008 [P] [US1] Component test for `ConnectorCard` in `frontend/src/input-connectors/connector-card.test.tsx` — asserts name, icon, description, and status badge all render for a sample connector of each status
- [X] T009 [P] [US1] Component test for `InputConnectorsPage` in `frontend/src/input-connectors/input-connectors-page.test.tsx` — asserts three group headings render with counts "Live (1)", "Simulated (6)", "Planned (7)" and that each heading's count equals the number of entries rendered beneath it

### Implementation for User Story 1

- [X] T010 [US1] Create `ConnectorCard` in `frontend/src/input-connectors/connector-card.tsx` — renders `BrandIcon` or a `lucide-react` fallback icon, name, description, and `StatusBadge` (depends on T003, T004, T008)
- [X] T011 [US1] Create `InputConnectorsPage` in `frontend/src/input-connectors/input-connectors-page.tsx` — wraps content in `AppShell`, derives the three `ConnectorGroup`s from `connectors-data.ts` (group headings show `connectors.length`, never a hand-typed number, per research.md Decision 3), renders a `ConnectorCard` per entry (depends on T005, T010, T009)
- [X] T012 [US1] Register the `/connectors` route (wrapped in `ProtectedRoute`) pointing at `InputConnectorsPage` in `frontend/src/App.tsx` (depends on T011)

**Checkpoint**: User Story 1 is fully functional and testable independently — the page is
reachable from the sidebar and renders the full, correctly grouped catalog.

---

## Phase 4: User Story 2 - Understand what a specific connector does (Priority: P2)

**Goal**: Every connector's one-line description (and, for Transcripts, its underlying
pipeline) is accurate and self-explanatory enough that a non-technical user needs no
further help.

**Independent Test**: Read each entry's description text and confirm the Live entry names
its pipeline (local storage, OpenAI Whisper, pyannote.ai, Anthropic) and every other entry
has a clear, plain-language description, per spec.md Acceptance Scenarios 1–2.

### Tests for User Story 2

- [X] T013 [P] [US2] Extend `connector-card.test.tsx` (`frontend/src/input-connectors/connector-card.test.tsx`) with a case asserting the Live/Transcripts entry renders "Meeting audio" plus all four pipeline services
- [X] T014 [P] [US2] Extend `connectors-data.test.ts` (`frontend/src/input-connectors/connectors-data.test.ts`) asserting every connector has a non-empty `description` string

### Implementation for User Story 2

- [X] T015 [US2] Extend `ConnectorCard` (`frontend/src/input-connectors/connector-card.tsx`) to render the `pipeline` list as a distinct, muted sub-line beneath the description when present (depends on T010, T013)
- [X] T016 [US2] Fill in accurate, plain-language one-line `description` copy for all 13 non-Live connectors in `frontend/src/input-connectors/connectors-data.ts` (depends on T005, T014)

**Checkpoint**: User Stories 1 AND 2 both work independently — every entry is self-explanatory.

---

## Phase 5: User Story 3 - Discover how to add a new connector (Priority: P3)

**Goal**: An "Add Connector" action is clearly visible at the top of the page.

**Independent Test**: Load the page and confirm an "Add Connector" action is visible near
the top, per spec.md Acceptance Scenario 1.

### Tests for User Story 3

- [X] T017 [P] [US3] Extend `input-connectors-page.test.tsx` (`frontend/src/input-connectors/input-connectors-page.test.tsx`) asserting an "Add Connector" button is present and labeled

### Implementation for User Story 3

- [X] T018 [US3] Add the "Add Connector" action (lucide `Plus` icon + label) to the page header in `frontend/src/input-connectors/input-connectors-page.tsx` (depends on T011, T017)

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Fidelity to the reference mockup and accessibility/regression checks that span
all three stories.

- [X] T019 [P] Visual pass: match spacing, colors, group order, and card layout to `base/mockupInputConectors.jpg` (FR-010) across `frontend/src/input-connectors/`
- [X] T020 [P] Accessibility pass: keyboard focus states on cards and the "Add Connector" button, `aria-label`s where icon-only, confirm status is conveyed by label text everywhere (never color alone, FR-008)
- [X] T021 Run `quickstart.md`'s full validation: `npm run typecheck`, `npm run lint`, `npm test` (frontend, full suite) and the backend test suite, confirming zero regressions (FR-009, SC-004)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T004 needs T001 and T002) — BLOCKS all user stories
- **User Stories (Phase 3–5)**: All depend on Foundational phase completion
  - US1 has no dependency on US2/US3
  - US2 extends US1's `ConnectorCard`/data module (T010, T005) — depends on US1's Phase 3 tasks being done first, since it modifies the same files
  - US3 extends US1's `InputConnectorsPage` (T011) — depends on US1's Phase 3 tasks
- **Polish (Phase 6)**: Depends on all three user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — no dependency on other stories
- **User Story 2 (P2)**: Builds on US1's `ConnectorCard` and `connectors-data.ts` (extends, doesn't duplicate) — start after US1's Phase 3 checkpoint
- **User Story 3 (P3)**: Builds on US1's `InputConnectorsPage` header — start after US1's Phase 3 checkpoint; independent of US2

### Within Each User Story

- Tests written first, confirmed failing, then implementation
- Shared primitives (types, badge, icon, data) before page/card composition
- Story complete before moving to the next priority (US2/US3 both literally extend US1's files, so sequencing after US1 avoids merge conflicts)

### Parallel Opportunities

- T001 and T002 can run in parallel — different files, no shared dependencies (T003 too, in parallel with both)
- T008 and T009 (US1 tests) can run in parallel — different files
- T013 and T014 (US2 tests) can run in parallel — different files
- T019 and T020 (Polish) can run in parallel — different concerns, overlapping files reviewed independently

---

## Parallel Example: Foundational Phase

```bash
# T001 (icon assets) has no code dependency and can run alongside these:
Task: "Define Connector/ConnectorStatus/ConnectorGroup types in frontend/src/input-connectors/types.ts"
Task: "Create status-badge.tsx in frontend/src/input-connectors/status-badge.tsx"

# T004 runs only after T001 and T002 above complete — not part of this parallel batch:
Task: "Create brand-icon.tsx in frontend/src/input-connectors/brand-icon.tsx"
```

## Parallel Example: User Story 1

```bash
Task: "Component test for ConnectorCard in frontend/src/input-connectors/connector-card.test.tsx"
Task: "Component test for InputConnectorsPage in frontend/src/input-connectors/input-connectors-page.test.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (brand icon assets)
2. Complete Phase 2: Foundational (types, data catalog, badge/icon primitives, nav entry)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Open the page, confirm it matches the mockup's grouping and counts
5. This is already a demoable MVP — the full 14-connector catalog is visible and correctly grouped

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. Add User Story 1 → validate independently → demo (MVP)
3. Add User Story 2 → validate independently → demo (richer descriptions/pipeline detail)
4. Add User Story 3 → validate independently → demo ("Add Connector" affordance)
5. Polish → mockup-fidelity and accessibility pass, full regression check

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US2 and US3 both extend files US1 creates (`connector-card.tsx`, `connectors-data.ts`,
  `input-connectors-page.tsx`) rather than creating new ones — this is a small, single-page
  feature, so "independently testable" means each story's acceptance scenarios can be
  verified on their own, not that every story owns disjoint files
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
