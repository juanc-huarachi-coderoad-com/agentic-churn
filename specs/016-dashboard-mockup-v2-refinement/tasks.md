---

description: "Task list for feature implementation"
---

# Tasks: Dashboard Mockup V2 Refinement

**Input**: Design documents from `/specs/016-dashboard-mockup-v2-refinement/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/dashboard.md, quickstart.md (all present)

**Tests**: Included — this feature ships new presentation logic (dual-channel icons, a new modal primitive, a docked assistant) and one additive backend field, so it gets unit + component + backend route regression tests per P11's test hierarchy, matching `specs/015-group-risk-drivers/tasks.md`'s precedent.

**Organization**: Tasks are grouped by user story (spec.md P1–P5).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: Which user story this task belongs to (US1–US5)
- File paths are exact and relative to the repository root

## Path Conventions

Web app — `frontend/src/` and `backend/app/`, per plan.md's Project Structure. This is the
first dashboard-redesign feature since 012 to touch `backend/`; the backend edits are
scoped to four existing files under `backend/app/experience/`, one existing test, and
`architecture/07-api-spec.md` — no migration, no new route.

<!-- Sample tasks from the template have been replaced with this feature's actual tasks. -->

## Phase 1: Setup

**Purpose**: Confirm a clean baseline and bring in the one new dependency before touching any feature code.

- [X] T001 Run `pnpm typecheck && pnpm lint && pnpm test` in `frontend/`, and `pytest backend/tests/unit/test_dashboard_route.py` in `backend/`; confirm all green before making any change
- [X] T002 [P] Add `@radix-ui/react-dialog` to `frontend/package.json` dependencies and run `pnpm install` (research.md Decision 2)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The one piece of shared infrastructure two later stories both need — must exist before US1's orb and US2's chart both consume it.

**⚠️ CRITICAL**: T006 (US1) and T011 (US2) both import from T003 — do not start either before T003 is done.

- [X] T003 [P] Extract `BAND_CHART_COLOR` out of `frontend/src/dashboard/score-block.tsx` into a new `frontend/src/dashboard/band-colors.ts` (export `BAND_CHART_COLOR: Record<Band, string>`, same three hex values, unchanged); update `score-block.tsx` to import it instead of declaring it locally (research.md Decision 6, data-model.md)

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 - See the three-column, full-height layout (Priority: P1) 🎯 MVP

**Goal**: Three columns fill the viewport, each scrolling independently; column 1 shows the company title and a band-colored AURA risk orb; `NarratorPanel`/`StakeholderCards`/`CoverageLine` relocate beneath the Signal Stream in column 2; narrow-viewport reflow is preserved (FR-001, FR-002, FR-003, FR-018, FR-019).

**Independent Test**: Load `/dashboard` for an account with active findings; confirm three columns are visible and each occupies full viewport height; force one column to overflow and confirm only it scrolls; narrow the window and confirm the layout reflows instead of clipping.

### Tests for User Story 1

- [X] T004 [P] [US1] Update `frontend/src/dashboard/dashboard-page.test.tsx`: assert a three-column grid renders (three distinct column containers), assert `client_header.client_name`/`days_to_renewal` render inside column 1 (not the old top header row), assert `NarratorPanel`/`StakeholderCards`/`CoverageLine` render inside column 2's container after `PulseTimeline`, and assert each column container carries independent-scroll styling (e.g. `overflow-y-auto` with a bounded height) — confirm this fails against today's two-column markup before implementing
- [X] T005 [P] [US1] Create `frontend/src/dashboard/aura-risk-orb.test.tsx`: assert the orb renders the given `score`, and that its color/gradient class changes across `healthy`/`watch`/`at_risk` `band` values, sourced from `BAND_CHART_COLOR` (T003)

### Implementation for User Story 1

- [X] T006 [US1] Create `frontend/src/dashboard/aura-risk-orb.tsx` exporting `AuraRiskOrb({ score, band }: { score: number; band: Band })`: a radial-gradient circle colored via `BAND_CHART_COLOR[band]` (`band-colors.ts`, T003) with the score rendered inside it (research.md Decision 6) (depends on T003, T005)
- [X] T007 [US1] Modify `frontend/src/dashboard/dashboard-page.tsx`: replace the current `grid-cols-1 lg:grid-cols-[minmax(0,1fr)_380px]` two-column grid with a three-column grid sized per the mockup's proportions (e.g. `lg:grid-cols-[320px_minmax(0,1fr)_420px]`), give the outer row a bounded height (`h-screen`/`overflow-hidden`) and each column `h-full overflow-y-auto` so only that column scrolls; move `client_header.client_name`/`days_to_renewal` out of the existing top header row into the new column 1, rendered above a new `<AuraRiskOrb score={data.score_block?.score} band={data.score_block?.band} />`; keep the decorative "Last 30 days"/"Live"/bell row spanning the full width above the three columns (research.md Decision 5) (depends on T004, T006)
- [X] T008 [US1] In `frontend/src/dashboard/dashboard-page.tsx`, move the existing `NarratorPanel`, `StakeholderCards`, and `CoverageLine` blocks (unchanged components/props) to render after `PulseTimeline` inside column 2's container (research.md Decision 4, FR-019) — no edits to `narrator-panel.tsx`, `stakeholder-cards.tsx`, or `coverage-line.tsx` themselves (depends on T007)
- [X] T009 [US1] In the same file, verify the `lg:` breakpoint that collapsed the old two-column grid to one stacked column still collapses the new three-column grid the same way; adjust the breakpoint/stacking classes if the new column count changes the collapse point (FR-018) (depends on T007)

**Checkpoint**: Three columns are visible and independently scrollable; column 1 shows title + orb; column 2 hosts Signal Stream + Narrator/Stakeholders/Coverage; column 3's content is unchanged, only relocated.

---

## Phase 4: User Story 2 - Read churn risk at a glance from the enhanced overview (Priority: P2)

**Goal**: The score renders large and band-colored; the trend chart shows a `%`-labeled Y axis and a sequence-labeled X axis without hovering (FR-009, FR-010).

**Independent Test**: Open the dashboard for an account with score history; confirm the score is large and colored by band, and the chart's axis labels are visible without any hover interaction.

### Tests for User Story 2

- [X] T010 [P] [US2] Update `frontend/src/dashboard/score-block.test.tsx`: assert the chart renders visible `XAxis` sequence-index tick labels and `YAxis` tick labels suffixed with `%` (replacing today's hidden-`YAxis`/no-`XAxis` assertions), and assert the score element carries a larger/prominent size class than before

### Implementation for User Story 2

- [X] T011 [US2] Modify `frontend/src/dashboard/score-block.tsx`: add `<XAxis dataKey="index" tick={{ fontSize: 10 }} />`; change `<YAxis domain={['dataMin','dataMax']} hide />` to a visible axis with `tickFormatter={(v) => \`${v}%\`}`; increase the score number's size/weight classes for the "large, prominent" treatment (research.md Decision 7, FR-009) (depends on T003, T010)
- [X] T012 [US2] Adjust `frontend/src/dashboard/churn-risk-overview-card.tsx`'s spacing/padding around `<ScoreBlock>` so the larger score treatment from T011 doesn't crowd the "Top risk drivers" section beneath it (depends on T011)

**Checkpoint**: Score and trend read at a glance; both axes are labeled.

---

## Phase 5: User Story 3 - Scan the Signal Stream by real signal type and severity (Priority: P3)

**Goal**: Each Signal Stream entry shows a dual-channel icon (shape = real `event_type`, color/ring = `severity`), a type label, and a connecting timeline line; `event_type` is surfaced end-to-end from the database, through the API, to the frontend (FR-005, FR-005a, FR-006, FR-007, FR-008).

**Independent Test**: Seed events of at least two `event_type` values at two severities; confirm each Signal Stream entry's icon shape matches its real type and its ring color matches its severity, independently of each other, connected by a visible line.

### Tests for User Story 3

- [X] T013 [P] [US3] Update `backend/tests/unit/test_dashboard_route.py`: add `assert event["event_type"] in {"message", "ticket_state_change", "usage_measurement", "survey_response", "meeting", "absence", "crm_change"}` alongside the existing `severity` assertion (contracts/dashboard.md)
- [X] T014 [P] [US3] Create `frontend/src/dashboard/signal-type.test.ts`: assert `TYPE_LABEL` and `TYPE_ICON` each have exactly the 7 `SignalType` keys, with a distinct label and a distinct icon component per key
- [X] T015 [P] [US3] Update `frontend/src/dashboard/pulse-timeline.test.tsx`: assert two entries with the same `severity` but different `event_type` render different icon shapes; assert two entries with the same `event_type` but different `severity` render different ring colors; assert a connecting line element is present between consecutive entries

### Implementation for User Story 3 — backend chain (data-model.md table, in dependency order)

- [X] T016 [P] [US3] Modify `backend/app/experience/application/ports.py`'s `PulseEventRecord` dataclass: add `event_type: str` field
- [X] T017 [US3] Modify `backend/app/experience/adapters/sqlalchemy_repository.py`'s `SqlAlchemyPulseEventReader.list_recent`: add `e.event_type` to both the inner and outer `SELECT` lists, and `event_type=r.event_type` when constructing `PulseEventRecord` (depends on T016)
- [X] T018 [US3] Modify `backend/app/experience/application/use_cases.py`: add `event_type: str` to `PulseEventResult`; in `execute()`'s `pulse_timeline` comprehension, pass `event_type=p.event_type` through unchanged (depends on T016, T017)
- [X] T019 [US3] Modify `backend/app/experience/adapters/dashboard_router.py`'s `PulseEvent(BaseModel)`: add `event_type: str` field (depends on T018, T013)
- [X] T020 [P] [US3] Update `architecture/07-api-spec.md`'s `PulseEvent` OpenAPI schema: add `event_type: { type: string, enum: [message, ticket_state_change, usage_measurement, survey_response, meeting, absence, crm_change] }` (constitution's "fix stale docs everywhere" rule)

### Implementation for User Story 3 — frontend

- [X] T021 [P] [US3] Modify `frontend/src/dashboard/types.ts`: add the `SignalType` union type and `event_type: SignalType` field on `PulseEvent` (data-model.md)
- [X] T022 [US3] Create `frontend/src/dashboard/signal-type.ts` exporting the closed `TYPE_LABEL: Record<SignalType, string>` and `TYPE_ICON: Record<SignalType, LucideIcon>` maps (Mail, Ticket, BarChart3, ClipboardList, Calendar, UserX, Building2 from `lucide-react`) (data-model.md) (depends on T021, T014)
- [X] T023 [US3] Modify `frontend/src/dashboard/pulse-timeline.tsx`: icon glyph becomes `TYPE_ICON[event.event_type]` (shape), ring/color remains `SEVERITY_RING_CLASS[event.severity]` (FR-005a); render the type label (`TYPE_LABEL[event.event_type]`) next to the relative-time text (FR-005); add a connecting vertical line between consecutive `<li>` entries (FR-007) (depends on T022, T015)

**Checkpoint**: Signal Stream entries show real type + severity via a dual-channel icon, connected by a timeline line; backend, API contract, and docs are consistent end-to-end.

---

## Phase 6: User Story 4 - Converse with AURA from an always-ready docked panel (Priority: P4)

**Goal**: The Assistant renders already expanded, docked in column 1 below the orb — no launcher, no collapse state (FR-004).

**Independent Test**: Load `/dashboard`; confirm the Assistant is expanded and can accept a message with zero additional clicks, positioned below the AURA orb, without obscuring columns 2 or 3.

### Tests for User Story 4

- [X] T024 [P] [US4] Update `frontend/src/ask/ask-bar.test.tsx`: replace the launcher/collapsed-by-default assertions with "renders expanded immediately on mount, no launcher button present" assertions; keep the existing idle/thinking/answered and conversation-persistence-across-rerender assertions unchanged

### Implementation for User Story 4

- [X] T025 [US4] Modify `frontend/src/ask/ask-bar.tsx`: remove the `isOpen` state and the launcher-button branch entirely; always render the expanded panel content; change the outer container from `fixed right-6 bottom-6 z-40 ...` to an in-flow docked shell (e.g. `flex h-full flex-col`) that fills the remaining height of column 1 beneath the orb, keeping the message area `overflow-y-auto` (depends on T024)
- [X] T026 [US4] Modify `frontend/src/dashboard/dashboard-page.tsx`: move `<AskBar ... />` from its current overlay-sibling position into column 1's JSX, directly below `<AuraRiskOrb />` (depends on T007, T025)

**Checkpoint**: The Assistant is docked, expanded on load, and usable immediately in column 1.

---

## Phase 7: User Story 5 - Open item details in an elegant modal with clear selectable affordance (Priority: P5)

**Goal**: Selecting a Signal Stream entry or Action & Draft Hub item opens a single, centered, accessible modal (replacing the right-docked panel); hovering any selectable item shows a smooth affordance (FR-012, FR-013, FR-014, FR-016).

**Independent Test**: Hover a Signal Stream entry and an Action & Draft Hub item and confirm a smooth affordance; select an item and confirm a centered modal opens with the same content as today's side panel; trigger the Draft Composer while Evidence is open and confirm Evidence closes first.

### Tests for User Story 5

- [X] T027 [P] [US5] Create `frontend/src/components/ui/dialog.test.tsx`: assert `Dialog`/`DialogContent` render centered content over a backdrop, close on the Esc key and on backdrop click, and trap focus within the content while open
- [X] T028 [P] [US5] Update `frontend/src/evidence/evidence-panel.test.tsx`: assert the content now renders inside a centered `DialogContent` with `role="dialog"` (not the old right-docked markup); existing data/interaction assertions unchanged
- [X] T029 [P] [US5] Update `frontend/src/draft-composer/draft-composer-panel.test.tsx`: same centered-`DialogContent` assertion; existing data/interaction assertions unchanged
- [X] T030 [P] [US5] Update `frontend/src/dashboard/dashboard-page.test.tsx` (same file as T004): assert opening the Draft Composer while the Evidence modal is open closes Evidence first, and vice versa (research.md Decision 3 — at most one modal at a time)
- [X] T031 [P] [US5] Update `frontend/src/dashboard/pulse-timeline.test.tsx` and `frontend/src/dashboard/action-draft-hub.test.tsx`: assert each selectable item's icon/container carries a hover/focus affordance class (FR-012)

### Implementation for User Story 5

- [X] T032 [US5] Create `frontend/src/components/ui/dialog.tsx`: a minimal `Dialog`, `DialogContent`, `DialogOverlay`, `DialogClose` wrapper over `@radix-ui/react-dialog` (research.md Decision 2), centered layout, using Radix's built-in focus trap and Esc handling (depends on T002, T027)
- [X] T033 [US5] Modify `frontend/src/evidence/evidence-panel.tsx`: replace the hand-rolled `fixed inset-0 ... flex justify-end` markup with `Dialog`/`DialogContent` (T032), keeping all existing inner content and hooks (`useEvidence`, `useFeedback`) unchanged (depends on T032, T028)
- [X] T034 [US5] Modify `frontend/src/draft-composer/draft-composer-panel.tsx`: same `Dialog`/`DialogContent` conversion, keeping all existing inner content and hooks unchanged (depends on T032, T029)
- [X] T035 [US5] Modify `frontend/src/dashboard/dashboard-page.tsx`: add `openEvidence`/`openDraftComposer` helper functions that clear the other modal's state before setting the new one (data-model.md's "Modal state" section, research.md Decision 3); wire `PulseTimeline`'s `onSelect`, `ActionDraftHub`'s `onSelect`, and `AskBar`'s `onOpenEvidence`/`onOpenDraftComposer` callbacks through these helpers instead of the raw setters (depends on T007, T026, T030, T033, T034)
- [X] T036 [P] [US5] Modify `frontend/src/dashboard/pulse-timeline.tsx` and `frontend/src/dashboard/action-draft-hub.tsx`: add a smooth hover/focus transition on each item's icon and container (e.g. `transition-transform hover:scale-105` on the icon wrapper, extending the existing `hover:border-neutral-300` treatment consistently to both components) (FR-012) (depends on T031, T023)

**Checkpoint**: Selecting any item opens a single, centered, accessible modal; hovering any selectable item shows a smooth affordance.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Full regression pass and the FR-015 scope guard.

- [X] T037 [P] Run `pnpm typecheck && pnpm lint && pnpm test && pnpm test:e2e` in `frontend/`, and `pytest backend/tests/unit/test_dashboard_route.py` in `backend/` — all must pass. DONE for typecheck/lint/test/pytest (all green; one pre-existing, unrelated failure — see final report). `test:e2e` could NOT be run — no browser automation tool was available in this sandboxed session; `frontend/e2e/dashboard-redesign.spec.ts` was updated to match the new always-expanded docked assistant behavior (FR-004) so it's correct for the next run, but was not itself executed.
- [X] T038 Manual visual check per `quickstart.md` against `base/mockup-mainPage-v2.jpg` for all five user stories, on both a `normal`-state and a `healthy_quiet`-seeded account (FR-017 regression). PARTIAL — no browser automation tool was available in this sandboxed session, so no live screenshot comparison was possible; verified instead via careful code review against the mockup image and the full component/test suite. See final report for what to re-check visually.
- [X] T039 Run `git diff --stat`; confirm no diff under `backend/app/scoring/`, `backend/app/ledger/`, or any field on `DashboardResponse` other than the additive `pulse_timeline[].event_type` (FR-015). CONFIRMED — no diff under either path; `DashboardResponse`'s only field-shape change is the additive `pulse_timeline[].event_type`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS US1 (T006) and US2 (T011)
- **User Story 1 (Phase 3)**: Depends on Foundational (T003) — no dependency on other stories; this is the structural shell every other story's content sits inside
- **User Story 2 (Phase 4)**: Depends on Foundational (T003) only — independently testable against today's two-column layout if run before US1, though in practice runs after US1 since both land on `dashboard-page.tsx`/`score-block.tsx`
- **User Story 3 (Phase 5)**: Depends on nothing but Setup — the backend chain (T016-T020) and `types.ts`/`signal-type.ts` (T021-T022) have no dependency on US1's layout; `pulse-timeline.tsx` itself already exists in column 2 regardless of which grid wraps it
- **User Story 4 (Phase 6)**: Depends on US1 (T007, for column 1 to exist) — the Assistant needs a column to dock into
- **User Story 5 (Phase 7)**: Depends on US1 (T007), US3 (T023, hover affordance shares the icon markup it touches), and US4 (T026, `dashboard-page.tsx`'s modal-wiring task touches the same callbacks US4 passes to `AskBar`)
- **Polish (Phase 8)**: Depends on all five user stories being complete

### Parallel Opportunities

- T001/T002 (Setup) — different concerns, can run together
- T004/T005 (US1 tests), T010 (US2 test), T013/T014/T015 (US3 tests), T024 (US4 test), T027/T028/T029/T030/T031 (US5 tests) — all [P] within their own phase, different files
- T016 (US3, `ports.py`) and T021 (US3, `types.ts`) can start together — one is backend, one is frontend, neither depends on the other
- T020 (architecture doc) can be written any time after Decision 1 (research.md) is settled — no code dependency
- US3 (Phase 5) can be developed in parallel with US1/US2 (Phases 3-4) by a different contributor, since none of its files (`ports.py`, `sqlalchemy_repository.py`, `use_cases.py`, `dashboard_router.py`, `types.ts`, `signal-type.ts`, `pulse-timeline.tsx`) are touched by US1 or US2 — only US5's hover-affordance task (T036) later depends on US3's `pulse-timeline.tsx` changes landing first

---

## Parallel Example: User Story 3 (backend + frontend split)

```bash
# Backend chain (one contributor):
Task: "Add event_type to PulseEventRecord in backend/app/experience/application/ports.py"
# then sequentially: sqlalchemy_repository.py -> use_cases.py -> dashboard_router.py -> architecture/07-api-spec.md

# Frontend chain (a second contributor, in parallel):
Task: "Add SignalType and event_type to frontend/src/dashboard/types.ts"
# then: signal-type.ts -> pulse-timeline.tsx (waits for backend's dashboard_router.py to confirm the field name/shape before final integration test)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (T003 — blocks US1's orb)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: `pnpm test src/dashboard/dashboard-page.test.tsx src/dashboard/aura-risk-orb.test.tsx`; visually confirm the three-column shell against the mockup
5. This alone delivers the layout every other story enhances — a real, demoable increment even before the chart, signal-stream, assistant, and modal upgrades land

### Incremental Delivery

1. Setup + Foundational → shared infrastructure ready
2. US1 → validate → three-column shell in place (MVP!)
3. US2 → validate → score/chart read at a glance
4. US3 → validate → Signal Stream shows real type + severity
5. US4 → validate → Assistant docked and ready
6. US5 → validate → modal + hover affordance complete
7. Polish → full regression + FR-015 scope guard

### Parallel Team Strategy

With multiple developers, after Phase 1-2:
- Developer A: US1 → then US4 (US4 depends on US1's column 1)
- Developer B: US3 (independent of US1's layout entirely) → then helps with US5's hover affordance once US1/US3 have landed
- Developer C: US2 (independent once T003 lands)
- US5 is last regardless of staffing, since it depends on US1, US3, and US4 all being in place

---

## Notes

- [P] tasks = different files, no dependency on an incomplete task
- [Story] label maps task to specific user story for traceability
- This is a forward plan — none of T001-T039 are implemented yet
- Commit boundary suggestion: one commit per user story phase (matching the Checkpoint after each), plus a final Polish commit for T037-T039
- Avoid: vague tasks, same-file conflicts within a phase, cross-story dependencies that break independent testability beyond what's declared above
