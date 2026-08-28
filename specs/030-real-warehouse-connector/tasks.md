---

description: "Task list for feature 030 — Real Warehouse Connector"
---

# Tasks: Real Warehouse Connector

**Input**: Design documents from `specs/030-real-warehouse-connector/`

**Prerequisites**: plan.md, spec.md, research.md, quickstart.md

**Tests**: Unit tests against a fake `WarehouseClient` (no real database) for the collector itself;
one real-DB test proving `ComputeRollupsUseCase`'s new wiring actually rebuilds `rollups`.
`tests/unit/test_simulated_collector.py` is the non-regression proof for FR-005.

**Organization**: Tasks are grouped by the three user stories in `spec.md`.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 In `backend/app/config.py`, add `warehouse_connection_url: str = ""`,
      `warehouse_query_path: str = "./demo/warehouse-query.sql"`, and
      `warehouse_poll_interval_hours: int = 1` (same honest-empty-default discipline as
      `zendesk_subdomain`, except `warehouse_query_path` gets a real default path since it's a
      file location, not a secret — matching `client_profile_path`'s own precedent).
- [x] T002 [P] New `demo/warehouse-query.sql` — a placeholder/example query file (matching
      `quickstart.md`'s documented column contract), so a fresh checkout has something at the
      default path to point at during local development, clearly commented as an example to
      replace with a real, client-specific query.

**Checkpoint**: New settings load without error even when unset; the example query file exists.

---

## Phase 2: Foundational (Blocking Prerequisites)

- [x] T003 In `backend/app/worker.py`'s `_orchestrate_pipeline()`, add a call to
      `ComputeRollupsUseCase(SqlAlchemyEventRepository(session)).execute()` immediately before
      constructing/running `RunReadersUseCase` (`research.md` Decision 6) — both classes are
      already imported or trivially importable from
      `app.ingestion.application.use_cases`/`app.ingestion.adapters.sqlalchemy_repositories`. No
      change to `ComputeRollupsUseCase` itself.

**Checkpoint**: A real-DB test (T011) proves this call actually populates `rollups` from existing
`usage_measurement`/`survey_response` events — the first time this has ever been true in this
codebase for any source. This is foundational because it benefits User Story 1 regardless of which
collector (real or simulated) produced the underlying events.

---

## Phase 3: User Story 1 - Real warehouse data becomes real signals, and reaches the Usage reader (Priority: P1) 🎯 MVP

**Goal**: `WarehouseCollector` reads pre-computed usage readings from a configured SQL source and
turns each into a ledger event; `ComputeRollupsUseCase` (Phase 2) ensures they actually reach the
Usage reader.

**Independent Test**: Configure a real connection + query, run a cycle, confirm both a ledger event
and a `rollups` row exist (`quickstart.md` Story 1).

### Implementation for User Story 1

- [x] T004 [US1] New `backend/app/ingestion/adapters/warehouse_collector.py`: define
      `WarehouseClient` (a `Protocol` with `async def fetch_readings(self) ->
      list[dict[str, Any]]`), and `_RealWarehouseClient` implementing it — builds a SQLAlchemy
      async engine from `warehouse_connection_url`, executes the query text loaded from
      `warehouse_query_path`, and returns each row as a dict keyed by column name
      (`research.md` Decision 3).
- [x] T005 [US1] Same file: `WarehouseCollector(Collector)` — `source_type = "warehouse"`,
      `mvp_sources_always_expected = False`. Constructor `(client: WarehouseClient, collector_runs:
      CollectorRunRepositoryPort)`. `fetch()`: call `fetch_readings()`; for each row, validate the
      four required columns are present (skip and log if not, FR-008); compute
      `source_native_id = sha256(f"{metric}:{product_area}:{occurred_at.isoformat()}:
      {value_delta_pct}")` (`research.md` Decision 4); check `envelope_exists()` and skip if
      already processed. A whole-connection failure (the engine/query call itself raising)
      propagates unchanged (FR-007).
- [x] T006 [US1] Same file: `normalize(raw_item)` builds an `Envelope` matching
      `_normalize_warehouse`'s exact shape (`source_type="warehouse"`,
      `identity_status="unresolved"`, `resolved_stakeholder_id=None`, `redacted_fields=[]`,
      `payload_text=f"{metric} {value_delta_pct:+d}%"`, `structured_payload={"metric": ...,
      "product_area": ..., "value_delta_pct": ...}`) — FR-004, zero reader changes needed.
- [x] T007 [US1] In `backend/app/worker.py`: add `_run_warehouse_collector`/`_collect_warehouse`
      (sync-wrapper + async body, matching `_run_zendesk_collector`/`_collect_zendesk`'s exact
      shape), constructing `_RealWarehouseClient` from the new settings and `WarehouseCollector`,
      calling `RunCollectorUseCase.execute(collector, window_start=now, window_end=now,
      trigger="poll")`. Register `scheduler.add_job(_run_warehouse_collector, "interval",
      hours=settings.warehouse_poll_interval_hours, id="warehouse_collector")`; add `"warehouse":
      _run_warehouse_collector` to `_RUN_ONCE_JOBS` (FR-010).

### Tests for User Story 1

- [x] T008 [P] [US1] New `backend/tests/unit/test_warehouse_collector.py`: a fake
      `WarehouseClient` returning canned rows; assert `fetch()` correctly maps rows to raw items
      and that `normalize()`'s output shape matches `_normalize_warehouse`'s field-for-field.
- [x] T009 [P] [US1] Same file: assert identical row content across two `fetch()` calls produces
      the identical `source_native_id` both times (content-hash idempotency, FR-003/SC-002), and
      that a row missing a required column is skipped and logged rather than raising (FR-008).
- [x] T010 [P] [US1] Same file: assert a whole-connection failure (the fake's `fetch_readings`
      raising) propagates out of `fetch()` unchanged (FR-007).
- [x] T011 [US1] Real-DB test in `backend/tests/unit/test_pipeline_orchestration.py` (or a new
      dedicated file if that one's existing fixtures don't fit): insert a real
      `usage_measurement`-typed event directly (matching `test_hash_chain.py`'s own
      `make_envelope` + `SqlAlchemyEventRepository.append()` pattern, with
      `structured_payload={"metric": ..., "value_delta_pct": ...}`), call
      `ComputeRollupsUseCase(SqlAlchemyEventRepository(session)).execute()` directly (not the full
      `_orchestrate_pipeline()`, to keep this test focused), and assert a matching `rollups` row
      now exists — proving Phase 2's wiring target actually works, independent of which collector
      produced the underlying event.

**Checkpoint**: User Story 1 fully functional — real warehouse data becomes real, Usage-reader-
visible signals.

---

## Phase 4: User Story 2 - Simulated sources keep working unchanged (Priority: P1)

**Goal**: Prove `SimulatedCollector` and its JSON fixture are untouched.

### Tests for User Story 2

- [x] T012 [US2] Live-verify: run `tests/unit/test_simulated_collector.py` unchanged — confirm
      100% pass, zero modification to that file or to `simulated_collector.py`.
- [x] T013 [US2] Live-verify: `scripts/run_collector.py --source simulated` produces the same
      `envelopes_emitted`/`duplicates_skipped` counts as before this feature.

**Checkpoint**: User Stories 1 and 2 both independently verified.

---

## Phase 5: User Story 3 - A warehouse connection problem is visible (Priority: P2)

**Goal**: A whole-connection failure is an honest coverage gap.

### Tests for User Story 3

- [x] T014 [US3] Covered by T010 above (whole-connection-failure propagation) — no additional
      implementation needed; this phase confirms the coverage-gap behavior is exercised, not that
      new code exists for it.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T015 [P] Run `ruff`/`mypy`/`lint-imports --config ../.importlinter` clean across all changed
      files.
- [~] T016 [P] Run `quickstart.md`'s full validation sequence end to end (with a real warehouse
      connection, if available) as final sign-off. Partially done — see Verification log.
- [x] T017 Confirm `specs/ROADMAP.md` and `README.md` are intentionally left unmodified, matching
      `specs/025`–`029`'s own precedent.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Phase 1 only loosely; blocks User Story 1's own SC-003
  (Usage reader actually seeing the data), so it lands before Phase 3's own checkpoint can be
  fully proven, even though T003 itself doesn't depend on the collector existing yet.
- **User Story 1 (Phase 3)**: Depends on Phases 1–2. This is the MVP.
- **User Story 2 (Phase 4)**: Depends on nothing this feature builds — a non-regression check.
- **User Story 3 (Phase 5)**: Depends on Phase 3's `WarehouseCollector` existing (already covered
  by T010).
- **Polish (Phase 6)**: Depends on Phases 3–5.

### Parallel Opportunities

- T008/T009/T010 (same new test file, independent test cases) can be drafted together.
- T015/T016 (independent checks) can run in parallel.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 (Setup) → Phase 2 (Foundational — the pre-existing gap closes here).
2. Phase 3 (User Story 1) — the real connector exists and its data actually reaches the reader.
3. **STOP and VALIDATE** via `quickstart.md` Story 1.

### Incremental Delivery

1. Setup + Foundational → Phase 3 (US1) → validate → real warehouse signals flow in *and* are
   actually usable, for the first time for any source.
2. Phase 4 (US2) → validate → the explicit non-negotiable constraint confirmed held.
3. Phase 5 (US3) → validate → failure visibility confirmed (already covered by Phase 3's own tests).
4. Phase 6 (Polish) → final sign-off.

## Notes

- No `[Story]` label on T001–T003 (Setup/Foundational) or T015–T017 (Polish).
- Phase 2 (Foundational) is unusually load-bearing for this feature specifically — it's the one
  piece of this roadmap's three real-connector features that fixes something pre-existing rather
  than only adding something new, and User Story 1's own success criteria (SC-003) cannot be met
  without it.

## Verification log (how each task was actually confirmed, not just assumed)

- **T001/T002**: new `warehouse_*` settings load with no unset-value error; `demo/warehouse-query.sql`
  exists, clearly commented as a placeholder returning zero rows against this app's own database.
- **T003–T007**: `WarehouseCollector`/`_RealWarehouseClient`/`WarehouseClient` implemented and wired
  into `worker.py` (job function, `_RUN_ONCE_JOBS` entry, `scheduler.add_job`, startup log message);
  `ruff check .`, `uv run mypy app`, `lint-imports --config ../.importlinter` (4/4 contracts kept)
  all clean.
- **T008–T010**: New `backend/tests/unit/test_warehouse_collector.py` (5 tests, against a fake
  `WarehouseClient` — no real database needed, unlike Gmail/Zendesk, since this connector has no
  ledger-derived window), all passing in isolation and in the full suite.
- **T011**: Already existed as `backend/tests/unit/test_compute_rollups_use_case.py` (real-DB,
  calls `ComputeRollupsUseCase(...).execute()` directly against the seeded Meridian fixture) — ran
  it explicitly, passes, confirms `rollups` is populated for the first time in this codebase's
  history for any source.
- **Genuine pre-existing bug found and fixed, surfaced only by T003's own wiring**: the first full
  real-DB pipeline run (`tests/unit/test_pipeline_orchestration.py`) failed with a Postgres
  `CheckViolationError` on `score_runs_score_check` — `points_to_score()` returned a raw float
  `99.9999999999774` (not exactly `100.0`, so it slipped past the existing `if raw >= 100.0: return
  99.99` underflow guard), which Postgres then rounded to `100.00` at insert time for the
  `NUMERIC(5,2)` `score` column, before evaluating the `CHECK (score < 100)` constraint — failing
  it. This bug has existed since the scoring engine's own original guard was written; it was never
  reachable before because `rollups` was always empty, so the Usage reader never contributed enough
  points to push a real score run this close to saturation. Root-caused in
  `backend/app/scoring/domain/services.py`'s `ScoringCalculator.points_to_score()`; fixed by
  replacing the `if raw >= 100.0: return 99.99` threshold with `min(raw, 99.99)` — mathematically
  equivalent for the pathological-underflow case this guard was originally written for, but also
  monotonic by construction (no threshold discontinuity), unlike a naive `if raw >= 99.995: return
  99.99` fix (tried first, reverted): that version is NUMERIC(5,2)-safe but introduces a real
  discontinuity — total_points values straddling the 99.995 boundary would produce a *lower* score
  just past it, which `tests/scoring/test_monotonicity.py`'s 3000-example property test would be
  positioned to eventually catch (a much more reachable input range than the original `raw==100.0`
  float-underflow-only edge). One existing test's own premise was invalidated by this fix's
  correctness, not broken by it: `test_score_approaches_100_smoothly_for_large_but_representable_
  points` used `total_points=1000.0` to prove the domain function's saturation curve isn't just the
  99.99 clamp applying everywhere — but `total_points=1000.0` actually yields
  `raw≈99.999999999993`, itself inside the (correct, DB-safety-driven) clamp zone, so it stopped
  demonstrating unclamped behavior. Updated to `total_points=200.0` (`raw≈99.7667`, safely below the
  clamp), which still proves the same point. Confirmed via three full real-DB test runs after the
  fix: `tests/scoring/` (42 passed), `tests/unit/test_pipeline_orchestration.py` in isolation with
  real OpenAI/Anthropic calls (2 passed, 360s), and the full suite (`tests/golden_replay/
  tests/scoring/ tests/unit/`: 205 passed, 1 skipped, 0 failed — including the known pre-existing
  `test_hash_chain.py` full-suite-only flake, which did not occur in this run).
- **T012/T013**: `git diff` confirms zero changes to `simulated_collector.py` or
  `test_simulated_collector.py`; a live `scripts/run_collector.py --source simulated` run against a
  freshly migrated/seeded database produced `envelopes_emitted=18`, matching every prior
  real-connector feature's own baseline exactly. FR-005/User Story 2 holds.
- **T014**: Whole-connection-failure propagation covered by `test_a_whole_connection_failure_
  propagates_unchanged` in `test_warehouse_collector.py`, passing.
- **T015**: `ruff check .`, `uv run mypy app`, `lint-imports --config ../.importlinter` all clean.
- **T016**: Partially done. The fake-client unit tests (T008–T010) and the real-DB rollups test
  (T011) together prove the full local pipeline end to end (row → `Envelope` → ledger event →
  `rollups` → Usage-reader-visible signal). What was **not** verified: a connection to a real,
  external, client-owned warehouse database — no such warehouse was available in this session (this
  connector is generic-SQL-by-design, so there is no single "the Meridian warehouse" fixture to
  point at the way Gmail/Zendesk had one real or fake account). This mirrors feature 029's own
  honest gap for live Zendesk verification.
- **T017**: `specs/ROADMAP.md` and `README.md` intentionally left unmodified, matching
  `specs/025`–`029`'s own precedent.

**Outstanding**: live verification against a real, external warehouse connection (T016's "if
available" clause) requires a real client warehouse and query, which was not available in this
session — flagged honestly here, the same as feature 029's Zendesk connector was before this one.
