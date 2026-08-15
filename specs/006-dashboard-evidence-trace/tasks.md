# Tasks: Dashboard Evidence Trace

**Input**: Design documents from `specs/006-dashboard-evidence-trace/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`,
`quickstart.md`

**Tests**: `plan.md`'s Testing section commits to a specific test suite (per-route
real-DB tests, pure domain-service tests for the state precedence and evidence
dispatch table, frontend component tests, one new E2E spec) — included below,
scoped to exactly what `spec.md`'s acceptance scenarios require, not a broader
TDD suite beyond that.

**Organization**: Tasks are grouped by user story — US1 Score/contributions/pulse
(P1), US2 Evidence trace panel (P1), US3 Coverage line + system health (P2), US4
Stakeholder cards (P2), US5 State banners (P3) — per `plan.md`'s Project
Structure. All five build on one shared foundation (the state-precedence
function and the six new ports) but are independently testable per `spec.md`'s
own "Independent Test" for each story; several tasks across stories share one
file (`app/experience/{domain/services.py,adapters/sqlalchemy_repository.py,
application/use_cases.py}`, `dashboard_router.py`, `dashboard-page.tsx`) and are
marked `[P]` only where they touch independent regions with no dependency on an
incomplete task, the same discipline features 004/005 already applied.

**Note**: T007 and T012 (renewal_date wiring) and the fallback additions to
T021/T025/T026 were added during `/speckit-analyze` remediation (findings CV2
and CV1) — every other task keeps its original scope.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1/US2/US3/US4/US5
- Every task names an exact file path from `plan.md`'s Project Structure

---

## Phase 1: Setup

- [X] T001 Create the `backend/app/experience/domain/` package skeleton
      (`__init__.py`, empty `entities.py`/`services.py`) — this module's first
      domain ring; feature 002 needed none, being a pure passthrough
      (`plan.md`'s Structure Decision)
- [X] T002 [P] Create `backend/tests/experience/__init__.py`
- [X] T003 [P] Create frontend feature folders `frontend/src/evidence/` and
      `frontend/src/coverage/` with `.gitkeep` (matching the existing empty-stub
      convention, e.g. `frontend/src/ask/.gitkeep`)

**Checkpoint**: Package skeleton ready.

---

## Phase 2: Foundational

**Purpose**: The state-precedence logic and reader-owned ports every user
story's dashboard-rendering work depends on knowing the shape of.

**CRITICAL**: No user story task can begin until this phase is complete.

- [X] T004 [P] Define domain value objects in
      `backend/app/experience/domain/entities.py` — `DashboardState`,
      `PulseSeverity`, `EvidenceComparison`, `ArithmeticClause` (`data-model.md`)
- [X] T005 [P] Implement the state-precedence pure function
      `resolve_dashboard_state()` in `backend/app/experience/domain/services.py`
      (depends on T004) — takes pre-computed boolean/count flags (no current
      profile, any source disconnected, an unresolved-person count ≥ 3, any
      source degraded, connected-signal-type count, healthy band with zero
      contributions) and returns the real `DashboardState` per `research.md`'s
      seven-value precedence table; pure, no I/O, callable before any real port
      exists
- [X] T006 [P] Define the six new reader-owned ports in
      `backend/app/experience/application/ports.py` (depends on T004 for entity
      types) — `ScoreReadPort`, `FindingReadPort`, `PulseEventPort`,
      `StakeholderReadPort`, `CoveragePort`, `IdentityGapPort` — reader-owned,
      no cross-module adapter import (`research.md`'s Decision)
- [X] T007 Extend feature 002's `ClientProfileRecord`/`ClientProfileRepositoryPort`
      in `backend/app/experience/application/ports.py` (same file as T006,
      sequential) — add `renewal_date: date` to `ClientProfileRecord`, the only
      source `ClientHeader.days_to_renewal` has (`research.md`'s Decision,
      `/speckit-analyze` finding CV2 — not a new port, extending the existing
      one)
- [X] T008 [P] Write
      `backend/tests/experience/test_state_and_evidence_services.py` (depends
      on T005) — `resolve_dashboard_state()`'s precedence ordering for all
      seven states, including the two-preconditions-true case (`no_profile` >
      `source_down` > `unresolved_person` > `catching_up` > `learning` >
      `healthy_quiet` > `normal`)

**Checkpoint**: Foundation ready — user story work can now begin.

---

## Phase 3: User Story 1 - The score, its causes, and the recent pulse are real, not a shell (Priority: P1)

**Goal**: `GET /api/dashboard` renders real `score_block`/`contribution_bars`/
`pulse_timeline` from `score_runs`/`score_contributions`/cited `events` —
replacing feature 002's permanent shell.

**Independent Test**: `quickstart.md` §1.

### Implementation for User Story 1

- [X] T009 [P] [US1] Implement `SqlAlchemyScoreReader` in
      `backend/app/experience/adapters/sqlalchemy_repository.py` — implements
      `ScoreReadPort` (T006): latest `score_runs` row; last-14-days one-point-
      per-day trend (`research.md`'s Decision — the day's actual last score,
      not an average); a `score_contributions` row by ID joined to its
      finding's `finding_type`
- [X] T010 [P] [US1] Implement `SqlAlchemyPulseEventReader` in the same file as
      T009 (sequential) — implements `PulseEventPort` (T006): validated
      `score_contributions` within the 14-day window, joined to their
      findings' cited events
- [X] T011 [US1] Implement `pulse_severity()` in
      `backend/app/experience/domain/services.py` (same file as T005,
      sequential) — `info`/`at_risk`/`watch` per `research.md`'s finding-type
      mapping (reuses FR-012's own red/amber rule verbatim)
- [X] T012 [P] [US1] Extend `SqlAlchemyClientProfileRepository.get_current()` in
      `backend/app/experience/adapters/sqlalchemy_repository.py` (same file as
      T009/T010, sequential; depends on T007) — `SELECT` now includes
      `renewal_date` (`research.md`'s Decision, `/speckit-analyze` finding CV2)
- [X] T013 [US1] Implement `GetDashboardUseCase` in
      `backend/app/experience/application/use_cases.py` (depends on T005, T009,
      T010, T011, T012) — supersedes `GetDashboardShellUseCase`; assembles
      `client_header` (including `band` echoed from `score_block.band` and
      `days_to_renewal` computed from T012's `renewal_date`), `score_block`,
      `contribution_bars`, `pulse_timeline`, computes `state` via
      `resolve_dashboard_state()` for the `healthy_quiet`/`normal` distinction
      (the `source_down`/`catching_up`/`unresolved_person`/real `learning`
      flags are wired in US5 — `false`/full-coverage defaults here)
- [X] T014 [US1] Extend `backend/app/experience/adapters/dashboard_router.py`
      (depends on T013) — full `DashboardResponse` shape for `normal`/
      `healthy_quiet` states (`contracts/dashboard.md`)
- [X] T015 [P] [US1] Extend `backend/tests/unit/test_dashboard_route.py`
      (depends on T014) — real-DB test asserting `score_block`/
      `contribution_bars`/`pulse_timeline` match this deployment's real worked
      example (`data-model.md`'s ticket #456/39.0-points row), `client_header.
      days_to_renewal` is a real computed integer, `healthy_quiet` rendering
      (FR-004)
- [X] T016 [P] [US1] Implement `frontend/src/dashboard/score-block.tsx` —
      score, band pill, inline SVG trend, REQ-M8-03's animate-from-previous-
      value behavior
- [X] T017 [P] [US1] Implement `frontend/src/dashboard/contribution-bars.tsx`
      — positive (green) vs. negative styling, applying FR-012's red-only-for-
      broken-promise/disengaged-sponsor rule (same rule T011 implements for
      pulse severity — not a naive "negative = red"); click handler stubbed
      (wired to the evidence panel in US2)
- [X] T018 [P] [US1] Implement `frontend/src/dashboard/pulse-timeline.tsx` —
      severity dot, client-quoted text in the serif typeface (REQ-M8-04)
- [X] T019 [US1] Extend `frontend/src/dashboard/dashboard-page.tsx` (depends
      on T016, T017, T018) — wires the three components, renders
      `healthy_quiet`'s "Nothing needs you today" message in place of the
      normal set (REQ-M8-05)
- [X] T020 [P] [US1] Extend `frontend/src/dashboard/dashboard-page.test.tsx`
      (depends on T019) — one test per rendered state (`normal`,
      `healthy_quiet`)

**Checkpoint**: Dashboard shows real score/contribution/pulse data,
independently verified.

---

## Phase 4: User Story 2 - Every number opens to its proof (Priority: P1)

**Goal**: `GET /api/evidence/{score_contribution_id}` returns a real
comparison/what-changed/quoted-messages/arithmetic-explanation for any
contribution; the frontend opens it from every clickable number.

**Independent Test**: `quickstart.md` §2.

### Implementation for User Story 2

- [X] T021 [P] [US2] Implement the evidence dispatch table in
      `backend/app/experience/domain/services.py` (same file as T005/T011,
      sequential) — one pure function per `finding_type`
      (`evaluate_commitment_evidence`, `evaluate_usage_evidence`,
      `evaluate_absence_evidence`, `evaluate_relationship_evidence`,
      `evaluate_recurrence_evidence`), each returning an `EvidenceComparison`
      (T004); plus `evaluate_generic_evidence()` — the fallback for any
      `finding_type` outside those five (`research.md`'s Decision,
      `/speckit-analyze` finding CV1: this deployment's own real, validated
      `score_contributions` already include `escalation_language`/
      `tone_deterioration`/`csat_deviation`, finding types feature 007's
      readers will eventually own — the dispatch must not raise for them);
      plus `format_arithmetic()` — one `ArithmeticClause` per non-neutral
      `score_contributions` factor, skipping neutral ones (`data-model.md`'s
      dispatch table, `research.md`'s "skip neutral factors" rule) — this
      function is finding-type-agnostic, unaffected by the fallback case
- [X] T022 [P] [US2] Extend `backend/app/experience/adapters/
      sqlalchemy_repository.py` (same file as T009/T010/T012, sequential) —
      resolve a finding's cited events (decrypted body where present,
      `structured_payload`), join `response_pairs`/`rollups` for the
      Commitment/Usage dispatch cases (implements the read side of
      `FindingReadPort`, T006)
- [X] T023 [US2] Implement `GetEvidenceTraceUseCase` in
      `backend/app/experience/application/use_cases.py` (same file as T013,
      sequential; depends on T021, T022) — dispatches by `finding_type` via
      T021 (falling back to `evaluate_generic_evidence()` for an
      unrecognized type), assembles the full `EvidenceTraceResponse`, raises a
      not-found error for an unresolvable ID
- [X] T024 [US2] Implement
      `backend/app/experience/adapters/evidence_router.py` (depends on T023) —
      `GET /api/evidence/{score_contribution_id}`, `404` on not-found
      (`contracts/evidence.md`)
- [X] T025 [P] [US2] Extend
      `backend/tests/experience/test_state_and_evidence_services.py` (same
      file as T008, sequential; depends on T021) — T021's dispatch table
      against `data-model.md`'s worked values for all five finding types, plus
      `evaluate_generic_evidence()`'s fallback output for an unrecognized
      `finding_type` (`/speckit-analyze` finding CV1), plain values, no DB
- [X] T026 [P] [US2] Write `backend/tests/unit/test_evidence_route.py`
      (depends on T024) — real-DB test reproducing `data-model.md`'s worked
      example (ticket #456, 39.0 points, criticality/recency-only arithmetic),
      the `404` case, and the fallback response for a real
      `escalation_language`/`tone_deterioration`/`csat_deviation` contribution
      already present in the seeded database (`/speckit-analyze` finding CV1)
- [X] T027 [P] [US2] Implement `frontend/src/evidence/use-evidence.ts` —
      TanStack Query hook for `GET /api/evidence/{id}`
- [X] T028 [US2] Implement `frontend/src/evidence/evidence-panel.tsx` (depends
      on T027) — client-side overlay (`research.md`'s Decision — no route
      change), comparison/what-changed/quoted-messages/arithmetic sections,
      serif client quotes
- [X] T029 [US2] Wire click-through on score/contribution bars/pulse events in
      `frontend/src/dashboard/dashboard-page.tsx` (same file as T019,
      sequential; depends on T028, T019) — opens T028's panel (FR-007)
- [X] T030 [P] [US2] Write `frontend/src/evidence/evidence-panel.test.tsx`
      (depends on T028)
- [X] T031 [US2] Write `frontend/e2e/dashboard-to-evidence.spec.ts` (path
      corrected during implementation — `frontend/e2e/`, matching feature
      002's already-configured `playwright.config.ts` `testDir`, not
      `frontend/src/e2e/` as first planned) (depends on T029) — click a real
      contribution bar, a real pulse event, and the score number in turn,
      confirming each opens the evidence panel with real cited-message text
      (SC-002's "verified for at least one real instance of each component
      type" — not contribution bars alone)

**Checkpoint**: Every number opens to its proof, independently verified —
this feature's namesake complete.

---

## Phase 5: User Story 3 - A quiet score can be trusted, or explained, at a glance (Priority: P2)

**Goal**: The dashboard's coverage line and a dedicated system health screen
(`GET /api/coverage`) show real per-source status and an honestly-empty
quarantine list.

**Independent Test**: `quickstart.md` §3.

### Implementation for User Story 3

- [X] T032 [P] [US3] Implement `SqlAlchemyCoverageReader` in
      `backend/app/experience/adapters/sqlalchemy_repository.py` (same file,
      sequential) — implements `CoveragePort` (T006): `sources`' status/
      `last_successful_sync_at`, the latest `coverage_reports` row, a
      `source_type` → six-signal-type grouping (Tickets/Email/Chat/Product
      usage/Surveys/Meetings, `research.md`), quarantine (always empty —
      feature 007's `ValidationGate` doesn't exist yet)
- [X] T033 [US3] Extend `GetDashboardUseCase` in
      `backend/app/experience/application/use_cases.py` (same file as
      T013/T023, sequential; depends on T032) — adds `coverage_line`
- [X] T034 [US3] Implement `GetCoverageUseCase` in the same file as T033
      (sequential; depends on T032) — assembles `CoverageResponse`
- [X] T035 [US3] Implement
      `backend/app/experience/adapters/coverage_router.py` (depends on T034) —
      `GET /api/coverage` (`contracts/coverage.md`)
- [X] T036 [P] [US3] Write `backend/tests/unit/test_coverage_route.py`
      (depends on T035) — real per-source status, empty quarantine list
- [X] T037 [P] [US3] Implement `frontend/src/dashboard/coverage-line.tsx`,
      wire into `frontend/src/dashboard/dashboard-page.tsx` (same file as
      T019/T029, sequential; depends on T033)
- [X] T038 [US3] Implement `frontend/src/coverage/coverage-page.tsx` (depends
      on T035) — the dedicated system health screen
- [X] T039 [US3] Add the `/coverage` route in `frontend/src/App.tsx` (depends
      on T038)

**Checkpoint**: A quiet score can be trusted or explained, independently
verified.

---

## Phase 6: User Story 4 - The cast of stakeholders is visible, including who's gone quiet (Priority: P2)

**Goal**: Every profiled stakeholder renders as a card with real activity
status; `tone_trajectory` is honestly `unknown`.

**Independent Test**: `quickstart.md` §4.

### Implementation for User Story 4

- [X] T040 [P] [US4] Implement `SqlAlchemyStakeholderReader` in
      `backend/app/experience/adapters/sqlalchemy_repository.py` (same file,
      sequential) — implements `StakeholderReadPort` (T006): current profile
      stakeholders, each one's most recent real ledger activity, `active`
      (within 4 weeks) vs. `quiet`, reusing `RelationshipReader`'s existing
      `_WINDOW_DAYS = 28` constant (feature 005, `research.md`'s Decision) —
      not a new window
- [X] T041 [US4] Extend `GetDashboardUseCase` (same file as T013/T023/T033,
      sequential; depends on T040) — adds `stakeholder_cards`,
      `tone_trajectory` always `"unknown"`
- [X] T042 [P] [US4] Extend `backend/tests/unit/test_dashboard_route.py` (same
      file as T015, sequential; depends on T041) — real profile stakeholders,
      `quiet` vs. `active` status, `unresolved_identity` case
- [X] T043 [P] [US4] Implement `frontend/src/dashboard/stakeholder-cards.tsx`,
      wire into `dashboard-page.tsx` (same file as T019/T029/T037, sequential;
      depends on T041)

**Checkpoint**: The cast of stakeholders is visible, independently verified.

---

## Phase 7: User Story 5 - The screen looks like what's actually true, not a generic loading state (Priority: P3)

**Goal**: `state` renders `source_down`/`catching_up`/`unresolved_person` with
`base/...md` §11.5's exact copy whenever the real precondition holds, by the
fixed precedence.

**Independent Test**: `quickstart.md` §5.

### Implementation for User Story 5

- [X] T044 [P] [US5] Implement `SqlAlchemyIdentityGapReader` in
      `backend/app/experience/adapters/sqlalchemy_repository.py` (same file,
      sequential) — implements `IdentityGapPort` (T006):
      `events.structured_payload->>'participant'` grouped where
      `stakeholder_id IS NULL`, `HAVING count(*) >= 3` (`research.md`'s
      Decision — reuses the `participant` field every ingestion normalizer
      already writes, no new tracking)
- [X] T045 [US5] Wire the full `resolve_dashboard_state()` precedence (T005)
      into `GetDashboardUseCase` (same file as T013/T023/T033/T041,
      sequential; depends on T005, T032, T044, T041) — all seven states real:
      `source_down`/`catching_up` from T032's `sources.status`,
      `unresolved_person` from T044, `learning`'s real "N of 6" from T032's
      signal-type grouping
- [X] T046 [US5] Extend `backend/app/experience/adapters/dashboard_router.py`
      (same file as T014, sequential; depends on T045) — renders each state's
      exact `base/...md` §11.5 copy with its interpolated values (source name,
      minutes, domain, counts)
- [X] T047 [P] [US5] Extend `backend/tests/unit/test_dashboard_route.py` (same
      file as T015/T042, sequential; depends on T046) — one test per state,
      the precedence-conflict case (two preconditions true at once)
- [X] T048 [US5] Extend `frontend/src/dashboard/dashboard-page.tsx` (same file
      as T019/T029/T037/T043, sequential; depends on T046) — renders each
      state's banner
- [X] T049 [P] [US5] Extend `frontend/src/dashboard/dashboard-page.test.tsx`
      (same file as T020, sequential; depends on T048) — one test per state

**Checkpoint**: `quickstart.md` §1–5 all pass — all five user stories
independently functional.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Goal**: Confirm the whole feature against real tooling, not just green tests.

- [X] T050 [P] Run `uv run ruff check .`, `uv run mypy app`, and
      `uv run lint-imports --config ../.importlinter` from `backend/` —
      confirm the existing `global-dependency-rule` contract passes with
      `app.experience`'s new ports/adapters (no config change needed,
      `research.md`)
- [X] T051 [P] Run `pnpm lint` and `pnpm typecheck` from `frontend/` —
      TypeScript strict, no `any` (constitution P11); confirm no chart-library
      import exists anywhere in the component set (SC-004, `/speckit-analyze`
      finding CV5 — grep for a chart-library package name/forbidden component)
- [X] T052 Run all of `specs/006-dashboard-evidence-trace/quickstart.md` end to
      end (including its Automated coverage section), confirm every acceptance
      scenario in `spec.md` passes and `GET /api/dashboard`/`GET /api/evidence/
      {id}` both complete comfortably under 1 second (SC-001/FR-013,
      `/speckit-analyze` finding CV4), and re-run features 001–005's own
      quickstarts to confirm nothing regressed (depends on every task above)

**Checkpoint**: `quickstart.md` §1–5 + Automated coverage all pass — this
feature is complete.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories (every
  story's use case needs `resolve_dashboard_state()`'s signature and the six
  ports, plus `ClientProfileRecord`'s `renewal_date` field, to exist first).
- **User Stories 1–5 (Phases 3–7)**: All depend on Foundational only. US1/US2
  are genuinely independent of each other's *data* (score/contributions vs.
  evidence detail) but US2's evidence panel is wired into US1's rendered
  contribution bars (T029 depends on T019) — the same "reader reads different
  data, but the UI layers on top of the previous story's screen" shape feature
  002's own dashboard-then-nothing-else precedent set. US3/US4/US5 each extend
  the same `GetDashboardUseCase`/`dashboard-page.tsx` files US1 started,
  sequentially, not in parallel with each other on those specific files.
- **Polish (Phase 8)**: Depends on all five user stories being complete.

### Within Each User Story

- Ports' SqlAlchemy adapters before the use case that consumes them; the use
  case before the router; the router before its route test. Frontend:
  components before the page that wires them; the page before its component
  test.
- `app/experience/domain/services.py`, `adapters/sqlalchemy_repository.py`,
  `application/use_cases.py`, `adapters/dashboard_router.py`,
  `tests/unit/test_dashboard_route.py`, and `frontend/src/dashboard/
  dashboard-page.tsx`/`dashboard-page.test.tsx` are each touched by multiple
  stories — every task editing one of these six shared files is sequential
  with every other task editing the same file, regardless of story, the same
  discipline features 004/005 already applied to their own shared files.

### Parallel Opportunities

- T002 and T003 run in parallel with T001 (different files).
- T004 [P] and T006 [P] can proceed once T004 lands (T006 needs T004's entity
  types); T005 [P] also only needs T004. T007 (same file as T006) is
  sequential with it. T008 needs T005.
- Once Foundational lands, US1's port-adapter tasks (T009/T010/T012) and US2's
  domain dispatch table (T021) can all proceed in parallel — different files,
  no cross-story dependency — though US2's `GetEvidenceTraceUseCase` (T023)
  needs `FindingReadPort`'s adapter (T022) which is most naturally written
  alongside US1's own adapter work in the same file.
- US3's port adapter (T032), US4's port adapter (T040), and US5's port adapter
  (T044) can all proceed in parallel once Foundational lands — three
  independent new classes in the same shared adapter file, each reading a
  disjoint set of tables.
- All five stories' frontend leaf component files (`score-block.tsx`,
  `contribution-bars.tsx`, `pulse-timeline.tsx`, `coverage-line.tsx`,
  `stakeholder-cards.tsx`) are `[P]` relative to each other — only the shared
  `dashboard-page.tsx` wiring step per story is sequential.

---

## Implementation Strategy

### MVP First (User Story 1 alone)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3 (User Story 1 — real score/contributions/pulse).
4. **STOP and VALIDATE**: `quickstart.md` §1. The dashboard shows real data for
   the first time — the smallest slice that replaces feature 002's permanent
   shell with something true.

### Incremental Delivery

1. Setup + Foundational → state precedence and ports ready.
2. Add User Story 1 (real dashboard data) → validate independently → the
   shell is retired.
3. Add User Story 2 (evidence trace panel) → validate independently → this
   feature's namesake, REQ-M8-08 satisfied for every rendered number.
4. Add User Story 3 (coverage line + system health screen) → validate
   independently → "healthy vs. we're blind" becomes answerable.
5. Add User Story 4 (stakeholder cards) → validate independently.
6. Add User Story 5 (state banners) → validate independently → all seven
   `state` values render their exact required copy.
7. Polish (Phase 8) → full quickstart + regression pass against features
   001–005.

---

## Notes

- `[P]` tasks touch different files, or independent regions of a shared file,
  with no dependency on an incomplete task.
- Commit after each task or logical group; stop at any checkpoint to validate
  a story independently before continuing.
