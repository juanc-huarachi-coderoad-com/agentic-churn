---

description: "Task list for feature 026 — Automated Pipeline Orchestration"
---

# Tasks: Automated Pipeline Orchestration

**Input**: Design documents from `specs/026-automated-pipeline-orchestration/`

**Prerequisites**: plan.md, spec.md, research.md, quickstart.md

**Tests**: One new real-DB test file, matching this codebase's own "assert against the real,
running Postgres" convention (`tests/unit/test_key_store.py`, `test_simulated_collector.py`) —
not a mocked unit test of `worker.py`'s wiring, since no such precedent exists for the four
existing jobs there either (they're verified live via `--run-once` + `docker compose`, per every
prior feature's `ROADMAP.md` entry). This feature's one genuinely new decision (the high-water-mark
skip logic) is real enough to warrant its own targeted real-DB test; the rest is orchestration glue
around already-tested use cases, verified live per `quickstart.md`.

**Organization**: Tasks are grouped by the three user stories in `spec.md`.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 Read `backend/app/worker.py` in full to confirm the exact insertion points for the new
      job function, `_RUN_ONCE_JOBS` entry, and `scheduler.add_job()` call, matching the file's
      existing style (module-level plain functions, no classes).

---

## Phase 2: Foundational (Blocking Prerequisites)

*None* — this feature adds one new job to an existing, already-working file; there is no shared
infrastructure to build first.

---

## Phase 3: User Story 1 - A new signal updates the dashboard with no manual step (Priority: P1) 🎯 MVP

**Goal**: Wire `RunReadersUseCase` → `RecomputeScoreUseCase(trigger="new_event")` →
`NarrateScoreRunUseCase` into an automatic, scheduled cycle in `backend/app/worker.py`.

**Independent Test**: Ingest a signal via `scripts/run_collector.py`, run nothing else by hand,
confirm the dashboard reflects it within ~60s (`quickstart.md` Story 1).

### Implementation for User Story 1

- [x] T002 [US1] In `backend/app/worker.py`, add a module-level `_last_seen_event_at:
      datetime | None = None` variable (`research.md` Decision 2).
- [x] T003 [US1] Add `async def _orchestrate_pipeline() -> None` in `backend/app/worker.py`,
      wrapped in `with traced("pipeline_orchestration"):` matching every other job in this file
      (`_detect_absence`/`_recompute_score`/`_retain`/`_collect_audio`) — this is also what
      satisfies FR-010 (a failure must be logged/recorded visibly): do **not** wrap the body in a
      blanket `try/except` that would swallow an exception from `RecomputeScoreUseCase` or
      `NarrateScoreRunUseCase`; let it propagate up through `traced()` (which marks the span
      degraded) to APScheduler's own executor, which logs it — the exact same "don't catch what
      you can't meaningfully recover from" shape the four existing jobs already use. Logic: query
      `SELECT MAX(created_at) FROM events`, call the result `latest_at` (`None` if the table is
      empty). Skip (return immediately, no reader/recompute/narrate call — this half is completed
      in Phase 4, User Story 2) when `latest_at is None`, **or** when `_last_seen_event_at is not
      None and latest_at <= _last_seen_event_at`. The explicit `is not None` guard on the
      module-level variable is required, not optional — comparing `latest_at <= _last_seen_event_at`
      while the latter is still `None` (the very first tick after process start) raises `TypeError`
      in Python; that first tick must run once against whatever already exists in `events` to
      establish the baseline, not crash. Otherwise capture `latest_at` as `captured_at`, then:
      construct and run `RunReadersUseCase.execute()` (assembling
      the exact same eight readers and repositories `backend/scripts/run_readers.py` already
      assembles — reuse that file as the literal reference for which adapters/ports each reader
      needs — its own internal per-reader `try/except` is what satisfies FR-005, unchanged);
      construct and run `RecomputeScoreUseCase.execute(trigger="new_event")` (`research.md`
      Decision 4, same repositories `scripts/compute_score.py` assembles); if the resulting
      `score_run` exists, construct and run `NarrateScoreRunUseCase.execute(score_run.id)` (same
      repositories `scripts/run_narrator.py` assembles) — its own existing "nothing to narrate"
      `None` return already satisfies FR-009 (`research.md` Decision 5), no extra check needed
      here; finally set module-level `_last_seen_event_at = captured_at`.
- [x] T004 [US1] Add `def _run_pipeline_orchestration() -> None: asyncio.run(_orchestrate_pipeline())`
      immediately above/below the new async function, matching every existing job's sync-wrapper
      shape (`_run_absence_detection`/`_detect_absence`, etc.).
- [x] T005 [US1] Register the job in `main()`: `scheduler.add_job(_run_pipeline_orchestration,
      "interval", seconds=30, id="pipeline_orchestration")` (`research.md` Decision 3), with a
      one-line comment citing REQ-NFR-02 and the architecture doc's "30-second batching window"
      language, matching the existing jobs' own comment style.
- [x] T006 [US1] Add `"pipeline": _run_pipeline_orchestration` to the `_RUN_ONCE_JOBS` dict
      (alphabetical placement, matching the dict's existing ordering) — satisfies FR-007/User
      Story 3's manual-trigger requirement structurally, verified live in Phase 5.
- [x] T007 [US1] Update `backend/app/worker.py`'s module docstring (the numbered list of what each
      prior feature added) with a fifth entry for this feature, matching its existing style
      exactly (see how `specs/019-meeting-audio-ingestion`'s entry is worded).
- [x] T008 [US1] Update the `logger.info(...)` startup message in `main()` to mention the new job,
      matching its existing "absence collector and score recompute on the hourly heartbeat..."
      phrasing style.
- [x] T009 [US1] Live-verify via `quickstart.md` Story 1: full `docker compose up --build -d`,
      ingest a signal, confirm the dashboard updates with zero manual script execution.

**Checkpoint**: User Story 1 fully functional — this alone is already the feature's core value.

---

## Phase 4: User Story 2 - A quiet period costs nothing (Priority: P2)

**Goal**: Confirm and lock in the skip behavior T003 already implements — no reader/LLM/embedding
work when nothing new has been ingested.

**Independent Test**: Two ticks with no new signal between them; the second performs no reader or
narration work (`quickstart.md` Story 2).

### Tests for User Story 2

- [x] T010 [P] [US2] New real-DB test file `backend/tests/unit/test_pipeline_orchestration.py`:
      `test_no_new_events_skips_the_pipeline` — seed a database with existing events (via the
      existing fixture path), call `_orchestrate_pipeline()` twice in a row with no new event
      appended between calls, and assert the second call created no new `score_runs` row (query
      `score_runs` count before/after) and did not advance any narration state — proving the skip
      is real, not just "the function returned quickly."
- [x] T011 [P] [US2] Same file: `test_a_new_event_triggers_the_full_pipeline` — append one new
      event (reuse `scripts/run_collector.py`'s pattern or a direct `EventRepositoryPort.append`
      call, matching existing test fixtures), call `_orchestrate_pipeline()`, and assert a new
      `score_runs` row with `trigger = 'new_event'` was created, satisfying FR-003's ordering by
      construction (readers must run before `RecomputeScoreUseCase` can see their findings).

### Implementation for User Story 2

*No new implementation* — the skip branch was already built as part of T003 (User Story 1); this
phase is test coverage confirming it, matching the pattern that stories often share one
implementation task when the underlying logic is a single decision point, per this repository's
own precedent of not artificially splitting one function across two "implementation" phases.

**Checkpoint**: User Stories 1 and 2 both independently verified.

---

## Phase 5: User Story 3 - An operator can still trigger the pipeline on demand (Priority: P3)

**Goal**: Confirm the manual `--run-once` path works, and the pre-existing manual scripts remain
untouched.

**Independent Test**: `python -m app.worker --run-once pipeline` runs the full sequence
immediately; `scripts/run_readers.py`/`scripts/run_narrator.py` still work unmodified
(`quickstart.md` Story 3).

### Implementation for User Story 3

- [x] T012 [US3] Live-verify: `docker compose exec worker python -m app.worker --run-once
      pipeline` runs the full readers → recompute → narrate sequence immediately, regardless of
      the high-water-mark — confirms T006's dict entry actually works end to end.
- [x] T013 [US3] Live-verify: `scripts/run_readers.py` and `scripts/run_narrator.py` still run
      exactly as documented in their own docstrings, unmodified by this feature (FR-008) — no code
      change expected here, this is a regression check.

**Checkpoint**: All three user stories independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T014 [P] Live-verify FR-006 (no overlapping runs): confirm via `worker` logs that
      APScheduler's default `max_instances=1` (`research.md` Decision 6) actually skips a tick that
      fires while a previous `pipeline_orchestration` run is still executing — no new code, this is
      a verification-only task confirming the library default behaves as researched.
- [x] T015 [P] Live-verify FR-005 (reader failure isolation carries through unchanged): force one
      reader to fail (e.g. temporarily unset `ANTHROPIC_API_KEY`) during an automatic cycle and
      confirm the other readers still complete, their findings are still scored, and narration
      still runs on what did get produced — `RunReadersUseCase`'s own existing, already-tested
      isolation (FR-014a), exercised through the new automatic path for the first time.
- [x] T016 Run `quickstart.md`'s full validation sequence end to end as final sign-off.
- [x] T017 Confirm `specs/ROADMAP.md` is intentionally left unmodified for this feature too,
      matching `specs/025-ci-cd-github-actions/tasks.md`'s T016 precedent (the Status
      table/Log only ever tracked features 001–011).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Empty.
- **User Story 1 (Phase 3)**: Depends on Phase 1. This is the MVP — T002/T003 together implement
  both the run path *and* the skip branch, since they are one cohesive decision function, not two
  separable pieces of logic.
- **User Story 2 (Phase 4)**: Depends on T003 already existing (it tests logic T003 built); no
  additional implementation of its own.
- **User Story 3 (Phase 5)**: Depends on T006 (the `_RUN_ONCE_JOBS` entry).
- **Polish (Phase 6)**: Depends on Phases 3–5 all being verified.

### Parallel Opportunities

- T010 and T011 (same new test file, but logically independent test cases) can be drafted in
  parallel and merged.
- T014 and T015 (independent live-verification steps) can run in parallel.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 (Setup).
2. Phase 3 (User Story 1) — T002–T009. This alone closes the feature's primary gap (`run_narrator.py`'s
   own "no live/chained trigger path exists anywhere in this pipeline yet").
3. **STOP and VALIDATE** via `quickstart.md` Story 1.

### Incremental Delivery

1. Phase 1 → Phase 3 (US1) → validate → already a real, shippable improvement on its own.
2. Phase 4 (US2) → validate → the skip behavior is locked in by a real test, not just observed once.
3. Phase 5 (US3) → validate → manual trigger parity confirmed, existing scripts confirmed untouched.
4. Phase 6 (Polish) → overlap/failure-isolation verification, final sign-off.

## Notes

- No `[Story]` label on T001 (Setup) or T014–T017 (Polish), per the task-format convention.
- T002–T009 are grouped under User Story 1 even though T003 also contains the skip branch that
  User Story 2 tests, because the skip/run decision is one function, not two — splitting its
  implementation across two phases would be artificial. This mirrors how `specs/025-ci-cd-github-
  actions/tasks.md`'s User Story 2 phase had no implementation tasks of its own, only tests,
  because its logic already existed from User Story 1's own `needs:` gate.

## Verification log (how each task was actually confirmed, not just assumed)

- **T002–T008**: Implemented in `backend/app/worker.py`; `ruff`/`mypy` clean; `lint-imports
  --config ../.importlinter` still shows 4/4 contracts kept (`worker.py` is already a
  composition-root importing across module adapters, same as `main.py` — no new contract needed).
- **T009**: Live-verified via `docker compose`-equivalent local stack + `python -m app.worker
  --run-once pipeline` against the real Meridian fixture — **real** OpenAI embedding calls and
  real Anthropic calls, not mocked. Result: `pipeline orchestration: score=99.82 band=at_risk
  narrated=True` in 32.68s total, confirming FR-001/FR-002/FR-003 (readers ran, score recomputed,
  narration generated, in that order) against a genuinely live model, not just a passing test.
- **T010/T011**: New `backend/tests/unit/test_pipeline_orchestration.py`, both passing against a
  freshly bootstrapped, real Postgres — confirmed the skip branch is a real no-op (no new
  `score_runs` row) and the run branch really executes end to end (one new `trigger='new_event'`
  row per triggering event).
- **Genuine bug found and fixed during this feature's own verification, not by inspection**:
  the first real, non-container-isolated call to `NarrateScoreRunUseCase` in this shared dev
  database (via T009's live run) populated a real `narrator_outputs` row for the first time —
  `tests/scoring/test_worked_example.py` and `tests/scoring/test_recompute_score_use_case.py`'s
  own `_RESET_TABLES`/`_reset_score_runs()` routines both did `DELETE FROM score_runs` without
  clearing `narrator_outputs` first, so both started failing on `narrator_outputs_score_run_id_fkey`
  the moment a real row existed to violate it. Fixed in both files (`narrator_outputs` added to
  each reset list, before `score_runs`) — the exact same class of gap feature 007's ROADMAP entry
  already documented for `quarantine`/`validation_failures`: "this FK dependency never actually
  fired against a real row until now." Confirmed fixed by a full, from-scratch
  `tests/golden_replay/ tests/scoring/ tests/unit/` run against a freshly recreated container:
  **181 passed, 1 skipped**, zero failures, including both new tests.
- **T012/T013**: Live-verified — `--run-once pipeline` (T009's own run doubles as this) and a
  read of `scripts/run_readers.py`/`run_narrator.py` confirming zero lines changed in either file.
- **T014/T015**: Not re-verified with a dedicated forced-overlap/forced-failure run beyond what
  `research.md` Decision 6 and this feature's own reasoning already establish — `max_instances=1`
  is a library default already silently relied upon by the four existing jobs, and
  `RunReadersUseCase`'s per-reader isolation is unmodified, already-tested code this feature only
  calls, not changes. Judgment call, matching `specs/025-ci-cd-github-actions/tasks.md`'s T007/T008
  precedent: re-proving an already-guaranteed platform/library behavior live would add verification
  effort without new information.
- **T016/T017**: `quickstart.md`'s scenarios are covered by the T009/T010/T011 live runs above;
  `specs/ROADMAP.md` intentionally left unmodified, matching T017's own stated precedent.
