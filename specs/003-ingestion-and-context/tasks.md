# Tasks: Ingestion and Context

**Input**: Design documents from `specs/003-ingestion-and-context/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/profile-reload.md`, `quickstart.md`

**Tests**: Test tasks below cover exactly `spec.md`'s acceptance scenarios (profile
validation, hash-chain/business-hours/replay arithmetic, collector idempotency/identity
resolution/redaction/coverage, absence detection) — not a broader TDD suite beyond what
those scenarios already require.

**Organization**: Tasks are grouped by user story — US1 (P1, client profile), US2 (P1,
event ledger), US3 (P2, signal collection), US4 (P3, absence detection) — per `plan.md`'s
Project Structure.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1/US2/US3/US4
- Every task names an exact file path from `plan.md`'s Project Structure

---

## Phase 1: Setup

- [X] T001 [P] Add `cryptography` and `PyYAML` to `backend/pyproject.toml` via `uv add`
      (`research.md` §Decision: Message-body encryption)
- [X] T002 [P] Add a `./secrets:/app/secrets:ro` volume mount to the `api`/`worker`
      services in `docker-compose.yml`, and `ENCRYPTION_KEY_ID` to `.env.example`
      (`research.md`)
- [X] T003 Create `demo/fixtures/meridian-week.json` — the 6-item fixture from
      `data-model.md`, derived from `examples/01-end-to-end-walkthrough.md`'s Phase-1
      subset, including the sixth item whose text touches the `legal_threads` exclusion
      (so redaction has something real to redact)

**Checkpoint**: Dependencies installed, fixture exists, key-file mount ready.

---

## Phase 2: Foundational

**Purpose**: Message-body encryption — shared by US2 (event bodies) and US3 (envelope
payloads), and a hard boundary from the first line of code (`REQ-M1-P4`), not something
either story should implement separately.

**CRITICAL**: No user story task can begin until this phase is complete.

- [X] T004 Implement `load_key`/`encrypt`/`decrypt` (Fernet) in
      `backend/app/ingestion/adapters/encryption.py`, reading `ENCRYPTION_KEY_PATH`
      (depends on T001)
- [X] T005 Wire encryption-key loading into `backend/app/main.py` startup — the app
      MUST fail to start if the key file is missing or invalid (spec.md Edge Cases;
      depends on T004, T002)
- [X] T006 [P] Write `backend/tests/unit/test_encryption.py` — `encrypt`/`decrypt`
      round-trips to the original plaintext, and the ciphertext never contains the
      plaintext as a substring (depends on T004)

**Checkpoint**: Foundation ready — user story work can now begin.

---

## Phase 3: User Story 1 - The client profile becomes queryable, versioned context (Priority: P1)

**Goal**: A submitted YAML profile is validated and stored as a new immutable version
with the right multipliers, or rejected with a specific error.

**Independent Test**: `quickstart.md` §1.

### Implementation for User Story 1

- [X] T007 [P] [US1] Implement the profile Pydantic schema and `signs_renewal`
      validator (`REQ-M3-01`, `REQ-M3-07`) in
      `backend/app/context/domain/profile_schema.py`
- [X] T008 [P] [US1] Define `ClientProfileRepositoryPort` (write side) in
      `backend/app/context/application/ports.py`
- [X] T009 [US1] Implement `SqlAlchemyClientProfileRepository` — inserts a new
      versioned row set, flips the prior version's `is_current` in the same
      transaction — in `backend/app/context/adapters/sqlalchemy_repository.py`
      (depends on T008)
- [X] T010 [US1] Implement the YAML loader in
      `backend/app/context/adapters/yaml_profile_loader.py`, parsing into the schema
      from T007 (depends on T007)
- [X] T011 [US1] Implement `SubmitProfileUseCase` — validate, version, and call the
      real `ReplayUseCase` (T022) — in `backend/app/context/application/use_cases.py`
      (depends on T007, T008, T022)
- [X] T012 [US1] Implement `POST /api/profile/reload` and `GET /api/profile` per
      `contracts/profile-reload.md` in `backend/app/context/adapters/profile_router.py`
      (depends on T009, T010, T011)
- [X] T013 [US1] Wire the profile router into `backend/app/main.py` (depends on T012)
- [X] T014 [P] [US1] Write `backend/tests/unit/test_profile_validation.py` covering
      accept/reject cases: missing required field, zero `signs_renewal: true`
      stakeholders (depends on T007)
- [X] T015 [US1] Write `backend/tests/unit/test_profile_router.py` exercising
      `POST /api/profile/reload` end to end: new version created, prior version's
      `is_current` flips, `422` on an invalid profile with no new version created
      (depends on T013)

**Checkpoint**: `quickstart.md` §1 passes — User Story 1 is independently functional
(note: T011 depends on T022 from Phase 4, since "trigger replay" needs a real replay
to trigger — see Dependencies below).

---

## Phase 4: User Story 2 - Events append immutably to a tamper-evident, replayable ledger (Priority: P1)

**Goal**: Events append with a verifiable hash chain; response pairs compute exact
business-hours arithmetic against the client's calendar, including across a weekend; a
message referencing a ticket number stitches to that ticket's thread; dropping and
replaying projections reproduces them exactly.

**Independent Test**: `quickstart.md` §2.

### Implementation for User Story 2

- [X] T016 [P] [US2] Implement canonical serialization + SHA-256 hashing (genesis value
      for the first event) in `backend/app/ingestion/domain/hash_chain.py`, per
      `data-base/03-schema-ledger.md`'s algorithm (`REQ-M2-08`)
- [X] T017 [P] [US2] Implement `compute_business_hours_elapsed(start, as_of, calendar)`
      in `backend/app/ingestion/domain/business_hours.py` (`REQ-M2-05`, `research.md`'s
      `as_of`-parameter design) — MUST correctly skip weekends, not just clip to the
      daily window (`data-model.md`'s weekend-boundary worked example)
- [X] T018 [P] [US2] Define `EventRepositoryPort` in
      `backend/app/ingestion/application/ports.py`
- [X] T019 [US2] Implement `SqlAlchemyEventRepository` — append with hash chain, query
      the latest `event_hash` to chain against, plus `truncate_projections`/
      `bulk_rebuild_projections` methods for T022's replay — in
      `backend/app/ingestion/adapters/sqlalchemy_repositories.py` (depends on T016,
      T018)
- [X] T020 [US2] Implement `AppendEventUseCase` — builds canonical fields, computes the
      hash via T016, appends (`REQ-M2-01`, `REQ-M2-02`, `REQ-M2-03` for
      `supersedes_event_id`) — in `backend/app/ingestion/application/use_cases.py`
      (depends on T016, T018)
- [X] T021 [US2] Implement response-pair computation (`open`/`resolved`/
      `open_overdue`, using T017) in
      `backend/app/ingestion/application/use_cases.py` (same file as T020, sequential;
      depends on T017, T020)
- [X] T022 [US2] Implement `ReplayUseCase` — truncates `event_threads`/
      `response_pairs`, replays every `events` row in `occurred_at` order rebuilding
      both projections from scratch via T019/T020/T021's logic, records a
      `replay_runs` row (`REQ-M2-07`) — in
      `backend/app/ingestion/application/use_cases.py` (same file, sequential; depends
      on T019, T020, T021)
- [X] T023 [P] [US2] Write `backend/tests/unit/test_replay.py` — append a sequence of
      events, snapshot `event_threads`/`response_pairs`, truncate them, call
      `ReplayUseCase`, assert the rebuilt state is byte-identical to the snapshot
      (depends on T022)
- [X] T024 [US2] Implement ticket-reference thread stitching (`#(\d+)` regex,
      `research.md`'s minimal-heuristic decision) in
      `backend/app/ingestion/domain/thread_stitching.py` (`REQ-M2-04`)
- [X] T025 [P] [US2] Write `backend/tests/unit/test_hash_chain.py` — append a sequence
      of events, verify the chain via the database's own `verify_hash_chain()` function
      (`research.md`'s independent cross-check) (depends on T019)
- [X] T026 [P] [US2] Write `backend/tests/unit/test_business_hours.py` — assert
      `data-model.md`'s exact worked numbers: 19.0h `open_overdue` for #456 at the
      documented `as_of` reference time, 2.0h `resolved` for #398, **and** 4.0h for the
      Friday-to-Monday weekend-boundary case (depends on T017)

**Checkpoint**: `quickstart.md` §2 passes — User Stories 1 AND 2 both work
independently; both modules `decisions/01-mvp-scope-and-phasing.md` calls un-phaseable
now exist for real, including a genuine, tested replay path.

---

## Phase 5: User Story 3 - Signals are collected, identified, redacted, and reported on honestly (Priority: P2)

**Goal**: `SimulatedCollector` proves the `Collector` interface end to end against the
Meridian fixture — idempotent, identity-resolving, redacting, coverage-reporting (both
the clean case and a simulated source failure).

**Independent Test**: `quickstart.md` §3. Depends on US1 (identity/exclusion targets)
and US2 (a ledger to append into, encryption from Foundational).

### Implementation for User Story 3

- [X] T027 [US3] Define the `Collector` ABC (Template Method: `fetch`, `normalize`,
      `resolve_identity`, `emit_envelope`) in
      `backend/app/ingestion/application/collector.py` (depends on T018)
- [X] T028 [P] [US3] Implement the `Envelope` value object and idempotency-key
      derivation (`hash(source_type, source_native_id)`) in
      `backend/app/ingestion/domain/envelope.py` (`REQ-M1-03`, `REQ-M1-10`)
- [X] T029 [US3] Define `ClientProfileContextPort` (current stakeholder identifiers +
      exclusions) in `backend/app/ingestion/application/ports.py` (same file as T018,
      sequential)
- [X] T030 [US3] Implement `SqlAlchemyClientProfileContext` in
      `backend/app/ingestion/adapters/sqlalchemy_repositories.py` (same file as T019,
      sequential; depends on T029)
- [X] T031 [US3] Implement identity resolution — exact match against identifiers, else
      `unresolved`, upserting `identity_map` (`REQ-M1-04`, `REQ-M1-05`, `REQ-M1-P5`,
      `research.md`'s exact-match-only decision) — in
      `backend/app/ingestion/application/use_cases.py` (same file as T020–T022,
      sequential; depends on T029)
- [X] T032 [US3] Implement redaction against the profile's `exclusions` list, recording
      which fields were stripped (`REQ-M1-09`) — in
      `backend/app/ingestion/application/use_cases.py` (same file, sequential)
- [X] T033 [US3] Implement `RunCollectorUseCase` — orchestrates fetch → normalize →
      resolve_identity → emit_envelope → append, the idempotency check, and coverage
      reporting including the degraded/source-failure path (`REQ-M1-07`, `REQ-M1-08`)
      — in `backend/app/ingestion/application/use_cases.py` (same file, sequential;
      depends on T027, T031, T032)
- [X] T034 [US3] Implement `SimulatedCollector`, reading
      `demo/fixtures/meridian-week.json`, in
      `backend/app/ingestion/adapters/simulated_collector.py` (depends on T027, T028,
      T003)
- [X] T035 [US3] Wire payload/body encryption (Foundational's T004) into envelope
      emission before persistence (`REQ-M1-P4`) — in
      `backend/app/ingestion/application/use_cases.py` (same file, sequential; depends
      on T004, T033)
- [X] T036 [US3] Create `backend/scripts/run_collector.py` — manual `SimulatedCollector`
      trigger, mirroring `scripts/seed.py`'s pattern (`research.md`) (depends on T033,
      T034)
- [X] T037 [P] [US3] Write `backend/tests/unit/test_simulated_collector.py` covering:
      run twice → 6 events then 0 new events with `duplicates_skipped = 6`; Ana's
      identifier resolves and the Zendesk reporter's does not; the sixth fixture item's
      `legal_threads` content is stripped and recorded in `redacted_fields`; and a
      simulated source failure produces a coverage report with `sources_read <
      sources_expected` and a populated `gap_reason` (depends on T034, T036)

**Checkpoint**: `quickstart.md` §3 passes — User Stories 1, 2, AND 3 all work.

---

## Phase 6: User Story 4 - The absence collector notices what didn't happen (Priority: P3)

**Goal**: A commitment with an unmet cadence produces an `absence` event; one just
satisfied produces none.

**Independent Test**: `quickstart.md` §4. Depends on US1 (commitments) and US2 (events
to query for "last contact").

### Implementation for User Story 4

- [X] T038 [US4] Define `CommitmentLookupPort` in
      `backend/app/ingestion/application/ports.py` (same file as T018/T029, sequential)
- [X] T039 [US4] Implement `SqlAlchemyCommitmentLookup` in
      `backend/app/ingestion/adapters/sqlalchemy_repositories.py` (same file as
      T019/T030, sequential; depends on T038)
- [X] T040 [US4] Implement `DetectAbsenceUseCase` — compares each commitment's cadence
      against the latest matching event, appends an `absence` event when overdue
      (`REQ-M1-06`) — in `backend/app/ingestion/application/use_cases.py` (same file,
      sequential; depends on T038, T020)
- [X] T041 [US4] Register the absence-detection job on the APScheduler heartbeat in
      `backend/app/worker.py` (depends on T040)
- [X] T042 [P] [US4] Write `backend/tests/unit/test_absence_collector.py` — an unmet
      cadence produces an `absence` event, a just-satisfied one produces none (depends
      on T040)

**Checkpoint**: `quickstart.md` §1–4 all pass — all four user stories independently
functional; this feature is complete.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T043 [P] Add an "Ingestion and Context" section to the root `README.md` — the new
      encryption-key setup step, and a link to
      `specs/003-ingestion-and-context/quickstart.md`
- [X] T044 Run all of `specs/003-ingestion-and-context/quickstart.md` end to end,
      confirm every acceptance scenario in `spec.md` passes, and re-run features
      001–002's own quickstarts to confirm nothing regressed (depends on every task
      above)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories (encryption is
  a hard boundary for both US2 and US3, and cheap enough to just always have ready).
- **User Story 1 (Phase 3)** and **User Story 2 (Phase 4)**: Both depend on
  Foundational — but **US1's T011 additionally depends on US2's T022** (`ReplayUseCase`),
  since "submit a profile → trigger replay" needs a real replay to call. This is the one
  place the "two independent P1 foundations" framing has a real, narrow exception: US1
  is independently *testable* up through validation and versioning (`quickstart.md`
  §1's first two checks) without US2, but its full acceptance scenario 4 (replay
  triggered) needs US2's T022 to exist.
- **User Story 3 (Phase 5)**: Depends on Foundational **and** both US1 (identity/
  exclusion targets) and US2 (a ledger to append into) being complete.
- **User Story 4 (Phase 6)**: Depends on Foundational **and** both US1 (commitments)
  and US2 (event querying) being complete — independent of US3.
- **Polish (Phase 7)**: Depends on all four user stories being complete.

### Within Each User Story

- Domain (pure logic) before application (use cases) before adapters (routes/repos).
- Several US2/US3/US4 tasks share `backend/app/ingestion/application/use_cases.py` and
  `.../ports.py` / `.../adapters/sqlalchemy_repositories.py` — marked sequential
  (no `[P]`), not because the *stories* depend on each other, but because they're
  literally editing the same file.

### Parallel Opportunities

- T001 and T002 run in parallel; T003 is independent of both.
- T006 (encryption test) runs in parallel with nothing else in Foundational (T004→T005
  is sequential; T006 only needs T004).
- US1's T007 and T008 run in parallel; T014 runs in parallel with the router work once
  T007 lands.
- US2's T016, T017, T018 run in parallel (three different files, no shared dependency
  beyond Foundational); T023, T025, T026 run in parallel once their dependencies land.
- US3's T028 runs in parallel with T027; US3's T037 is independent once T034/T036 land.
- US4's T042 is independent once T040 lands.
- **US1 and US2 can still largely be staffed to two different people** once
  Foundational is done — they touch disjoint files — but whoever owns US1's T011 needs
  US2's T022 merged first (see Phase Dependencies above).

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 4 (US2) far enough to reach T022 (`ReplayUseCase`), then Phase 3 (US1)
   can finish T011 onward; everything else in each story can proceed in parallel before
   that point.
4. **STOP and VALIDATE**: `quickstart.md` §1–2. This is the actual MVP —
   `decisions/01-mvp-scope-and-phasing.md` names these two modules as the ones that
   "can't be partial"; everything after this is breadth (collection, absence), not
   foundation.

### Incremental Delivery

1. Setup + Foundational → encryption ready, both stories can start.
2. Add US1 + US2 (US1's replay-triggering task waits on US2's `ReplayUseCase`) →
   validate each independently → the two un-phaseable foundations are real, including a
   genuine, tested replay path.
3. Add US3 → validate (`quickstart.md` §3) → the pipe to the outside world exists,
   proven against a real fixture end to end, including the redaction and
   source-failure-coverage paths.
4. Add US4 → validate (`quickstart.md` §4) → the smallest, most self-contained piece.
5. Polish (Phase 7) → re-verify features 001–002 still pass, not just this one.

---

## Notes

- `[P]` tasks touch different files with no dependency on an incomplete task.
- This feature's dependency shape is mostly a **diamond** (US3/US4 each depend on both
  US1 and US2), **with one edge running the other direction**: US1's final task depends
  on US2's `ReplayUseCase` (T022). Noted explicitly above rather than glossed over, per
  the same discipline applied in feature 002's tasks.md.
- Commit after each task or logical group; stop at any checkpoint to validate a story
  independently before continuing.
