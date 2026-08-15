# Tasks: Deterministic Findings

**Input**: Design documents from `specs/005-deterministic-findings/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `quickstart.md`
(no `contracts/` — this feature adds no API route, `spec.md`'s own scope boundary)

**Tests**: Test tasks below cover exactly `spec.md`'s acceptance scenarios (per-
reader worked-example reproduction, the z-score property test REQ-M5-08/SC-004
already scopes to this feature, cache/idempotency, failure isolation) — not a
broader TDD suite beyond what those already require.

**Organization**: Tasks are grouped by user story — US1 Commitment (P1), US2 Usage
+ rollups (P1), US3 Absence (P2), US4 Relationship (P2), US5 Recurrence (P2) — per
`plan.md`'s Project Structure. All five are independent leaves (no user story
depends on another's reader) — unlike feature 004's inverted-diamond shape, this
feature has no single "assembler" story; `RunReadersUseCase` (which SC-001 needs)
is genuinely cross-cutting integration work, placed in the final Polish phase once
all five readers exist, mirroring how `scripts/compute_score.py` was itself a late
step in feature 004.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1/US2/US3/US4/US5
- Every task names an exact file path from `plan.md`'s Project Structure

---

## Phase 1: Setup

- [X] T001 Create the `backend/app/readers/{domain,application,adapters}/`
      package skeleton (`__init__.py` in each — feature 001 scaffolded the
      top-level `readers/` directory empty; this feature is the first to need the
      three rings inside it), plus empty stub files
      `backend/app/readers/application/{tone_reader,intent_reader,meeting_reader,
      validation_gate}.py` (feature 007's future home — `decisions/02-repo-and-
      tooling.md`'s module map, `plan.md`'s Project Structure)
- [X] T002 [P] Add `zendesk-456-created` **and five historical
      `weekly_active_usage` warehouse readings** to `demo/fixtures/meridian-
      week.json`: `zendesk-456-created` — same `ticket_number = 456`, title
      "Slow API response", `state = created`, `occurred_at` earlier in the
      fixture week than the existing `zendesk-456-reopened` item
      (`research.md`'s Decision — needed for Recurrence's real clustering to have
      two related items); `usage-tracking_api-w29`..`w33` — `value_delta_pct`
      readings `-2, 1, -3, 2, -1` at weekly intervals before the existing `w34`
      (`-22`) reading (`research.md`'s Decision, found during `/speckit-analyze`
      — the fixture originally had only one warehouse event, which could never
      clear FR-008's 3-sample abstention floor; `data-model.md`'s worked `fnd-3`
      row has the resulting exact z-score)
- [X] T003 [P] Add `openai` and `hdbscan` to `backend/pyproject.toml`'s
      dependencies (`architecture/03-technology-stack.md`'s already-adopted
      choices — this feature is the first to actually import them)

**Checkpoint**: Package structure ready, fixture gap fixed, dependencies installed.

---

## Phase 2: Foundational

**Purpose**: The `Reader` interface, domain value objects, and ports every user
story's reader depends on knowing the shape of — plus the one adapter every
reader shares (persisting to `findings` and checking the REQ-M5-15 cache).

**CRITICAL**: No user story task can begin until this phase is complete.

- [X] T004 [P] Define the `Reader` abstract interface in
      `backend/app/readers/application/reader.py` —
      `interpret(events: list[Event], context: ClientProfileContext) ->
      list[Finding]`, one method, no template-method base beyond the interface
      itself (`architecture/08-class-diagrams.md`'s already-named pattern;
      `research.md`'s Decision)
- [X] T005 [P] Define reader-owned domain value objects in
      `backend/app/readers/domain/entities.py` — small frozen dataclasses each
      reader's pure decision logic needs (e.g. `ResponsePairInfo` for Commitment,
      `HistoricalSample` for Usage) — `Finding`/`Issue` stay defined once in
      `app.scoring.domain.entities` and are imported here, never redefined
      (constitution P8)
- [X] T006 Define reader-owned ports in `backend/app/readers/application/ports.py`
      — `ResponsePairRepositoryPort`, `RollupRepositoryPort`,
      `AbsenceEventRepositoryPort`, `RelationshipContextPort`, `EmbeddingPort`,
      `CandidateCorpusPort` (fetches `ticket_state_change` titles as Recurrence's
      embedding candidate set — found missing during `/speckit-analyze`),
      `FindingRepositoryPort` (depends on T005 for the entity types these ports
      return/accept; reader-owned per `research.md`'s Decision — no cross-module
      import of `app.ingestion`'s own ports)
- [X] T007 Implement `SqlAlchemyFindingRepository` in
      `backend/app/readers/adapters/sqlalchemy_repository.py` (depends on T006)
      — persists a `Finding` at `status = pending_validation`, and implements the
      REQ-M5-15 cache check (`SELECT 1 FROM findings WHERE reader_type = ? AND
      reader_version = ? AND ? = ANY(cited_event_ids)`, `research.md`'s Decision
      — remember the `(:param)::type` parenthesization SQLAlchemy/asyncpg needs
      for any cast bind param, per feature 004's already-found bug)

**Checkpoint**: Foundation ready — user story work can now begin.

---

## Phase 3: User Story 1 - A broken promise and a kept one both leave a receipt (Priority: P1)

**Goal**: Real `response_pairs` rows become real `broken_response_promise`/
`commitment_met` findings — zero new external dependencies, the lowest-risk reader
to build and verify first.

**Independent Test**: `quickstart.md` §2 (Commitment's two finding types only).

### Implementation for User Story 1

- [X] T008 [P] [US1] Implement the Commitment decision logic in
      `backend/app/readers/domain/services.py` — pure function(s) taking a
      `ResponsePairInfo` (state, `business_hours_elapsed`, `threshold_business_
      hours`), returning `finding_type`/`magnitude`/`confidence` per
      `research.md`'s Decision (`confidence = 1.0` always;
      `magnitude = min(overdue_ratio, 1.0)` for `broken_response_promise`;
      `magnitude = 1.0 − elapsed/threshold` for `commitment_met`, only emitted at
      or under 50% of threshold — FR-004/FR-005) — no I/O, unit-testable with
      plain values (depends on T005)
- [X] T009 [P] [US1] Implement `SqlAlchemyResponsePairRepository` in
      `backend/app/readers/adapters/sqlalchemy_repository.py` (same file as T007,
      sequential) — implements `ResponsePairRepositoryPort` (T006), reading
      `response_pairs` rows the same way feature 004's `resolve_lifecycle`
      already reads them, for a different purpose
- [X] T010 [US1] Implement `CommitmentReader` in
      `backend/app/readers/application/commitment_reader.py` (depends on T004,
      T008, T009) — `interpret()` fetches unresolved/resolved `response_pairs`,
      applies T008's decision logic, checks the REQ-M5-15 cache (T007) before
      emitting each finding
- [X] T011 [P] [US1] Write `backend/tests/readers/test_commitment_reader.py` —
      T008's pure decision logic against `data-model.md`'s worked values (`fnd-1`:
      `magnitude = 1.00`, `confidence = 1.00`; `fnd-9`: `magnitude = 0.50`,
      `confidence = 1.00`), the 50%-threshold boundary for `commitment_met`
      (exactly 50% emits, just over does not), and a `resolved` pair that exceeded
      its threshold before resolving still emits `broken_response_promise`
      (Acceptance Scenario 3) (depends on T008)

**Checkpoint**: Commitment reader complete and independently tested.

---

## Phase 4: User Story 2 - Activity that's actually unusual gets flagged, not activity that's merely different (Priority: P1)

**Goal**: A real rollup/baseline computation (REQ-M2-06, deferred since feature
003) plus a Usage reader that flags only genuine, z-score-defined deviation.

**Independent Test**: `quickstart.md` §3 (rollups populated) + §2 (Usage's finding).

### Implementation for User Story 2

- [X] T012 [P] [US2] Implement the z-score decision logic in
      `backend/app/readers/domain/services.py` (same file as T008, sequential) —
      `z_score(historical_values: list[float], new_value: float) -> float`, pure,
      plus the `|z| > 2` threshold check and minimum-sample-count (3) abstention
      rule (FR-007/FR-008; `research.md`'s Decision) — no I/O
- [X] T013 [US2] Implement `ComputeRollupsUseCase` in
      `backend/app/ingestion/application/use_cases.py` (feature 003's file,
      extended — REQ-M2-06, this feature's first real implementation) — truncates
      and rebuilds `rollups` rows for the metrics/subjects the Usage reader
      consumes, from `events` alone, over a rolling 8-week window (2026-08-14
      clarification), mirroring `ReplayUseCase`'s "truncate + rebuild from
      events" shape
- [X] T014 [P] [US2] Extend `backend/app/ingestion/adapters/
      sqlalchemy_repositories.py` — rollup persistence (write path for T013)
- [X] T015 [P] [US2] Implement `SqlAlchemyRollupRepository` in
      `backend/app/readers/adapters/sqlalchemy_repository.py` (same file as T007/
      T009, sequential) — implements `RollupRepositoryPort` (T006), reading
      `rollups` rows as a plain `list[float]` for a subject/metric (read path for
      the Usage reader, distinct from T014's write path — `research.md`'s
      cross-module port Decision)
- [X] T016 [US2] Implement `UsageReader` in
      `backend/app/readers/application/usage_reader.py` (depends on T004, T012,
      T015) — `interpret()` fetches the relevant rollup via T015, applies T012's
      z-score check, emits `usage_deviation` only on genuine deviation, checks the
      REQ-M5-15 cache (T007)
- [X] T017 [P] [US2] Write `backend/tests/readers/test_usage_reader.py` —
      T012's z-score logic against `data-model.md`'s worked shape (a value within
      2 standard deviations never flags — SC-004), the minimum-sample-count
      abstention (fewer than 3 historical values), and a `hypothesis`
      property test: thousands of generated historical-value lists plus one
      in-range new value never produce a finding (depends on T012)
- [X] T018 [US2] Write `backend/tests/unit/test_compute_rollups_use_case.py` —
      real-DB test confirming `ComputeRollupsUseCase` populates `rollups` from the
      real Meridian fixture's warehouse events over the 8-week window (depends on
      T013, T014)

**Checkpoint**: Usage reader complete, `rollups` populated for real for the first
time, independently tested.

---

## Phase 5: User Story 3 - Missing contact is judged against a real commitment, never a guessed silence window (Priority: P2)

**Goal**: A real `absence`-type ledger event (feature 003's `DetectAbsenceUseCase`
output) becomes a real `contact_absence` finding.

**Independent Test**: `quickstart.md` §2 (Absence's finding).

### Implementation for User Story 3

- [X] T019 [P] [US3] Implement the Absence decision logic in
      `backend/app/readers/domain/services.py` (same file, sequential) —
      `confidence = 0.85` fixed, `magnitude = min(missed_count / 3.0, 1.0)`
      reading the absence event's own `missed_count` payload field
      (`research.md`'s Decision) — no I/O
- [X] T020 [P] [US3] Implement `SqlAlchemyAbsenceEventRepository` in
      `backend/app/readers/adapters/sqlalchemy_repository.py` (same file,
      sequential) — implements `AbsenceEventRepositoryPort` (T006), reading
      `absence`-type events
- [X] T021 [US3] Implement `AbsenceReader` in
      `backend/app/readers/application/absence_reader.py` (depends on T004, T019,
      T020) — `interpret()` reads real `absence`-type events only, never infers a
      silence duration itself (REQ-M5-10), checks the REQ-M5-15 cache (T007)
- [X] T022 [P] [US3] Write `backend/tests/readers/test_absence_reader.py` —
      T019's decision logic against `data-model.md`'s worked value (`fnd-4`:
      `magnitude = 0.67`, `confidence = 0.85`), and confirms no finding is
      emitted when no `absence`-type event exists (Acceptance Scenario 2)
      (depends on T019)

**Checkpoint**: Absence reader complete and independently tested.

---

## Phase 6: User Story 4 - A quietly shrinking cast of stakeholders becomes visible (Priority: P2)

**Goal**: A stakeholder present in the profile but inactive over the rolling
4-week window becomes a real `relationship_change` finding.

**Independent Test**: `quickstart.md` §2 (Relationship's finding).

### Implementation for User Story 4

- [X] T023 [P] [US4] Implement the Relationship decision logic in
      `backend/app/readers/domain/services.py` (same file, sequential) — diffs a
      profile's stakeholder list against a set of ledger-active participant IDs
      over the rolling window, `magnitude = 0.5`/`confidence = 0.7` fixed
      (`research.md`'s Decision, reduced-strength honesty) — no I/O
- [X] T024 [P] [US4] Implement `SqlAlchemyRelationshipContext` in
      `backend/app/readers/adapters/sqlalchemy_repository.py` (same file,
      sequential) — implements `RelationshipContextPort` (T006): the current
      profile's stakeholder list, plus ledger-active participant IDs over a
      rolling 4-week window
- [X] T025 [US4] Implement `RelationshipReader` in
      `backend/app/readers/application/relationship_reader.py` (depends on T004,
      T023, T024) — `interpret()` diffs via T023/T024, cites the stakeholder's
      most recent active event plus any real `absence`-type event for them
      (co-citation expected, `spec.md`'s Edge Cases), checks the REQ-M5-15 cache
      (T007)
- [X] T026 [P] [US4] Write `backend/tests/readers/test_relationship_reader.py` —
      T023's diff logic against `data-model.md`'s worked value (`fnd-5`:
      `magnitude = 0.50`, `confidence = 0.70`), and confirms no finding when every
      profiled stakeholder remains active (Acceptance Scenario 3) (depends on
      T023)

**Checkpoint**: Relationship reader complete and independently tested.

---

## Phase 7: User Story 5 - The same recurring problem is recognized as one story, not several (Priority: P2)

**Goal**: Real OpenAI text embeddings + HDBSCAN clustering recognize ticket
#456's reopening as the same underlying problem as its original creation
(T002's fixture fix) — never a generative guess.

**Independent Test**: `quickstart.md` §2 (Recurrence's finding, two-event
citation per `data-model.md`'s correction).

### Implementation for User Story 5

- [X] T027 [P] [US5] Implement `OpenAIEmbeddingAdapter` in
      `backend/app/readers/adapters/openai_embedding.py` — implements
      `EmbeddingPort.embed(text) -> float[]` via `text-embedding-3-small`
      (`architecture/03-technology-stack.md`); the only file in this module that
      imports `openai` (`.importlinter`'s `readers-application-purity` contract)
- [X] T028 [P] [US5] Implement the Recurrence clustering + decision logic in
      `backend/app/readers/domain/services.py` (same file, sequential) — HDBSCAN
      clustering over vectors (`min_cluster_size = 2`, `research.md`'s Decision),
      `confidence` = HDBSCAN's own per-point membership probability,
      `magnitude = min((cluster_size − 1) / 3.0, 1.0)` — pure over already-
      computed vectors, no I/O beyond the clustering library itself
- [X] T029 [P] [US5] Implement `SqlAlchemyCandidateCorpusRepository` in
      `backend/app/readers/adapters/sqlalchemy_repository.py` (same file,
      sequential) — implements `CandidateCorpusPort` (T006), fetching
      `ticket_state_change` titles as Recurrence's embedding candidate set
- [X] T030 [US5] Implement `RecurrenceReader` in
      `backend/app/readers/application/recurrence_reader.py` (depends on T004,
      T027, T028, T029) — `interpret()` embeds the full candidate corpus every
      run (2026-08-14 clarification — no incremental clustering), clusters via
      T028, emits `recurring_issue` per cluster of size ≥ 2 citing every member
      event, surfaces an explicit error (not a silent skip) if `EmbeddingPort`
      fails (Edge Cases), checks the REQ-M5-15 cache (T007)
- [X] T031 [P] [US5] Write `backend/tests/readers/test_recurrence_reader.py` —
      T028's clustering/decision logic with a **faked** `EmbeddingPort` (fixed
      vectors for known input strings, no live OpenAI call — `plan.md`'s Testing
      section), reproducing `data-model.md`'s worked shape (`fnd-2`:
      `magnitude = 0.33`, two-event citation), and confirms an unrelated single
      ticket produces no finding (Acceptance Scenario 4)

**Checkpoint**: `quickstart.md` §1–2 all pass for every reader individually — all
five user stories independently functional.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Goal**: Assemble all five readers behind one real trigger (`RunReadersUseCase`,
`architecture/09`'s named Command), prove `spec.md`'s SC-001/SC-002/SC-003/SC-005
against the real, fully-ingested Meridian fixture, and document the feature.

- [X] T032 Implement `RunReadersUseCase` in `backend/app/readers/application/
      use_cases.py` (depends on T010, T016, T021, T025, T030) — iterates all
      five registered readers, isolates each one's failure (FR-014a, 2026-08-14
      clarification: one reader's exception is caught and reported, the other
      four still run and persist normally), persists directly at
      `status = pending_validation` — no `ValidationGate` call
      (`research.md`'s Decision, M5a doesn't exist until feature 007)
- [X] T033 Implement `backend/scripts/run_readers.py` (depends on T032) — manual
      `RunReadersUseCase` trigger, mirroring `scripts/run_collector.py`/
      `compute_score.py`'s pattern, printing a per-reader summary including any
      isolated failure
- [X] T034 Write `backend/tests/readers/test_run_readers_use_case.py` — real-DB
      integration test: seeds the new fixture event (T002), runs
      `RunReadersUseCase` against the real, already-ingested Meridian ledger,
      asserts `data-model.md`'s full worked-example table (`fnd-1`, `fnd-9`,
      `fnd-3`, `fnd-4`, `fnd-5`, `fnd-2` — SC-001); re-runs and asserts zero
      additional findings (REQ-M5-15, SC-003); asserts every finding's
      `cited_event_ids` resolves to a real `events` row (SC-002); forces a
      Recurrence failure (invalid embedding key) and asserts the other four
      readers' findings are still persisted (FR-014a) (depends on T032, T033)
- [X] T035 [P] Write `backend/tests/unit/test_readers_purity.py` (or extend the
      existing static-check pattern) confirming no `anthropic`/`openai` import
      exists anywhere in `app.readers.domain`/`app.readers.application` beyond
      `EmbeddingPort`'s interface declaration (SC-005) — `.importlinter`'s
      `readers-application-purity` contract already enforces this mechanically;
      this task confirms `lint-imports --config ../.importlinter` passes clean
- [X] T036 [P] Add a "Deterministic Findings" section to the root `README.md` —
      how to run all five readers, the new `OPENAI_API_KEY` prerequisite, and a
      link to `specs/005-deterministic-findings/quickstart.md`
- [X] T037 Run all of `specs/005-deterministic-findings/quickstart.md` end to
      end, confirm every acceptance scenario in `spec.md` passes, and re-run
      features 001–004's own quickstarts to confirm nothing regressed (depends on
      every task above)

**Checkpoint**: `quickstart.md` §1–6 all pass — this feature is complete.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories (every
  reader needs the `Reader` interface, ports, and the shared finding-persistence/
  cache adapter to exist first).
- **User Stories 1–5 (Phases 3–7)**: All depend on Foundational only — genuinely
  independent of each other, unlike feature 004's inverted diamond. Each reader
  reads different source data and writes independently to `findings`; no reader
  imports another's code.
- **Polish (Phase 8)**: Depends on all five user stories being complete —
  `RunReadersUseCase` is the one piece of real cross-cutting integration this
  feature needs, deliberately placed last since no individual user story requires
  it to be independently testable (each reader's own "Independent Test" in
  `spec.md` runs that reader directly, not through the orchestrator).

### Within Each User Story

- Domain (pure logic) before application (the reader itself) before adapters are
  wired in — though, as in feature 004, several tasks share one file
  (`backend/app/readers/domain/services.py` across all five stories;
  `backend/app/readers/adapters/sqlalchemy_repository.py` across US1/US2/US3/US4)
  and are marked `[P]` only where they touch genuinely independent regions of
  that shared file; the reader class itself (T010/T016/T021/T025/T030) is always
  sequential, since it's the one task per story that assembles that story's own
  domain + port pieces together.

### Parallel Opportunities

- T002 and T003 run in parallel with T001 (different files).
- T004 and T005 run in parallel (different files); T006 needs T005 first.
- Once Foundational (T004–T007) lands, **User Stories 1, 3, and 4's domain-logic/
  adapter tasks (T008/T009, T019/T020, T023/T024) can all proceed in parallel**
  with each other (different logical sections of shared files, no cross-story
  dependency) — only each story's own reader-assembly task (T010/T021/T025) and
  the shared-file edit ordering need to stay sequential within that file.
- User Story 2 (T012–T018) can also start immediately after Foundational, in
  parallel with US1/US3/US4, though it additionally touches `app.ingestion`
  (T013/T014) — a different module entirely, so zero file contention with the
  other stories.
- User Story 5 (T027–T031) can start immediately after Foundational too — its
  adapter (`openai_embedding.py`) is a new file with no contention, though its
  `services.py`/`sqlalchemy_repository.py` edits should land after whichever
  other story is mid-edit on those shared files.
- All five stories' test tasks (T011, T017, T022, T026, T031) run in parallel
  once their respective reader-assembly task lands.
- T035 and T036 are independent of each other and of T034 in Polish.

---

## Implementation Strategy

### MVP First (User Story 1 alone)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3 (User Story 1 — Commitment).
4. **STOP and VALIDATE**: `quickstart.md` §2, Commitment's finding only. This is
   the smallest real, demonstrable slice — a real reader producing a real finding
   from data that already exists.

### Incremental Delivery

1. Setup + Foundational → `Reader` interface and shared persistence ready.
2. Add User Story 1 (Commitment) → validate independently → the simplest reader
   proven correct.
3. Add User Story 2 (Usage + rollups) → validate independently → REQ-M2-06's
   long-deferred rollup computation is real for the first time.
4. Add User Stories 3 and 4 (Absence, Relationship) → validate each
   independently → both reduced-strength readers proven honest and correct.
5. Add User Story 5 (Recurrence) → validate independently → the one reader with
   a real external dependency proven correct, with `EmbeddingPort` faked in tests.
6. Polish (Phase 8) → assemble all five behind `RunReadersUseCase`, prove SC-001
   through SC-005 against the real fixture, re-verify features 001–004 still pass.

---

## Notes

- `[P]` tasks touch different files, or independent regions of a shared file,
  with no dependency on an incomplete task.
- This feature's dependency shape is five independent leaves (unlike feature
  004's inverted diamond) plus one final assembly phase — noted explicitly here
  rather than glossed over, per the same discipline features 002–004 applied to
  their own cross-story dependencies.
- Commit after each task or logical group; stop at any checkpoint to validate a
  story independently before continuing.
