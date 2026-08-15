# Tasks: Score Engine

**Input**: Design documents from `specs/004-score-engine/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `quickstart.md`
(no `contracts/` — this feature adds no API route, `spec.md`'s own scope boundary)

**Tests**: Test tasks below cover exactly `spec.md`'s acceptance scenarios (worked-
example reproduction, recency by state, hysteresis/stickiness, the three real
triggers) plus the two property-based tests `tests/strategy.md` already scopes to this
module (reconciliation, monotonicity) — not a broader TDD suite beyond what those
already require.

**Organization**: Tasks are grouped by user story — US1 (P1, the checkpoint itself —
the whole pipeline reproduces the worked example), US2 (P1, evidence ages honestly),
US3 (P1, band never wobbles), US4 (P2, real recomputation triggers) — per `plan.md`'s
Project Structure.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1/US2/US3/US4
- Every task names an exact file path from `plan.md`'s Project Structure

---

## Phase 1: Setup

- [X] T001 Create/verify the `backend/app/scoring/{domain,application,adapters}/`
      package skeleton (`__init__.py` in each — feature 001 scaffolded the top-level
      `scoring/` directory empty; this feature is the first to need the three rings
      inside it)
- [X] T002 [P] Create `demo/fixtures/score-engine-findings.json` — the 9-finding,
      2-issue static fixture from `data-model.md` (reader_type/finding_type/magnitude/
      confidence/stakeholder-or-product-area-key per finding, plus each finding's
      citation strategy — real MVP event, real absence event, or the one synthetic
      CSAT event — and the `iss-A`/`iss-B` groupings)

**Checkpoint**: Package structure ready, fixture shape exists (not yet consumed).

---

## Phase 2: Foundational

**Purpose**: The domain entities and application ports every user story's code depends
on knowing the shape of — `architecture/09-clean-architecture-and-patterns.md`'s
already-named entities/ports for this exact module.

**CRITICAL**: No user story task can begin until this phase is complete.

- [X] T003 [P] Define `Finding`, `Issue`, `ScoreRun`, `ScoreContribution` domain
      entities in `backend/app/scoring/domain/entities.py` (`architecture/09`'s
      pattern catalog — mirrors each table's own columns, `data-model.md`; `Finding.
      state` starts `None`)
- [X] T004 Define `FindingRepositoryPort`, `ScoreRunRepositoryPort`,
      `ClientProfileMultipliersPort`, `DampingRepositoryPort`, `CoverageCheckPort` in
      `backend/app/scoring/application/ports.py` (depends on T003 for the entity
      types these ports return/accept)

**Checkpoint**: Foundation ready — user story work can now begin.

---

## Phase 3: User Story 2 - Evidence ages honestly, not uniformly (Priority: P1)

**Goal**: `open` never fades, `resolved` fades by half-life, `open_overdue` ages up to
a 2.0 cap — each computed independently by finding state.

**Independent Test**: `quickstart.md`'s automated coverage (`test_ageing_calculator.py`
runs standalone, no other domain service needed).

### Implementation for User Story 2

- [X] T005 [P] [US2] Implement `AgeingCalculator` in
      `backend/app/scoring/domain/services.py` — `recency = 1.0` for `open`,
      `0.5^(days_since_resolved / half_life_days)` for `resolved`, `min(1.0 + 0.08 ×
      overdue_ratio, 2.0)` for `open_overdue` (REQ-M6-09..12, REQ-M6-CAL-01/02;
      depends on T003)
- [X] T006 [P] [US2] Write `backend/tests/scoring/test_ageing_calculator.py` —
      asserts exactly 1.0 for `open` at any reference time; exactly 0.5 at one
      half-life and 0.25 at two; exactly 1.30 for ticket #456's 19h-vs-4h case
      (`data-model.md`); the 2.0 cap holds under an extreme overdue ratio (depends on
      T005)

**Checkpoint**: `AgeingCalculator` is correct and independently tested — User Story 1
can now consume it.

---

## Phase 4: User Story 3 - A band label never wobbles on a one-point swing (Priority: P1)

**Goal**: Hysteresis (65 enter / 55 exit for `at_risk`) and 2-consecutive-run
stickiness, evaluated purely from a score and prior `band_history` — no dependency on
how the score itself was computed.

**Independent Test**: `quickstart.md`'s automated coverage
(`test_band_classifier.py` runs standalone against synthetic score/history sequences).

### Implementation for User Story 3

- [X] T007 [US3] Implement `BandClassifier` in
      `backend/app/scoring/domain/services.py` (same file as T005 — sequential, not
      parallel, despite being a different user story) — threshold classification
      (`<35`/`35–65`/`≥65`), hysteresis gap, and the 2-consecutive-run-of-any-trigger
      stickiness rule (REQ-M6-17..19, REQ-M6-CAL-07; depends on T003); when no prior
      `band_history` row exists (the account's first-ever run), the raw
      classification displays immediately with `consecutive_runs_in_band = 1` — there
      is nothing to protect via hysteresis yet (`spec.md`'s Edge Cases)
- [X] T008 [P] [US3] Write `backend/tests/scoring/test_band_classifier.py` — the
      two-week worked example from `sequences/06-state-band-hysteresis.md` (week 0:
      78 → enters `at_risk`; week 1: 61 → stays `at_risk`, since 61 > the 55 exit
      floor); a score newly crossing 65 does not display `at_risk` until a second
      confirming run; the first-ever run (no prior `band_history`) displays its raw
      band immediately (depends on T007)

**Checkpoint**: `BandClassifier` is correct and independently tested — User Story 1
can now consume it.

---

## Phase 5: User Story 1 - The score can be checked by hand against real evidence (Priority: P1) — the checkpoint

**Goal**: The full pipeline — per-finding weight, issue ranking, damping, positive
cap, points→score, stakes — reproduces `examples/01-end-to-end-walkthrough.md` §9's
worked example, corrected for a rank-order inconsistency in that document found
during `/speckit-analyze` (`research.md`): `score = 85.64`, `band = at_risk`.

**Independent Test**: `quickstart.md` §1–2. Depends on User Story 2 (`AgeingCalculator`)
and User Story 3 (`BandClassifier`) already being correct — this is the one place the
"independent stories" framing has a real, narrow exception: this feature's whole point
is a checkpoint that *assembles* the other two, not a fourth independent leaf.

### Implementation for User Story 1

- [X] T009 [US1] Implement `IssueGrouper` in
      `backend/app/scoring/domain/services.py` (same file, sequential; depends on
      T007) — ranks findings within a shared `issue_id` by raw points (`base ×
      influence × criticality × confidence × magnitude`, recency excluded) descending,
      upserts `finding_issue_map.rank_within_issue`, applies the 0.6ⁿ diminishing
      factor (REQ-M6-06..08); one general algorithm, no fixture-specific exception,
      no hardcoded issue IDs — `data-model.md`'s Issue A worked numbers (`fnd-1` 1st,
      `fnd-3` 2nd, `fnd-2` 3rd) are what this correct, general implementation
      produces, which corrects `examples/01` §9.2's own published rank order
      (`research.md`'s Decision: that document's `fnd-2`/`fnd-3` order contradicts
      its own stated ranking rule)
- [X] T010 [US1] Implement `DampingCalculator` in
      `backend/app/scoring/domain/services.py` (same file, sequential; depends on
      T009) — `clamp(0.5^false_alarm_count × 1.15^correct_count, 0, 1.0)`
      (REQ-M6-05, REQ-M6-CAL-03a); always returns the undamped default (1.0) against
      this feature's fixture, since `damping_weights` has no rows yet (`spec.md`'s
      Assumptions)
- [X] T011 [US1] Implement `ScoringCalculator` and `compute_stakes()` in
      `backend/app/scoring/domain/services.py` (same file, sequential; depends on
      T005, T009, T010) — per-finding weight (`base × influence × criticality ×
      confidence × magnitude × recency × damping × rank_within_issue_factor`,
      REQ-M6-01), the 25%-of-negative positive cap (REQ-M6-13/14), the saturating
      points→score conversion (REQ-M6-15/16), and `stakes = contract_value_multiplier
      × renewal_proximity_factor` using this feature's pinned constants (`spec.md`
      FR-012: `strategic`/`standard`/`smb` = 1.5/1.0/0.6, `clamp(2.0 −
      days_until_renewal/90, 0.5, 2.0)`)
- [X] T012 [P] [US1] Implement `SqlAlchemyFindingRepository` in
      `backend/app/scoring/adapters/sqlalchemy_repository.py` (depends on T004) —
      fetch validated findings + their `finding_issue_map` rows, update
      `findings.state` and `finding_issue_map.rank_within_issue`
- [X] T013 [US1] Implement `SqlAlchemyScoreRunRepository` in
      `backend/app/scoring/adapters/sqlalchemy_repository.py` (same file as T012,
      sequential) — persist `score_runs`, `score_contributions`, `band_history`;
      fetch the most recent `band_history` row for hysteresis
- [X] T014 [US1] Implement `SqlAlchemyClientProfileMultipliers`,
      `SqlAlchemyDampingRepository`, `SqlAlchemyCoverageCheck` in
      `backend/app/scoring/adapters/sqlalchemy_repository.py` (same file, sequential)
      — multiplier/`contract_value_band`/`renewal_date` lookups against the current
      profile version, `damping_weights` lookups by `pattern_signature`,
      `coverage_reports.sources_read < sources_expected` existence check
- [X] T015 [US1] Implement `RecomputeScoreUseCase` in
      `backend/app/scoring/application/use_cases.py` (depends on T005, T007, T009,
      T010, T011, T012, T013, T014) — orchestrates: fetch validated findings → derive
      each finding's `state` (`research.md`'s Decision: `broken_response_promise`/
      `commitment_met` mirror the cited `response_pairs.state`, every other type is
      permanently `open`) → `AgeingCalculator` → `IssueGrouper` → `DampingCalculator`
      → `ScoringCalculator` → `BandClassifier` → `compute_stakes` → persist
      everything, recomputed entirely from zero every time (REQ-M6-20)
- [X] T016 [US1] Implement `backend/scripts/seed_score_fixture.py` (depends on T002,
      T012) — reads `demo/fixtures/score-engine-findings.json`, resolves 6 of 9
      citations against real, already-collected MVP-source events, calls
      `DetectAbsenceUseCase.execute()` (feature 003) for a 7th, inserts one synthetic
      `survey_response` event via `AppendEventUseCase` (feature 003) for the 8th/9th
      (CSAT), inserts the 9 `findings` rows (`status = validated`, `state = NULL`)
      and `finding_issue_map` `(finding_id, issue_id)` pairs (no `rank_within_issue`
      yet — `research.md`'s Decision)
- [X] T017 [US1] Implement `backend/scripts/compute_score.py` (depends on T015) —
      manual `RecomputeScoreUseCase` trigger (`trigger = manual`), mirroring
      `scripts/run_collector.py`'s pattern
- [X] T018 [P] [US1] Write `backend/tests/scoring/test_scoring_calculator.py` —
      per-finding formula unit tests against `data-model.md`'s exact values (e.g.
      `fnd-1` = 39.00, `fnd-7` = 9.52), the positive cap applying in full when under
      25% of negative, `stakes`'s worked check (≈1.567 for Meridian's fixture), and
      `spec.md`'s Edge Case for a finding whose product area/stakeholder doesn't
      resolve or whose profile has no `first_response` commitment (`influence`/
      `criticality` default to 1.0) (depends on T011)
- [X] T019 [P] [US1] Write `backend/tests/scoring/test_issue_grouper.py` — rank
      assignment matches `data-model.md`'s documented order for both issues, a
      standalone finding (`fnd-9`) gets `rank_within_issue_factor = 1.000` (depends
      on T009)
- [X] T020 [P] [US1] Write `backend/tests/scoring/test_damping_calculator.py` — the
      exact worked checks from REQ-M6-CAL-03 (one `false_alarm` → 0.500, a second →
      0.250, a subsequent `correct` → 0.2875; `resolved` verdicts never affect
      `weight`) (depends on T010)
- [X] T021 [P] [US1] Write `backend/tests/scoring/test_worked_example.py` — runs
      `scripts/seed_score_fixture.py`'s logic (or an equivalent direct setup) then
      `RecomputeScoreUseCase`, asserts every `score_contributions` row and the final
      `score_runs` totals match `data-model.md`'s corrected numbers to the decimal:
      `total_negative_points = 68.04`, `total_points = 64.04`, `score = 85.64`,
      `band = at_risk` after two consecutive runs; additionally asserts determinism
      (SC-006) directly — recomputing a third time against the same unchanged finding
      state produces a `score_contributions` set equal, row for row, to the second
      run's, not just an equal final score (depends on T015, T016, T017)
- [X] T022 [P] [US1] Write `backend/tests/scoring/test_reconciliation.py` — fills in
      the skipped placeholder (feature 001) for real: property-based (`hypothesis`),
      thousands of generated `findings`/`issues` states,
      `SUM(score_contributions.points_contributed)` reconciles exactly with
      `score_runs.total_negative_points`/`total_positive_points`, every time
      (REQ-NFR-30; depends on T015)
- [X] T023 [P] [US1] Write `backend/tests/scoring/test_monotonicity.py` — fills in
      the skipped placeholder (feature 001) for real: property-based, thousands of
      generated valid `score_runs` states, adding one more validated negative finding
      and recomputing never produces a lower score (REQ-NFR-31, REQ-M6-P4; depends on
      T015)

**Checkpoint**: `quickstart.md` §1–4 pass — User Stories 1, 2, AND 3 all work; the
checkpoint itself (`spec.md`'s whole reason for being) is proven.

---

## Phase 6: User Story 4 - The score recomputes on a schedule and after real context changes (Priority: P2)

**Goal**: The three triggers with a real caller in this feature — `manual` (already
built, T017), `hourly_heartbeat`, `profile_edit_replay` — each produce a real
`score_runs` row; a degraded source freezes the score honestly instead of computing on
an incomplete picture.

**Independent Test**: `quickstart.md` §5–6. Depends on User Story 1 (`RecomputeScoreUseCase` must exist to be triggered).

### Implementation for User Story 4

- [X] T024 [US4] Extend `backend/app/worker.py` — register `RecomputeScoreUseCase` on
      the existing hourly heartbeat (`trigger = hourly_heartbeat`), alongside feature
      003's absence-collector job (REQ-M6-24; depends on T015)
- [X] T025 [US4] Extend `SubmitProfileUseCase` in
      `backend/app/context/application/use_cases.py` (feature 003's file) to call
      `RecomputeScoreUseCase` after `ReplayUseCase.execute()` completes
      (`trigger = profile_edit_replay`), using the newly-current profile version's
      multipliers (REQ-M6-25, REQ-M3-05; depends on T015)
- [X] T026 [US4] Implement the source-degraded freeze check in
      `RecomputeScoreUseCase` (`backend/app/scoring/application/use_cases.py`, same
      file as T015, sequential; depends on T014's `CoverageCheckPort` adapter) — if
      the most recent collector activity shows `sources_read < sources_expected`,
      persist a frozen `score_runs` row (`is_frozen = true`, `source_degraded = true`,
      `score` copied from the prior run) instead of computing fresh (REQ-M6-26,
      REQ-NFR-32); if no prior `score_runs` row exists yet (the account's first-ever
      run), there is nothing to freeze at — compute and persist normally from
      whatever findings are present, still marked `source_degraded = true` for
      visibility (`spec.md`'s Edge Cases)
- [X] T027 [P] [US4] Write `backend/tests/scoring/test_recompute_score_use_case.py`
      (moved next to its sibling scoring tests rather than `tests/unit/` as originally
      filed here — same coverage) —
      each of the three triggers produces a `score_runs` row with the correct
      `trigger` value; a degraded-coverage state produces a frozen, unchanged score;
      explicitly asserts FR-009/REQ-M6-P2 — mutating or deleting the prior
      `score_runs` row's `score` value has no effect on a fresh computation's result,
      confirming `RecomputeScoreUseCase` never reads a prior score as an input
      (depends on T024, T025, T026)

**Checkpoint**: `quickstart.md` §1–6 all pass — all four user stories independently
functional; this feature is complete.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T028 [P] Add a "Score Engine" section to the root `README.md` — how to load the
      fixture and compute a score manually, and a link to
      `specs/004-score-engine/quickstart.md`
- [X] T029 Run all of `specs/004-score-engine/quickstart.md` end to end, confirm every
      acceptance scenario in `spec.md` passes, and re-run features 001–003's own
      quickstarts to confirm nothing regressed (depends on every task above)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories (every
  story's code needs the entity/port shapes to exist first).
- **User Story 2 (Phase 3)** and **User Story 3 (Phase 4)**: Both depend on
  Foundational only — genuinely independent of each other and of User Story 1, pure
  domain-service leaves with no I/O.
- **User Story 1 (Phase 5)**: Depends on Foundational **and** both User Story 2
  (`AgeingCalculator`) and User Story 3 (`BandClassifier`) being complete — this
  feature's one real exception to "independent stories": User Story 1 is the
  checkpoint that assembles the other two, not a fourth independent leaf. (`spec.md`
  itself frames User Story 1 as "the checkpoint itself" — Priority 1 in importance,
  but last in build order among the three P1 stories.)
- **User Story 4 (Phase 6)**: Depends on User Story 1 (`RecomputeScoreUseCase` must
  exist before anything can trigger it) — independent of User Stories 2/3 beyond that
  transitive dependency.
- **Polish (Phase 7)**: Depends on all four user stories being complete.

### Within Each User Story

- Domain (pure logic) before application (use cases) before adapters (routes/repos) —
  except where a domain service depends on an *earlier* domain service's output
  (`IssueGrouper` → `ScoringCalculator`, both in User Story 1).
- Several User Story 1/3/2 tasks share `backend/app/scoring/domain/services.py` — one
  file, five services, deliberately sequential (not parallel) even across different
  user story phases: T005 (`AgeingCalculator`, US2) → T007 (`BandClassifier`, US3) →
  T009 (`IssueGrouper`, US1) → T010 (`DampingCalculator`, US1) → T011
  (`ScoringCalculator`, US1). Similarly `sqlalchemy_repository.py` (T012→T013→T014)
  and `use_cases.py` (T015, then T026 in User Story 4).

### Parallel Opportunities

- T001 and T002 run in parallel.
- T003 runs alone in Foundational (T004 needs it first).
- Once Foundational is done, **User Story 2's T005/T006 and User Story 3's T007/T008
  cannot literally run in parallel with each other** (same file, `services.py`) even
  though they're logically independent stories — pick one order (T005 before T007, as
  numbered, or swap) and let the other user story's *test* task run in parallel with
  the next service implementation instead.
- Within User Story 1: T012 (`SqlAlchemyFindingRepository`) can start as soon as T004
  lands, in parallel with T009/T010/T011's domain-service work (different files). All
  five User Story 1 test tasks (T018–T023 minus whichever depends on T015/T016/T017
  specifically) can run in parallel once their respective implementation task lands.
- T027 (User Story 4's test) is independent once T024/T025/T026 land.
- T028 is independent of everything else in Polish.

---

## Implementation Strategy

### MVP First (User Stories 2 + 3 + 1 — the checkpoint)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3 (User Story 2) and Phase 4 (User Story 3) — both are
   `services.py` edits, so do them in sequence, not literally in parallel, whichever
   order.
4. Complete Phase 5 (User Story 1) — the checkpoint itself.
5. **STOP and VALIDATE**: `quickstart.md` §1–4. This is the actual MVP — the whole
   point of build-order Phase 4 is this checkpoint; User Story 4 (triggers) is
   breadth, not foundation.

### Incremental Delivery

1. Setup + Foundational → entity/port shapes ready.
2. Add User Story 2 + User Story 3 → validate each independently (`test_ageing_
   calculator.py`, `test_band_classifier.py` pass in isolation) → two of the five
   named domain services are proven correct on their own.
3. Add User Story 1 → validate (`quickstart.md` §1–4) → the checkpoint holds: the
   full pipeline reproduces the published worked example to the decimal, reconciles
   exactly, and is provably monotonic across thousands of generated cases.
4. Add User Story 4 → validate (`quickstart.md` §5–6) → the score stays current
   without a human re-running anything, and degrades honestly instead of guessing.
5. Polish (Phase 7) → re-verify features 001–003 still pass, not just this one.

---

## Notes

- `[P]` tasks touch different files with no dependency on an incomplete task.
- This feature's dependency shape is an inverted diamond: User Stories 2 and 3 are
  independent leaves; User Story 1 is the checkpoint that assembles both (plus its own
  new work) rather than a third independent leaf; User Story 4 depends on User Story
  1 alone. Noted explicitly here rather than glossed over, per the same discipline
  applied in features 002/003's `tasks.md` for their own cross-story dependencies.
- Commit after each task or logical group; stop at any checkpoint to validate a story
  independently before continuing.
