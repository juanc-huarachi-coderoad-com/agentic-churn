---

description: "Task list for feature implementation"
---

# Tasks: Main Dashboard Visual Redesign

**Input**: Design documents from `/specs/012-dashboard-visual-redesign/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md (all present; no `contracts/` — see research.md Decision 7)

**Tests**: Included where they cover new/materially-changed behavior (constitution P11 requires unit + component tests per feature). Existing test files are *updated* in place for restyled components with unchanged props; new test files are added only where a file has no existing test today (`nav/sidebar.tsx` is new, `score-block.tsx` had no prior test).

**Organization**: Tasks are grouped by user story (spec.md P1/P2/P3) to enable independent implementation and testing of each.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- File paths are exact and relative to the repository root

## Path Conventions

Web app — this feature touches `frontend/src/` only (per plan.md's Project Structure). No `backend/` paths appear anywhere below; if any task seems to require one, stop — it violates FR-011.

<!-- Sample tasks from the template have been replaced with this feature's actual tasks. -->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Bring in the two new constitution-mandated dependencies and the shared class-merge helper everything else needs.

- [X] T001 Add `recharts` and `lucide-react` to `frontend/package.json` dependencies (`pnpm add recharts lucide-react` from `frontend/`) and commit the updated lockfile
- [X] T002 [P] Create `frontend/src/lib/utils.ts` exporting a `cn()` helper built on the already-installed `clsx` + `tailwind-merge` (research.md Decision 2)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The minimal shared design-system primitives every user story's UI is built from (research.md Decision 2). No user story work should start before these exist.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 [P] Create `frontend/src/components/ui/card.tsx` — a shadcn-style card primitive (built on `@radix-ui/react-slot`, styled via `cn()` from T002)
- [X] T004 [P] Create `frontend/src/components/ui/button.tsx` — a shadcn-style button primitive (same pattern as T003)
- [X] T005 [P] Create `frontend/src/components/ui/icon.tsx` — a thin wrapper around `lucide-react` icons for consistent sizing/stroke width across the sidebar, hub badges, and assistant launcher

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - See the redesigned dashboard layout (Priority: P1) 🎯 MVP

**Goal**: The dashboard renders the sidebar, Signal Stream, Churn Risk Overview card, and Action & Draft Hub in the mockup's positions, all populated by the existing `GET /api/dashboard` data, with zero change to state/query/data logic.

**Independent Test**: Load `/dashboard` for an account with active findings; confirm all four regions render in the mockup's positions with values identical to the pre-redesign dashboard (spec.md US1 Acceptance Scenarios 1–2); confirm sidebar navigation to `/coverage` and `/profile` still works (Acceptance Scenario 3).

### Tests for User Story 1

- [X] T006 [P] [US1] Update `frontend/src/dashboard/dashboard-page.test.tsx` to assert the new four-region layout renders (sidebar, Signal Stream, Churn Risk Overview card, Action & Draft Hub), while keeping every existing assertion about the `useQuery` call and `data.state` conditional branches (`no_profile` / `healthy_quiet` / `normal`) unchanged
- [X] T007 [P] [US1] Create `frontend/src/nav/sidebar.test.tsx` asserting the three destinations render (`/dashboard`, `/coverage`, `/profile`) with exactly one icon each and that the current route is visually indicated as active

### Implementation for User Story 1

- [X] T008 [US1] Create `frontend/src/nav/sidebar.tsx` — left icon-rail navigation using `NavLink` from `react-router` for `/dashboard`, `/coverage`, `/profile`, built from the T003–T005 primitives and `lucide-react` icons; no new routes added to `frontend/src/App.tsx` (depends on T003, T004, T005)
- [X] T009 [P] [US1] Restyle `frontend/src/dashboard/pulse-timeline.tsx` as the "Signal Stream" vertical timeline per the mockup (relative time, severity icon, evidence-backed excerpt) — same `PulseTimelineProps` (`events`, `onSelect`), same `score_contribution_id` → `EvidencePanel` wiring
- [X] T010 [US1] Create `frontend/src/dashboard/priority-tier.ts` exporting `priorityTierFromPoints(absPoints: number): 'high' | 'medium' | 'low'` per data-model.md's fixed-threshold display mapping (research.md Decision 3) — pure function, no new state
- [X] T011 [US1] Create `frontend/src/dashboard/action-draft-hub.tsx` composing `contribution_bars` only (via T010's `priorityTierFromPoints`) into the ranked, badge-labeled list per the mockup; selecting a row calls the same `onSelect(scoreContributionId)` pattern already used to open `EvidencePanel` — `narrator.actions` is NOT pulled in here (it has no ID to key off), and no new API call or fabricated ID is introduced (research.md Decision 3/4/8, corrected during implementation) (depends on T010)
- [X] T012 [US1] Create `frontend/src/dashboard/churn-risk-overview-card.tsx` — a card container (using T003's `card.tsx`) composing the existing `ScoreBlock` and `ContributionBars` output into one visual unit per the mockup; internal chart rendering is whatever `ScoreBlock` currently produces — the Recharts swap happens in US2, not here (depends on T003)
- [X] T013 [US1] Update `frontend/src/dashboard/dashboard-page.tsx` to compose the new three-column layout (sidebar left, Signal Stream center, Churn Risk Overview + Action & Draft Hub right) from T008, T009, T011, T012, preserving every existing `useQuery`, `useState`, and conditional-branch line verbatim — only the returned JSX structure changes (depends on T008, T009, T011, T012)
- [X] T014 [P] [US1] Restyle `frontend/src/dashboard/stakeholder-cards.tsx` and `frontend/src/dashboard/coverage-line.tsx` to match the new visual language, same props for both
- [X] T015 [US1] Add the static/decorative header controls required by FR-013 (date-range label, live-status badge, notification bell) directly in `frontend/src/dashboard/dashboard-page.tsx`'s header — hardcoded/presentational only, no new state or API call (depends on T013)

**Checkpoint**: User Story 1 is fully functional and independently testable — the four-region layout is live with real data, only the trend visualization (US2) and assistant placement (US3) are still using their pre-redesign shape.

---

## Phase 4: User Story 2 - Understand churn risk through the consolidated overview card (Priority: P2)

**Goal**: The Churn Risk Overview card renders the trend as a continuous Recharts area chart and the risk drivers as a properly ranked list, matching the mockup.

**Independent Test**: For an account with ≥2 score-history points, confirm the trend renders as a filled area (not disconnected points) and the risk-driver list is ranked by contribution with unchanged signs/magnitudes (spec.md US2 Acceptance Scenarios 1–2); for an account with <2 points, confirm graceful degradation (Acceptance Scenario 3).

### Tests for User Story 2

- [X] T016 [P] [US2] Create `frontend/src/dashboard/score-block.test.tsx` asserting: the score and band still render correctly, the area chart renders given a `trend: number[]` prop of length ≥2, and the <2-point case degrades gracefully instead of throwing or rendering a broken chart

### Implementation for User Story 2

- [X] T017 [US2] Replace the hand-rolled `Sparkline` SVG in `frontend/src/dashboard/score-block.tsx` with a Recharts `AreaChart`/`Area` consuming the same `trend: number[]` prop (index-based x-axis — no new fields), same `ScoreBlockProps` (`score`, `band`, `trend`, `onClick`) — depends on T001; remove the now-stale "SVG-based only, no chart library" code comment as part of this change
- [X] T018 [US2] Handle the `trend.length < 2` case in `frontend/src/dashboard/score-block.tsx` with a graceful presentation (e.g. a single point or a "not enough history yet" state) instead of a misleading or broken chart (depends on T017)
- [X] T019 [US2] Restyle `frontend/src/dashboard/contribution-bars.tsx`'s "Top risk drivers" rows to match the mockup's ranked bar-list styling inside `churn-risk-overview-card.tsx` (T012) — same `ContributionBar[]` props, sorted by `Math.abs(points)`

**Checkpoint**: User Stories 1 and 2 both independently functional — the overview card now matches the mockup fully.

---

## Phase 5: User Story 3 - Reach the AI assistant through a floating component (Priority: P3)

**Goal**: The AI assistant is a collapsible floating widget, starting collapsed on every load, reusing its existing conversational state untouched.

**Independent Test**: From a scrolled position, open the floating assistant without losing scroll position or page navigation (spec.md US3 Acceptance Scenario 1); collapse and reopen it and confirm the last exchange is still shown (Acceptance Scenario 2); confirm it never obscures the Signal Stream or Action & Draft Hub while collapsed (Acceptance Scenario 3).

### Tests for User Story 3

- [X] T020 [P] [US3] Update `frontend/src/ask/ask-bar.test.tsx` to assert: the assistant renders collapsed (launcher only) on mount, opening/collapsing it via the new toggle preserves `mutation.data` across the toggle, and the existing idle → thinking → answered behavior (same `postAsk` call) is unchanged

### Implementation for User Story 3

- [X] T021 [US3] Convert `frontend/src/ask/ask-bar.tsx`'s outer container from `fixed inset-x-0 bottom-0 z-40` (full-width bar) to a collapsible corner launcher + panel built from the T003–T005 primitives, defaulting to collapsed on every mount per FR-007 — the existing `useMutation`/`postAsk` call, `question` state, and `AnswerRenderer` usage are reused unchanged, only the wrapping shell is new (depends on T003, T004, T005)
- [X] T022 [US3] Verify and, if needed, adjust the floating assistant's z-index so it stays below `EvidencePanel`'s and `DraftComposerPanel`'s existing `z-50` overlays (matching today's `z-40` convention), so opening either overlay while the assistant is open leaves both usable (research.md Decision 5) (depends on T021)

**Checkpoint**: All three user stories independently functional — the redesign matches `base/mockup-mainPage.jpg` end to end.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Repo-wide checks that span all three stories.

- [X] T023 [P] Run `pnpm lint` and `pnpm format` in `frontend/` across every file touched by T001–T022 and fix findings
- [X] T024 [P] Run `pnpm typecheck` in `frontend/` and fix any type errors introduced by the `recharts`/`lucide-react` integration
- [X] T025 Grep `frontend/src/` for any remaining stale references to the old "SVG-based only, no chart library" or "always present, bottom of screen" comments (score-block.tsx, ask-bar.tsx) and remove/update them so code comments don't contradict the shipped behavior
- [X] T026 Execute every step in `specs/012-dashboard-visual-redesign/quickstart.md`, including the `git diff --stat` regression guard confirming zero changes to `frontend/src/dashboard/types.ts`, `ask/types.ts`, `draft-composer/types.ts`, `evidence/types.ts`, any `api.ts` file, or anywhere in `backend/`
- [X] T027 [P] Run `pnpm test:e2e` (Playwright) and add/update scenarios covering the new layout and floating-assistant flows described in quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on T001–T002 (needs `lucide-react` installed and `cn()` available) — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 completion — no dependency on US2 or US3
- **User Story 2 (Phase 4)**: Depends on Phase 2 completion; T017–T019 assume `churn-risk-overview-card.tsx` (T012) already exists, so in practice runs after Phase 3
- **User Story 3 (Phase 5)**: Depends on Phase 2 completion only — can run in parallel with Phase 4 by a different developer, since `ask-bar.tsx` is untouched by any US1/US2 task
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on US2/US3 — is the MVP slice
- **User Story 2 (P2)**: Builds inside the card US1 creates (T012) — sequenced after US1 in practice, though its own tests/logic are self-contained to `score-block.tsx`/`contribution-bars.tsx`
- **User Story 3 (P3)**: Touches only `ask/ask-bar.tsx` — genuinely independent of US1/US2 file-wise; only shares the Phase 2 primitives

### Parallel Opportunities

- T002 (Setup) can run in parallel with T001
- T003, T004, T005 (Foundational) can all run in parallel — different files
- T006, T007 (US1 tests) can run in parallel
- T009, T014 (US1 implementation) can run in parallel with each other and with T010/T011/T012 — different files
- T016 (US2 test) can run in parallel with any US1 task once Phase 2 is done
- T020 (US3 test) can run in parallel with any US1/US2 task — `ask-bar.tsx` is untouched elsewhere
- T023, T024, T027 (Polish) can run in parallel
- Once Phase 2 completes, a second developer can start all of Phase 5 (US3) in parallel with Phase 3/4, since no task in either phase touches `frontend/src/ask/`

---

## Parallel Example: User Story 1

```bash
# Launch both US1 tests together:
Task: "Update frontend/src/dashboard/dashboard-page.test.tsx for the new layout"
Task: "Create frontend/src/nav/sidebar.test.tsx"

# Launch independent US1 implementation files together:
Task: "Restyle frontend/src/dashboard/pulse-timeline.tsx as the Signal Stream"
Task: "Restyle frontend/src/dashboard/stakeholder-cards.tsx and coverage-line.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T005) — CRITICAL, blocks all stories
3. Complete Phase 3: User Story 1 (T006–T015)
4. **STOP and VALIDATE**: run quickstart.md's User Story 1 section independently
5. Demo the four-region layout with real data — this alone is a visible, shippable improvement

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. User Story 1 → validate independently → demo (MVP)
3. User Story 2 → validate independently → demo (proper area chart)
4. User Story 3 → validate independently → demo (floating assistant)
5. Polish (Phase 6) → full regression pass, including the FR-011 `git diff --stat` guard

### Parallel Team Strategy

With two developers, after Phase 2 completes:
- Developer A: Phase 3 (US1) then Phase 4 (US2), since US2 builds on US1's card
- Developer B: Phase 5 (US3) — touches only `frontend/src/ask/`, no file overlap with A's work

---

## Notes

- [P] tasks = different files, no dependencies between them
- [Story] label maps each task to its spec.md user story for traceability
- Every implementation task above names the exact prop interface or file it must not change, per FR-011 — when in doubt, re-read research.md before writing a new field, state hook, or API call
- Commit after each task or logical group
- Stop at each phase checkpoint to validate that story independently before moving on
