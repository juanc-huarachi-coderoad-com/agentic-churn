# Tasks: Production Hardening

**Input**: Design documents from `specs/011-production-hardening/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/profile-editor.md`, `contracts/weight-recalibration.md`,
`contracts/rbac.md`, `quickstart.md`

**Tests**: Included, matching every prior feature's convention — pure unit
tests for new domain-shaped logic (no DB), real-DB/real-route integration
tests per story, and one static no-LLM-import re-scan.

**Organization**: Six independent user-story phases, ordered exactly by
`spec.md`'s priority (P1→P6). Unlike a typical single-slice feature, this is
build-order Phase 11 ("Hardening") bundling six real but loosely-coupled
items the base product spec's own §16 groups together — most stories touch
different modules and files, so cross-story parallelism is higher than
usual; the two real cross-story dependencies (US2's role-threading feeding
US4's admin check; US2's `require_full_access` gate reused by US5's new
route) are called out explicitly where they occur.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, or an independent region of
  a shared file, with no dependency on an incomplete task)
- **[Story]**: US1 (retention), US2 (RBAC), US3 (observability), US4 (weight
  recalibration), US5 (profile editor), US6 (Post-MVP sources)
- Every task names an exact file path from `plan.md`'s Project Structure

---

## Phase 1: Setup

- [X] T001 [P] Add `retention_window_days: int = 90`, `data_keys_dir: str =
      "./secrets/data-keys"`, and `otel_exporter_endpoint: str = ""` to
      `backend/app/config.py`'s `Settings` (`research.md` Decision 1/6;
      `otel_exporter_endpoint = ""` means tracing initializes with a
      console/no-op exporter, matching FR-012's "unaffected if the
      observability backend itself is unreachable"). Implemented as
      `otel_exporter_otlp_endpoint` (not `otel_exporter_endpoint`) so
      pydantic-settings' default env-var mapping matches the OTel-standard
      `OTEL_EXPORTER_OTLP_ENDPOINT` name used in docker-compose.yml with no
      alias needed — a naming correction found during implementation.
- [X] T002 [P] Add `opentelemetry-sdk` and `opentelemetry-exporter-otlp` to
      `backend/pyproject.toml`'s dependencies (`research.md` Decision 6);
      run `uv lock`
- [X] T003 [P] Add an `otel-collector` service to `docker-compose.yml`
      (`otel/opentelemetry-collector` image, minimal config logging spans to
      stdout — `docker-compose/otel-collector-config.yaml`, new file) and
      set `OTEL_EXPORTER_OTLP_ENDPOINT` on the `api`/`worker` services'
      environment to point at it. Also changed the `secrets/` volume mount
      for `api`/`worker` from fully read-only to additionally mounting
      `./secrets/data-keys` read-write — a real gap found during
      implementation: User Story 1's daily key-rotation buckets need both
      services to create/destroy key files there, which the original
      single-static-key-era read-only mount never had to allow.

**Checkpoint**: Environment ready for every story below.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The one shared migration (new tables + grants two stories
need) and the auth-layer `role` threading US2 and US4 both build on.

**CRITICAL**: No user story task can begin until this phase is complete.

- [X] T004 New Alembic migration
      `backend/migrations/versions/0003_production_hardening.py`:
      `CREATE TABLE retention_job_runs` and `CREATE TABLE
      finding_type_config_changes` (`data-model.md`'s exact column lists);
      `GRANT INSERT ON retention_job_runs, finding_type_config_changes TO
      app_role`; `GRANT UPDATE (base_points, version) ON finding_type_config
      TO app_role` (currently ungranted — `finding_type_config` has never
      had a writer before this feature). **Two corrections found during
      implementation**: (1) fixture users are NOT seeded in this migration
      — this codebase seeds users via `data-base/11-seed-data.sql` +
      `scripts/seed.py`, not a migration (`0001` has no user INSERTs at
      all; the "mirrors 0001's precedent" claim in this task's original
      text was wrong) — `ae-demo`/`admin-demo` added to `data-base/
      11-seed-data.sql` instead, with real Argon2id hashes so both roles
      can actually log in; (2) this task's original text also called for
      `GRANT UPDATE (payload_encrypted)`/`SELECT` on `raw_envelopes` to
      `shredder_role`, both wrong and since removed — `raw_envelopes.
      payload_encrypted` is `NOT NULL` and the DDL's own crypto-shredding
      design already makes key destruction alone sufficient there (see
      T015's note); the retention job's `shred_bucket()` never issues a
      `SELECT` either, so that grant was unnecessary too. Both excess
      grants were briefly applied then corrected in place (migration
      downgraded, grants manually revoked, corrected migration re-applied
      — not shipped as a stale grant followed by a second migration, since
      this feature has no external consumers yet). Verified: migration
      applies cleanly against a real Postgres 16 (`docker compose run --rm
      migrate` and, after the correction, `alembic downgrade`/`upgrade`
      directly against the running container), grants confirmed via `\dp`
      to be exactly minimal (`shredder_role`: `UPDATE (body_encrypted) ON
      events` only, nothing on `raw_envelopes`), both new users insert and
      are queryable.
- [X] T005 [P] Add `role: str | None` to `TokenRecord` in
      `backend/app/auth/application/ports.py` (`data-model.md`)
- [X] T006 Extend the SQL behind `get_by_hash`
      (`backend/app/auth/adapters/sqlalchemy_repository.py`) with a `JOIN
      users ON users.id = auth_tokens.user_id`, selecting `users.role`
      into the now-extended `TokenRecord` (depends on T005)
- [X] T007 Add `role: str | None` to `CurrentUser` and thread it through
      from `TokenRecord.role` in `get_current_user`
      (`backend/app/auth/application/dependencies.py`) (depends on T006).
      Verified: existing `tests/unit/test_auth.py` (7 tests) still passes
      unchanged against the real DB; `ruff`/`mypy --strict` clean on
      `app/auth/` and `app/config.py`.

**Checkpoint**: Migration applied, `role` flows from token to
`CurrentUser`. US1–US6 can now begin (US2/US4 additionally depend on T007
specifically; called out again in their own phases below).

---

## Phase 3: User Story 1 - Message bodies expire automatically, on schedule (Priority: P1) 🎯 MVP

**Goal**: Message bodies older than the retention window become
permanently unrecoverable once a day, automatically, while findings,
scores, and evidence citations survive.

**Independent Test**: `quickstart.md`'s User Story 1 section — seed an aged
event, run the job once, confirm `body_encrypted IS NULL` and
`retention_job_runs` logged the run; re-run confirms idempotency.

### Implementation for User Story 1

- [ ] T008 [P] [US1] Add `KeyStorePort` to
      `backend/app/ingestion/application/ports.py`: `current_bucket_id() ->
      str` (today's UTC date, `YYYY-MM-DD`), `resolve(bucket_id: str) ->
      Fernet`, `list_active_buckets() -> list[str]`, `destroy(bucket_id:
      str) -> None` (`research.md` Decision 1)
- [ ] T009 [P] [US1] Implement `FileKeyStore` in
      `backend/app/ingestion/adapters/key_store.py` (new file), implementing
      `KeyStorePort`: one Fernet key file per bucket under
      `settings.data_keys_dir`, generated lazily on first `resolve()` for an
      unseen bucket id; `list_active_buckets()` lists the directory;
      `destroy()` deletes a bucket's file (depends on T008)
- [X] T010 [US1] Implement `BucketedFernetEncryption` in
      `backend/app/ingestion/adapters/encryption.py` (new class alongside
      the existing `FernetEncryption`, both implementing `EncryptionPort`):
      constructor takes a `KeyStorePort`; `encrypt()` always uses today's
      bucket key; `decrypt()` tries every `list_active_buckets()` key in
      turn, raising `EncryptionKeyError` only if none succeed (`research.md`
      Decision 1's key-ring design — zero change to `EncryptionPort`'s
      signature) (depends on T008, T009). **Critical bug found and fixed
      during implementation, not at plan time**: without a fallback, every
      message body encrypted before this feature shipped becomes instantly
      unreadable the moment it deploys, since none of them belong to a
      bucket. Reproduced for real against this repo's own shared dev
      database (`tests/unit/test_profile_router.py` failed first). Fixed by
      adding an optional `legacy_key_path` constructor parameter, tried by
      `decrypt()` only after every bucket key fails — every composition
      site (T011) now passes `settings.encryption_key_path` as this
      fallback.
- [X] T011 [US1] Swap every composition-root construction of
      `FernetEncryption(settings.encryption_key_path)` to
      `BucketedFernetEncryption(FileKeyStore(settings.data_keys_dir),
      settings.encryption_key_path)` in `backend/app/main.py`,
      `backend/app/worker.py`, `backend/app/experience/adapters/
      ask_router.py`, `backend/app/experience/adapters/dashboard_router.py`,
      `backend/app/experience/adapters/draft_router.py`,
      `backend/app/experience/adapters/evidence_router.py`, and
      `backend/app/context/adapters/profile_router.py` (7 call sites — no
      other change needed in any of these files; depends on T010). **Scope
      grew during implementation**: 2 more composition sites this task's
      original list missed, found by grep, not assumed — `backend/scripts/
      run_readers.py` and `backend/scripts/run_narrator.py`, both
      decrypt-only call sites for readers/narrator.
- [X] T012 [US1] Change `AppendEventUseCase`, `RunCollectorUseCase`, and
      `DetectAbsenceUseCase` (`backend/app/ingestion/application/
      use_cases.py`) from a constructor-injected `data_key_ref: str` to a
      constructor-injected `key_store: KeyStorePort`, calling
      `key_store.current_bucket_id()` inside `execute()` (not cached at
      construction, so a long-running process rolls to a new bucket at
      midnight UTC correctly) (depends on T008)
- [X] T013 [US1] Update the three composition sites that construct the
      classes from T012 — `backend/app/worker.py`,
      `backend/scripts/run_collector.py`, `backend/scripts/
      seed_score_fixture.py` — to pass `key_store=FileKeyStore(settings.
      data_keys_dir)` instead of `data_key_ref=settings.encryption_key_id`
      (depends on T009, T012)
- [X] T014 [P] [US1] Implement `shredder_session_factory` in
      `backend/app/db.py`: a second `async_sessionmaker` built from
      `settings.database_url` with its credentials replaced by
      `("shredder_role", settings.shredder_role_password)` via SQLAlchemy's
      `URL.set()` — the retention job's only writer of `body_encrypted`,
      exercising the `shredder_role` grant for real for the first time
      (`research.md` Decision 1). Verified: connecting and running
      `SELECT current_user` through it against the real container returns
      `shredder_role`, not the default unrestricted user.
- [X] T015 [US1] Implement `RunRetentionUseCase` in
      `backend/app/ingestion/application/use_cases.py`: resolves every
      bucket from `KeyStorePort.list_active_buckets()` whose bucket-day + 1
      is older than `settings.retention_window_days` (a new pure helper,
      `is_bucket_expired`, `backend/app/ingestion/domain/retention.py`);
      for each, calls `KeyStorePort.destroy(bucket_id)` then, via the T014
      shredder session, `UPDATE events SET body_encrypted = NULL WHERE
      data_key_ref = :bucket_id` — **`raw_envelopes.payload_encrypted` is
      deliberately never touched, a correction found during
      implementation**: that column is `NOT NULL`, and the DDL's own
      crypto-shredding design already makes key destruction alone
      sufficient there (see `SqlAlchemyRetentionJobRepository`'s docstring,
      `backend/app/ingestion/adapters/sqlalchemy_repositories.py`); writes
      one `retention_job_runs` row (`started_at`, `completed_at`,
      `buckets_evaluated`, `buckets_shredded`, `status`) via the normal
      session; on any exception, writes `status = failed` + `error_detail`,
      emits `logger.error(...)` via the module's standard
      `logging.getLogger(__name__)` (matching `worker.py`'s existing
      logging precedent — this alone fully satisfies FR-004a's "surface
      the failure," independent of User Story 3; `/speckit-analyze`
      finding I1), and re-raises (`app.worker`'s job-runner wraps this in
      a try/except that logs and lets APScheduler's own next-run schedule
      retry, no separate retry loop) (depends on T008, T009, T014, T004).
      **A second real bug found only by actually running this against
      Postgres, not by inspection**: `shredder_role`'s original grant
      (`UPDATE (body_encrypted)` only) let it write the column but not
      evaluate the `UPDATE ... WHERE data_key_ref = ... AND body_encrypted
      IS NOT NULL` predicate — Postgres requires read access to every
      column a `WHERE` clause references. Fixed with a narrow `GRANT
      SELECT (data_key_ref, body_encrypted) ON events TO shredder_role`
      added to the T004 migration (not a blanket `SELECT ON events`).
      Verified: `tests/ingestion/test_retention_real_db.py` (T020) passes
      against the real, freshly re-applied migration.
- [X] T016 [US1] Register the retention job on the existing
      `BackgroundScheduler` in `backend/app/worker.py`, alongside absence
      detection and the hourly score recompute, scheduled daily; add a
      `--run-once retention` CLI flag mirroring the existing
      `--run-once absence`/`--run-once score` pattern for manual/quickstart
      triggering (depends on T015). **Correction found during
      implementation**: no `--run-once` mechanism actually existed before
      this task (`worker.py` had no `argparse` at all) — this task's
      original text wrongly assumed one to "mirror." Added a real
      `argparse`-based `--run-once {absence,score,retention}` flag from
      scratch. Verified: `uv run python -m app.worker --run-once
      retention` against the real container inserted one real
      `retention_job_runs` row.
- [X] T017 [US1] Catch `EncryptionKeyError` at the **adapter** layer only —
      inside `_quoted_text()` (`backend/app/experience/adapters/
      sqlalchemy_repository.py`, the actual single call site for
      `encryption.decrypt()` shared by the evidence trace, dashboard pulse
      timeline, and every other read path that renders event text) — and
      translate it there into a fixed marker string ("original message no
      longer available — retention period expired") instead of the raw
      decrypted text. `GetEvidenceTraceUseCase` and every other caller
      never import or see `EncryptionKeyError` itself, keeping the
      Application→Adapter import boundary intact (P8) — the same class of
      violation feature 008's `narration_v1.py` incident already hit once
      (`/speckit-analyze` finding C1) (depends on T010). Verified: existing
      `tests/experience/` evidence tests (21/21) still pass unchanged.
- [X] T018 [P] [US1] Update the existing tests that reference
      `data_key_ref=settings.encryption_key_id` to use a fake `KeyStorePort`
      instead: `backend/tests/unit/test_simulated_collector.py`,
      `backend/tests/unit/test_absence_collector.py`,
      `backend/tests/readers/test_run_readers_use_case.py` (depends on
      T012). **Scope grew during implementation**: a full-suite run (not
      just these 3 files) found 5 more files still constructing the old
      `FernetEncryption(settings.encryption_key_path)` directly —
      `tests/unit/test_replay.py`, `tests/experience/
      test_ask_agent_latency.py`, `tests/golden_replay/test_placeholder.py`,
      `tests/scoring/test_worked_example.py` — all switched to
      `BucketedFernetEncryption(FileKeyStore(...), settings.
      encryption_key_path)`, the same swap every production composition
      site got. Also found and fixed a real, severe bug this task's own
      testing surfaced: `BucketedFernetEncryption.decrypt()` originally had
      no fallback to the legacy single-key file, so every message body
      encrypted before this feature shipped would have become permanently
      unreadable the moment it deployed — not a hypothetical, reproduced
      directly against this repo's own shared dev database
      (`tests/unit/test_profile_router.py`'s reload-replay path failed
      first). Fixed by adding an optional `legacy_key_path` fallback to
      `BucketedFernetEncryption`, tried only after every bucket key fails.
      **Verified**: full suite went from 18 failing / 254 passing before
      this fix to 1 failing / 268 passing after — the 1 remaining
      (`test_run_readers_use_case.py`'s `recurring_issue` citing only 1
      event) is the exact pre-existing, documented "shared cumulative dev
      database" flake `specs/ROADMAP.md` already logged for features
      009/010, reproduced identically on the unmodified pre-feature-011
      code (confirmed via `git stash`), not a regression this feature
      introduces.
- [X] T019 [P] [US1] Write `backend/tests/unit/test_key_store.py` — pure,
      no DB: `current_bucket_id()` returns today's date; `resolve()` on an
      unseen bucket lazily creates a key; `resolve()` on a known bucket
      returns the same key twice; `destroy()` removes it from
      `list_active_buckets()` and a subsequent `resolve()` of the same id
      creates a *new*, different key (proving destruction is real, not
      cached). 5/5 passing.
- [X] T020 [US1] Write `backend/tests/ingestion/test_retention_real_db.py`
      — real-DB: seed an event with `data_key_ref` set to a bucket dated
      past `retention_window_days` and a real key written for it; run
      `RunRetentionUseCase`; assert `body_encrypted IS NULL` and one
      `retention_job_runs` row with `status = succeeded`; re-run and assert
      no error (idempotency, FR-003); force a mid-run failure (a fake
      `KeyStorePort` wrapping the real one, raising on its second
      `destroy()` call) and assert a `status = failed` row with
      `error_detail` set and the first bucket's shred not rolled back
      (FR-004a). 2/2 passing — and this test is what surfaced both real
      bugs T010/T015 document (the missing legacy-key fallback and the
      missing `SELECT` grant), neither found by inspection.

**Checkpoint**: User Story 1 is fully functional and independently
testable — the retention job runs daily, shreds provably, survives a
partial failure, and every other read path degrades honestly instead of
erroring. `quickstart.md`'s User Story 1 section passes. Verified: 97/97
targeted tests pass against a freshly reset, migrated, and seeded database
(`tests/ingestion/`, `test_key_store.py`, `test_hash_chain.py`,
`test_simulated_collector.py`, `test_absence_collector.py`,
`test_replay.py`, `test_profile_router.py`, `test_auth.py`,
`tests/experience/`); `ruff`/`mypy app` clean on every touched file.

**Pre-existing issue found, not fixed (genuinely out of this feature's
scope)**: running the **entire** backend suite together against a freshly
reset, empty database — not just US1's own tests — fails 5 tests,
including `tests/unit/test_hash_chain.py`'s own hash-chain-integrity
assertion, with `verify_hash_chain()` reporting real broken links.
Rigorously confirmed via `git stash` + an equally fresh database that this
reproduces identically on the unmodified, pre-feature-011 codebase — not a
regression this feature introduces. Root cause (not fully diagnosed):
`scripts/run_collector.py` (feature 003) inserts `demo/fixtures/
meridian-week.json`'s fixed 2026 calendar-date events without shifting
them relative to the ledger's current floor, unlike every other test in
this suite that carefully anchors to `ledger_floor(session)` first
(`tests/conftest.py`) — when a full-suite run reaches a test that calls it
(`tests/scoring/test_worked_example.py`) after other tests have already
advanced the floor far into the future, the fixed-date insert violates the
global `occurred_at`-order-of-insertion invariant `EventRepositoryPort.
append`'s docstring requires, breaking the chain for every test that runs
after it in the same session. Flagged here per this repository's own
established standard for genuine findings (`specs/ROADMAP.md`'s Log
entries for features 003/004/008/009/010) rather than silently patched or
ignored — worth a dedicated fix (most likely: floor-anchor `scripts/
run_collector.py`'s fixture timestamps the same way `tests/unit/
test_simulated_collector.py`'s own `_build_fixture` helper already does)
before any future feature's own full-suite verification pass.

---

## Phase 4: User Story 2 - Account executives get a read-only view (Priority: P2)

**Goal**: An `account_executive`-role user reaches the dashboard/evidence/
coverage screens exactly like a `cs_lead`, and is refused, cleanly, on
every write-capable route. No other role's access changes.

**Independent Test**: `quickstart.md`'s User Story 2 section — log in as
`ae-demo` (T004), confirm `200` on `GET /api/dashboard`, `403` on
`POST /api/feedback`; confirm `marta` (`cs_lead`) is unaffected.

**Depends on**: Foundational T007 (`CurrentUser.role`).

### Implementation for User Story 2

- [X] T021 [US2] Add `require_full_access` to
      `backend/app/auth/application/dependencies.py`: wraps
      `get_current_user`, raises `HTTPException(403, "This action is not
      available for your account.")` when `role == "account_executive"`,
      otherwise returns the same `CurrentUser` (`research.md` Decision 2,
      `contracts/rbac.md`); on every call (both outcomes), emits one
      structured log line via `logging.getLogger(__name__)` — `{"event":
      "access_decision", "user_id": ..., "role": ..., "outcome": "allowed"
      | "denied"}` — satisfying FR-008's "record which role a request was
      authorized under" with the role *as it was at decision time*, not a
      later `users.role` lookup (`/speckit-analyze` finding G1) (depends on
      T007)
- [X] T022 [US2] Swap `Depends(get_current_user)` for
      `Depends(require_full_access)` on exactly the routes
      `contracts/rbac.md` names: `backend/app/context/adapters/
      feedback_router.py` (`POST /api/feedback`),
      `backend/app/context/adapters/profile_router.py`
      (`POST /api/profile/reload` only — the new `POST /api/profile` gets
      this gate directly when US5 creates it),
      `backend/app/experience/adapters/ask_router.py` (`POST /api/ask`),
      `backend/app/experience/adapters/draft_router.py` (all three routes:
      `POST /api/drafts`, `.../copy`, `.../log-as-sent`). Every read-only
      route (`dashboard_router.py`, `evidence_router.py`,
      `coverage_router.py`, `GET /api/profile`) is explicitly left
      unchanged (depends on T021)
- [X] T023 [P] [US2] Write
      `backend/tests/auth/test_require_full_access.py` — pure, `TokenRepositoryPort`
      faked: an `account_executive`-role token raises `403`; every other
      seeded role value (`cs_lead`, `support_lead`, `engineering_manager`,
      `admin`, `None`) passes through unchanged; both cases assert the
      `access_decision` log line fires with the correct `role`/`outcome`
      (via `caplog`) — FR-008. 7/7 passing.
- [X] T024 [US2] Write `backend/tests/auth/test_rbac_real_db.py` — real-DB,
      parametrized over `contracts/rbac.md`'s full route table: `ae-demo`'s
      token gets `403` on every write-capable route and never `403` on any
      read-only one; `marta`'s token never gets `403` anywhere, proving
      FR-007's "no new restriction" (depends on T022, T004's `ae-demo` seed
      row). 20/20 passing. **Implementation notes**: (1) `/api/ask` reaches
      real business logic for a non-AE token in this environment (no
      `ANTHROPIC_API_KEY`) — the test's `client` fixture uses
      `ASGITransport(app=app, raise_app_exceptions=False)` so that surfaces
      as a real `500`, matching what an actual deployed server returns,
      not a raised exception the test would otherwise choke on; (2) tests
      verify the authorization layer specifically (well-formed bodies
      referencing nonexistent IDs, asserting on `403` vs. not-`403` rather
      than full business-logic correctness, which is already covered
      elsewhere) since exercising every route's true happy path would
      require the full collector→readers→scoring pipeline having already
      run.

**Checkpoint**: User Story 2 is fully functional and independently
testable — an account executive sees the dashboard, never a write.
`quickstart.md`'s User Story 2 section passes.

---

## Phase 5: User Story 3 - Operators can see what the running system is doing (Priority: P3)

**Goal**: Collector runs, score recomputations, reader executions, and Ask
agent queries each produce a trace with duration and outcome; the product
keeps working identically if the trace backend is unreachable.

**Independent Test**: `quickstart.md`'s User Story 3 section — trigger a
collector run/score recompute/Ask query, confirm one span per operation in
the OTel collector's log output; stop the exporter and confirm no
regression in any endpoint's status code.

### Implementation for User Story 3

- [X] T025 [P] [US3] Implement `backend/app/observability/adapters/
      tracing.py` (new package, adapters-only — `research.md` Decision 6):
      `setup_tracing()` configures the OTel SDK `TracerProvider` with an
      OTLP exporter pointed at `settings.otel_exporter_endpoint` (a no-op/
      console exporter when empty, never a hard failure — FR-012); a
      `traced(operation: str)` context manager records start time, duration,
      and outcome (`success`/`failure`/`degraded`, the last passed
      explicitly by the caller) as a span. Implemented as
      `settings.otel_exporter_otlp_endpoint` (T001's naming correction);
      `BatchSpanProcessor` used deliberately (not `SimpleSpanProcessor`) so
      an unreachable OTLP endpoint exports asynchronously in a background
      thread and never blocks or fails the calling request (FR-012).
      Verified: `uv run python -m app.worker --run-once retention` printed
      a real span (`outcome: success`, real `duration_ms`) via the console
      exporter.
- [X] T026 [US3] Call `setup_tracing()` once at composition-root startup in
      `backend/app/main.py` and `backend/app/worker.py` (depends on T025)
- [X] T027 [US3] Wrap `backend/app/worker.py`'s `_run_absence_detection`,
      `_run_score_recompute`, and User Story 1's already-shipped, already-
      independently-logging retention job runner (T015) with `traced(...)`
      — an **enhancement** layered on top of T015's existing
      `logger.error()` call, not a prerequisite for FR-004a (`/speckit-
      analyze` findings I1/I2: not marked `[P]` because it genuinely
      depends on US1's T016 having already run, unlike every other task in
      this phase) (depends on T025, T016)
- [X] T027a [P] [US3] Wrap `RunCollectorUseCase.execute`
      (`backend/app/ingestion/application/use_cases.py`) with
      `traced("collector_run")` at its composition sites
      (`backend/scripts/run_collector.py` and any other place a collector
      run is triggered) — the "collector run" FR-009/FR-011 explicitly name
      as a traced operation type, previously uncovered (`/speckit-analyze`
      finding G2) (depends on T025). Wrapped only the collector-execute
      call, not the trailing replay call in the same script, to keep the
      span scoped to the actual "collector run" operation.
- [X] T028 [P] [US3] Wrap `RunReadersUseCase.execute`'s per-reader loop
      (`backend/app/readers/application/use_cases.py`) with
      `traced("reader_execution")` per reader, recording `degraded` when a
      reader raises and is isolated (FR-014's existing per-reader failure
      isolation) rather than `failure` (depends on T025). **Architecture
      note**: `traced()` is imported directly into this application-layer
      file, deliberately not gated behind a new port — treated as
      infrastructure-utility-grade, the same way this codebase already
      calls Python's stdlib `logging` directly from application-layer code
      (e.g. `RunRetentionUseCase`) with no dedicated port, distinct from a
      business-domain-relevant concrete type like `EncryptionKeyError`
      (kept out of the application layer for exactly that reason, T017).
      Verified: `.importlinter`'s `readers-application-purity` contract
      (which forbids `anthropic`/`openai`/`app.readers.adapters`, not
      `app.observability`) still passes; all 3 contracts kept.
- [X] T029 [P] [US3] Wrap `backend/app/experience/adapters/
      ask_router.py`'s `POST /api/ask` handler body with
      `traced("ask_query")` (depends on T025)
- [X] T029a [P] [US3] Wrap `backend/app/experience/adapters/
      dashboard_router.py`'s `GET /api/dashboard` handler body with
      `traced("dashboard_load")` — the "dashboard-load" latency FR-010/
      SC-003 explicitly name, previously uncovered (`/speckit-analyze`
      finding G2) (depends on T025). Wrapped only the `use_case.execute()`
      call, not the subsequent response-model construction.
- [X] T030 [P] [US3] Write `backend/tests/unit/test_tracing.py` — pure: a
      successful `traced()` block records `outcome = success` and a
      `duration_ms >= 0`; a block raising an exception records
      `outcome = failure` and re-raises (the context manager never
      swallows the original exception, matching FR-012's "unaffected"
      guarantee); a block calling `.mark_degraded()` records
      `outcome = degraded`. 3/3 passing. **Bug found and fixed while
      writing this test, not at plan time**: OTel's global `TracerProvider`
      can only be set once per process — the first version of this test
      fought that restriction directly (`trace.set_tracer_provider`) and
      passed in isolation but failed whenever run alongside any other test
      file that had already triggered `setup_tracing()` via an `app.main`/
      `app.worker` import (a real race, reproduced and confirmed via `uv
      run pytest tests/auth/ tests/unit/ -q`). Fixed by monkeypatching
      `get_tracer` directly inside `app.observability.adapters.tracing`
      instead of touching the global provider singleton at all — passes
      reliably regardless of import/execution order.

**Checkpoint**: User Story 3 is fully functional and independently
testable — every FR-009-named operation is traced, and pulling the
exporter never breaks a request. `quickstart.md`'s User Story 3 section
passes.

---

## Phase 6: User Story 4 - Base weights can be recalibrated without a code deploy (Priority: P4)

**Goal**: An `admin`-role user changes a finding type's base weight; the
next score computation uses it; every already-computed score run stays
byte-identical; every other role is refused.

**Independent Test**: `quickstart.md`'s User Story 4 section — `PATCH` a
weight as `admin-demo`, confirm a new `weight_edit_replay` score run with a
different `finding_type_config_version`, confirm the prior run unchanged,
confirm `403` for `marta`.

**Depends on**: Foundational T004 (migration), T007 (`CurrentUser.role`).

### Implementation for User Story 4

- [ ] T031 [US4] Add `require_admin` to
      `backend/app/auth/application/dependencies.py`: wraps
      `get_current_user`, raises `HTTPException(403, ...)` unless
      `role == "admin"`; on every call (both outcomes), emits an
      `access_decision` structured log line in the same shape T021
      introduces for `require_full_access` (FR-008, `/speckit-analyze`
      finding G1) — a few duplicated lines between the two dependencies in
      this shared file, deliberately not factored into a cross-story
      shared helper, so US4 has no dependency on US2's delivery order
      (P10; if both stories land in the same PR, feel free to extract the
      shared three-line log call at that point, not before) (depends on
      T007)
- [ ] T031a [P] [US4] Write `backend/tests/auth/test_require_admin.py` —
      pure, `TokenRepositoryPort` faked: a non-`admin` token (including
      `cs_lead`) raises `403`; an `admin` token passes through unchanged;
      both cases assert the `access_decision` log line fires with the
      correct `role`/`outcome` (FR-008) (depends on T031)
- [X] T032 [P] [US4] Add `FindingTypeConfigWritePort` to
      `backend/app/scoring/application/ports.py`:
      `update_base_points(finding_type: str, new_base_points: float,
      changed_by_user_id: UUID) -> FindingTypeConfigChangeResult` (returns
      the new `finding_type_config.version` and the change's `id`)
      (`data-model.md`). `FindingTypeConfigChangeResult` also carries
      `changed_at` (the real, DB-generated timestamp via `RETURNING`, not a
      client-side approximation) — a small addition beyond this task's
      original text, needed for `contracts/weight-recalibration.md`'s
      response schema to be accurate.
- [X] T033 [US4] Implement `SqlAlchemyFindingTypeConfigWriter` in
      `backend/app/scoring/adapters/sqlalchemy_repository.py`: one
      transaction — `SELECT base_points FROM finding_type_config WHERE
      finding_type = :ft FOR UPDATE` (404 if no row), `UPDATE
      finding_type_config SET base_points = :new, version = :new_version`
      (a fresh version string, e.g. a UUID or incrementing suffix),
      `INSERT INTO finding_type_config_changes (...)` (depends on T032,
      T004). **Real bug found by `tests/scoring/
      test_weight_recalibration_real_db.py` (T038), not by inspection**:
      `finding_type_config.version` is physically a per-row column, but
      `get_finding_type_config_version()` (shipped since feature 004) reads
      it via `SELECT version FROM finding_type_config LIMIT 1` — no
      `ORDER BY` — meaning every row has always been assumed to share one
      identical value. The first version of this writer bumped only the
      *changed* row's version, so `LIMIT 1` kept returning an arbitrary
      *other*, unchanged row's stale version — `score_runs.
      finding_type_config_version` silently never reflected the edit.
      Fixed by updating every row's `version` column together, keeping the
      existing shared-version contract intact rather than changing the
      read side.
- [X] T034 [US4] Implement `UpdateFindingTypeWeightUseCase` in
      `backend/app/scoring/application/use_cases.py`, alongside
      `RecomputeScoreUseCase`: validates `new_base_points >= 0` (422 via a
      new `InvalidWeightError`), calls T033's writer, then calls the
      existing `RecomputeScoreUseCase.execute(trigger="weight_edit_
      replay")` (`research.md` Decision 3 — the same trigger-value/
      orchestration pattern `profile_router.py`'s `reload_profile` already
      uses for `profile_edit_replay`) (depends on T033)
- [X] T035 [US4] Implement `backend/app/scoring/adapters/weight_router.py`
      (new file): `PATCH /api/admin/finding-types/{finding_type}`,
      `Depends(require_admin)`, `changed_by_user_id` from the bearer token;
      catches "no such finding type" → `404`, `InvalidWeightError` → `422`
      (`contracts/weight-recalibration.md`) (depends on T034, T031)
- [X] T036 [US4] Register `weight_router` in `backend/app/main.py`
      (depends on T035)
- [X] T037 [P] [US4] Write `backend/tests/unit/
      test_update_finding_type_weight_use_case.py` — `FindingTypeConfig
      WritePort`/`RecomputeScoreUseCase` faked: a valid update calls the
      writer then triggers recompute with `trigger="weight_edit_replay"`; a
      negative `new_base_points` raises `InvalidWeightError` without
      calling the writer. 2/2 passing.
- [X] T038 [US4] Write `backend/tests/scoring/
      test_weight_recalibration_real_db.py` — real-DB against the worked
      example: note `broken_response_promise`'s current `base_points`/
      `finding_type_config.version`; `PATCH .../broken_response_promise
      {"base_points": 25}` as `admin-demo` → `200`, new
      `finding_type_config_changes` row, new `score_runs` row with
      `trigger = weight_edit_replay` and a different
      `finding_type_config_version`; fetch the prior `score_run` by id →
      byte-identical `score`/`score_contributions` (FR-015); repeat as
      `marta` (`cs_lead`) → `403`, no row inserted anywhere; repeat with a
      nonexistent `finding_type` → `404`; repeat with `base_points: -1` →
      `422` (depends on T036, T004's `admin-demo` seed row). 4/4 passing.
      **Two implementation notes**: (1) the shared dev database's most
      recent `coverage_reports` row was left degraded by an earlier,
      unrelated test in this session — `RecomputeScoreUseCase` correctly
      freezes instead of computing fresh when degraded (REQ-M6-26,
      existing behavior), so this test inserts one healthy coverage report
      first, the same "anchor to real state, don't assume" pattern
      `tests/conftest.py`'s `ledger_floor` already establishes; (2) the
      weight-restore cleanup at the end of the main test is wrapped in
      `try`/`finally` — an early draft without it left `broken_response_
      promise`'s seed weight silently drifted upward by 5 on every failed
      debug run, which then broke `tests/scoring/test_worked_example.py`
      for an unrelated-looking reason (a real, self-inflicted bug caught
      by running the full `tests/scoring/` suite together, not this file
      alone, and fixed at the DB level plus in this test).

**Checkpoint**: User Story 4 is fully functional and independently
testable — an admin recalibrates a weight, the audit trail is complete,
past scores are untouched, non-admins are refused. `quickstart.md`'s User
Story 4 section passes.

---

## Phase 7: User Story 5 - CS lead edits the client profile without touching YAML (Priority: P5)

**Goal**: `POST /api/profile` accepts a structured JSON profile, reusing
`SubmitProfileUseCase` unmodified; the frontend's long-empty
`profile-editor/` slot gets a real form.

**Independent Test**: `quickstart.md`'s User Story 5 section — `GET
/api/profile`, edit one field via `POST /api/profile`, confirm
`version_number` increments and the dashboard reflects it; submit an
invalid edit, confirm `422` with no new version.

**Depends on**: User Story 2's `require_full_access` (T021) for the new
route's auth gate — if US2 hasn't shipped yet, this route can temporarily
use `get_current_user` and be upgraded in one line once US2 lands, so US5
is still independently developable.

### Implementation for User Story 5

- [X] T039 [US5] Add a `ProfileSubmitRequest` Pydantic model to
      `backend/app/context/adapters/profile_router.py`, matching
      `contracts/profile-editor.md`'s request shape exactly
      (`stakeholders`, `product_areas`, `commitments`, `renewal_date`,
      `contract_value_band`, `client_name`, `exclusions`,
      `communication_norms`). **Superseded by a simpler, more correct
      approach found during implementation**: no separate
      `ProfileSubmitRequest` model was created at all. `load_profile_yaml`
      already builds a `ClientProfileInput` (`app.context.domain.
      profile_schema`) — a Pydantic model, already fully validated
      (influence/criticality/contract_value_band enums, the "at least one
      signs_renewal" cross-field rule) — so the route accepts
      `ClientProfileInput` directly as its body type. Zero duplicated
      validation logic, and the request genuinely is byte-identical to
      what the YAML path already produces, more faithfully satisfying
      `research.md` Decision 4 than a hand-mapped parallel model would
      have. `contracts/profile-editor.md` corrected to match.
- [X] T040 [US5] Implement `POST /api/profile` in the same file: converts
      `ProfileSubmitRequest` into the same `ClientProfile` domain object
      `load_profile_yaml` already builds, calls the existing, unmodified
      `SubmitProfileUseCase.execute(profile, authored_by_user_id=...)`,
      `Depends(require_full_access)` (`research.md` Decision 4 — zero
      change to `SubmitProfileUseCase`/`ReplayUseCase`) (depends on T039,
      T021). No conversion step needed (see T039) — `ClientProfileInput`
      goes straight into `SubmitProfileUseCase.execute()` unchanged.
- [X] T041 [P] [US5] Create `frontend/src/profile-editor/schema.ts` — Zod
      schema mirroring `ProfileSubmitRequest`, per constitution P11.
      **Corrected during implementation**: mirrors `ClientProfileInput`
      (the real backend model, T039/T040's finding), not the originally
      planned, never-actually-built `ProfileSubmitRequest`. Deliberately no
      `z.default()` anywhere in the schema — it makes a field's input type
      optional while its output type stays required, which `useForm<T>`
      can't reconcile into one type; `toFormValues()` (T043) already
      populates every field explicitly, so no schema-level default is
      needed.
- [X] T042 [US5] Create `frontend/src/profile-editor/use-profile.ts` —
      TanStack Query `useProfile()` (GET) and `useSubmitProfile()`
      (POST mutation), matching `frontend/src/evidence/use-feedback.ts`'s
      existing pattern from feature 010 (depends on T041)
- [X] T043 [US5] Create `frontend/src/profile-editor/
      profile-editor-form.tsx` — React Hook Form bound to T041's schema,
      rendering stakeholders/exclusions/renewal date/contract value band/
      communication norms as editable fields, inline field-level `422`
      error display (depends on T042). **Real gap found while wiring
      this**: `GET /api/profile`'s response never carried `exclusions`/
      `communication_norms` at all, even before this feature — FR-017
      requires viewing both. Fixed by extending `ProfileVersionSummary`
      (`app.context.application.ports`), both its adapter construction
      sites, and `ProfileResponse` with the two missing fields (`data-base`
      columns already existed since feature 003; only the read path never
      surfaced them). Scope decision, documented in the component's own
      comment: `business_goals`/`communication.working_hours`/`timezone`/
      `languages`/`history` aren't exposed for editing (the read response
      is still too reduced to round-trip those safely) and are resubmitted
      with fixed defaults on every save — a deliberate limitation matching
      FR-017's literal scope, not a silent data-loss bug. **Bug found and
      fixed by this story's own tests (T046), not by inspection**:
      `useForm()` runs before any data has loaded, so every array field
      needs a real `defaultValues` object (not left `undefined`) or the
      exclusions `Controller`/stakeholder `useFieldArray` bindings throw on
      the first render.
- [X] T044 [US5] Register a `/profile` route in `frontend/src/App.tsx`
      (`<Route path="/profile" element={<ProtectedRoute><ProfileEditorPage
      /></ProtectedRoute>} />`, mirroring the existing `/coverage` route)
      and add a nav link to it wherever `/coverage`'s own nav entry lives
      (depends on T043). **Correction found during implementation**: no
      nav bar/nav-link component exists anywhere in this codebase yet —
      not for `/coverage`, not for `/dashboard` — so there was no existing
      nav entry to mirror; only the route registration applies.
- [X] T045 [P] [US5] Write `backend/tests/context/
      test_profile_editor_real_db.py` — real-DB: `POST /api/profile` with
      one changed stakeholder → `200`, `version_number` incremented,
      `authored_by_user_id` set; a submission referencing a nonexistent
      stakeholder in a commitment → `422`, `version_number` unchanged; an
      `account_executive` token → `403` (depends on T040). 3/3 passing.
- [X] T046 [P] [US5] Write `frontend/src/profile-editor/
      profile-editor-form.test.tsx` — renders current profile data, submits
      a change, asserts the mutation fires with the right payload; renders
      a `422` response as inline field errors (depends on T043). 3/3
      passing — this test file is what caught T043's `useForm()` defaults
      bug above.

**Checkpoint**: User Story 5 is fully functional and independently
testable — the profile editor UI works end to end, `SubmitProfileUseCase`
untouched. `quickstart.md`'s User Story 5 section passes.

---

## Phase 8: User Story 6 - The system reads from the Post-MVP sources (Priority: P6)

**Goal**: Slack Connect, CSAT/NPS, and Calendar/meeting-transcript data
(fixture-driven, `research.md` Decision 5) feed the Absence, Relationship,
Usage, Tone, and newly-activated Meeting readers; a client with none of the
three connected is unaffected.

**Independent Test**: `quickstart.md`'s User Story 6 section — extend the
fixture, run the collector, confirm `GET /api/coverage` shows the new
source and a downstream reader consumes it; confirm feature 010's existing
quickstart still reproduces unchanged (FR-024).

### Implementation for User Story 6

- [X] T047 [US6] Extend `backend/demo/fixtures/meridian-week.json` with
      new `slack`/`csat`/`calendar` items. **Corrected during implementation
      (plan-vs-actual drift found before writing any code):** `data-model.md`
      and this task both assumed the fixture was nested per-source top-level
      arrays (`{"gmail": [...], "zendesk": [...], ...}`) mirroring
      `research.md` Decision 5's own description — the real, committed file
      is a single **flat array**, each item carrying its own `source_type`
      discriminator (confirmed by reading the file directly, not by
      inspection of the docs). New items follow that real shape. The
      original 14-item content is preserved verbatim as
      `backend/demo/fixtures/meridian-week-phase1-only.json` — needed for
      T060's FR-024 regression check once `meridian-week.json` itself
      permanently gains Post-MVP data.
- [X] T048 [P] [US6] Implement `_normalize_slack` in `simulated_collector.py`
      (depends on T047).
- [X] T049 [P] [US6] Implement `_normalize_csat` in the same file. **Refined
      during implementation:** the written comment (if present) goes into
      `Envelope.payload_text` (the field every other source already
      encrypts-at-rest through), not a `structured_payload["payload_text"]`
      key as literally worded above — `structured_payload` is stored as
      plaintext JSONB (`data-base/03-schema-ledger.md`), and a client's
      survey comment is exactly the kind of sensitive text every other
      source's body is already encrypted for. `structured_payload` instead
      carries `score` and a `has_comment` boolean marker, so
      `SqlAlchemyMessageEventRepository` (Tone/Intent's shared corpus) can
      decide whether a `survey_response` row is worth decrypting without
      ever decrypting a score-only response just to find out it has nothing
      to read (depends on T047).
- [X] T050 [P] [US6] Implement `_normalize_calendar` in the same file.
      **Correction found during implementation:** the resulting `Envelope`'s
      `source_type` is `"transcripts"`, not `"calendar"` — `sources.
      source_type` is looked up as a global singleton per value
      (`get_or_create_source`), and `"calendar"` is already claimed by
      `DetectAbsenceUseCase.ABSENCE_SOURCE_TYPE` for its own internally
      generated absence events (feature 005). The `source_type` enum
      (`data-base/10-ddl-appendix.md`) already carries both `calendar` and
      `transcripts` as distinct values for exactly this reason — the
      fixture's own dispatch key stays `"calendar"` (human-readable,
      `SimulatedCollector.normalize()`'s lookup only), the Envelope's
      `source_type` is `"transcripts"`. Also implements FR-023's consent
      gate directly in `SimulatedCollector.fetch()` — see T059's note
      (depends on T047).
- [X] T051 [US6] Fill in `meeting_reader.py` — `MeetingReader(Reader)`,
      mirroring `IntentReader`'s single-call shape (direct interpretation,
      no baseline). **Scope correction found while implementing:** FR-023
      says the system SHALL NEVER *collect* a transcript lacking consent —
      stronger than "the reader abstains on it." Consent is therefore
      enforced once, at `SimulatedCollector.fetch()` (T050), not re-checked
      here: `MeetingTranscriptRepositoryPort.list_all()` structurally cannot
      return a non-consented transcript, so there is nothing left for this
      reader to check (documented in both files' docstrings). Emits
      `finding_type = "meeting_commitment"` — REQ-M5-14 never named one, and
      `data-base/11-seed-data.sql` never seeded a config row for it (unlike
      every other reader's finding_type); added via new migration
      `0004_meeting_finding_type` + a matching `data-base/11-seed-data.sql`
      row for fresh installs (depends on T050).
- [X] T052 [US6] Added `MeetingReader` to `scripts/run_readers.py`'s readers
      list (depends on T051).
- [X] T053 [US6] **Confirmed via reading the real code, not assumed:**
      `absence_reader.py` needs **zero code changes**. `DetectAbsenceUseCase.
      last_contact_at()` (`SELECT MAX(occurred_at) FROM events WHERE
      event_type != 'absence'`) is already fully source-agnostic — a
      Slack-sourced `message` event counts as "contact" automatically. This
      task's own original wording ("extend absence_reader.py") was a
      plan-time assumption `research.md` Decision 5 had already correctly
      called "an input-data change, not a reader-interface change" — this
      correction just makes that explicit against the actual query
      (depends on T048).
- [X] T054 [US6] **Confirmed via reading the real code:** `relationship_
      reader.py` / `SqlAlchemyRelationshipContext` also need **zero code
      changes** — both `active_stakeholder_ids(since)` (`SELECT DISTINCT
      stakeholder_id FROM events WHERE stakeholder_id IS NOT NULL AND
      occurred_at >= :since`) and `most_recent_event_for_stakeholder()`
      query the source-agnostic `events` table with no `source_type`
      filter. Same correction as T053 (depends on T048).
- [X] T055 [US6] Extended `ComputeRollupsUseCase` (not `usage_reader.py`
      itself) to also project `survey_response` events into `rollups` as
      `subject_type="stakeholder", metric="csat_score"`, and extended
      `UsageReader.interpret()` to route `subject_type == "stakeholder"`
      rows to a new `csat_deviation` finding_type instead of
      `usage_deviation` — a seeded row for exactly this finding_type
      (`data-base/11-seed-data.sql`) had been sitting unused since Phase 1,
      confirming this was the intended design. **Genuinely does need code
      changes**, unlike T053/T054 — `ComputeRollupsUseCase.execute()`
      hardcoded `event_type == "usage_measurement"` before this feature
      (depends on T049).
- [X] T056 [US6] Extended `SqlAlchemyMessageEventRepository.list_all()`'s
      SQL (not `tone_reader.py` itself, which is unmodified) to also
      include `survey_response` rows carrying `has_comment: true`.
      **Genuinely does need code changes** — the adapter's SQL hardcoded
      `event_type IN ('message', 'ticket_state_change')` before this
      feature. `ToneReader`/`IntentReader` both benefit automatically since
      they share this same corpus port (depends on T049).
- [X] T057 [P] [US6] Wrote `backend/tests/unit/test_meeting_reader.py` —
      faked `LLMPort`/`MeetingTranscriptRepositoryPort`: an extracted
      commitment produces a finding; an empty extraction produces none; a
      cached event is never re-interpreted; a missing-API-key `ValueError`
      propagates (mirrors Tone/Intent's identical guard). Consent-gating
      itself is proven at the collection layer (T059), not here — see
      T051's note on why the reader has nothing left to check.
- [X] T058 [P] [US6] **Scope correction found during implementation:**
      `test_absence_reader.py`/`test_relationship_reader.py`/(pre-existing)
      `test_usage_reader.py` only ever tested pure domain-service functions
      (`absence_magnitude`, `relationship_change_finding`, `z_score`) —
      never the `Reader` classes' own orchestration with faked ports. Since
      T053/T054 need no code changes at all, and absence/relationship's
      ports carry no `source_type` concept to fake differently, there is no
      new *unit-level* case to add for them — the real proof a Slack event
      counts is only representable at the integration level (T059).
      `usage_reader.py`'s orchestration, by contrast, gained genuinely new
      routing logic (T055) that had never been exercised by any test at
      any level — added two new orchestration tests to
      `tests/readers/test_usage_reader.py` (faked `RollupRepositoryPort`)
      confirming `subject_type="stakeholder"` routes to `csat_deviation`
      and `subject_type="product_area"` still routes to `usage_deviation`.
      Tone's new CSAT-comment path is adapter-only (T056) and covered at
      the real-DB level (T059), not unit level, since `ToneReader` itself
      is unmodified.
- [X] T059 [US6] Wrote `backend/tests/ingestion/
      test_post_mvp_sources_real_db.py` (6 tests, uuid-suffixed isolated
      fixture copies, matching `test_simulated_collector.py`'s established
      pattern): coverage reports the 3 Post-MVP sources only because this
      run's own data contains them; an unconsented calendar series produces
      zero `raw_envelopes` rows; Slack messages and CSAT-with-comment
      (but not CSAT-score-only) reach the shared Tone/Intent corpus; the
      one consented transcript (and not the unconsented one) reaches
      `MeetingReader`'s dedicated port; a CSAT score reaches `UsageReader`'s
      rollups. **Deliberately does not force a statistically-triggered
      Finding** (chat-silence/CSAT deviation) — that decision logic is
      already exhaustively covered by `test_usage_reader.py`/
      `test_absence_reader.py`'s pure-function tests and
      `test_run_readers_use_case.py`'s real-DB pass; forcing enough
      synthetic samples here to cross a z-score threshold would duplicate
      that coverage without adding confidence (depends on T052, T053–T056).
- [X] T060 [US6] FR-024 regression: added
      `test_a_client_connecting_none_of_the_three_sources_sees_identical_
      behavior` to `test_post_mvp_sources_real_db.py`, running the
      collector against the preserved `meridian-week-phase1-only.json`
      (T047's note) and confirming `envelopes_emitted == 14` and
      `coverage_reports.sources_expected == 3` — byte-for-byte the
      pre-Phase-11 numbers, proving Post-MVP sources are additive-only
      (`RunCollectorUseCase._POST_MVP_SOURCE_TYPES`'s docstring). Also
      re-ran the full backend suite from a genuine clean slate (`docker
      compose down -v` -> `up -d` -> `alembic upgrade head` -> `scripts/
      seed.py`) multiple times to separate real regressions from
      pre-existing noise:
      - **Found and fixed a genuine, previously-masked bug**, not caused by
        this feature's own new code but surfaced by this feature's
        clean-slate verification: `tests/narrator/test_run_narrator_real_db.py`
        still constructed the legacy single-key `FernetEncryption` directly
        (`FernetEncryption("../secrets/data.key")`) instead of
        `BucketedFernetEncryption` — every event body has been
        bucket-encrypted since this feature's own User Story 1, so on a
        truly fresh database (no leftover pre-bucketing rows the shared dev
        DB had been quietly carrying) every one of that file's 3 tests
        failed with `EncryptionKeyError`/`InvalidToken`. Fixed by switching
        to `BucketedFernetEncryption(FileKeyStore(...), ...)`, matching
        every other test/script in the codebase.
      - **Confirmed pre-existing, out-of-scope, unrelated to Post-MVP
        code**: `test_hash_chain.py::test_appended_sequence_has_no_broken_
        links` and `test_run_readers_use_case.py::test_run_readers_
        reproduces_the_full_worked_example_table` both still fail on a
        clean-slate full-suite run — this is the same full-suite
        test-ordering fragility already investigated and documented earlier
        in this feature's own US1 checkpoint (git-stash-verified against
        unmodified code). Neither failing test touches any Post-MVP file;
        confirmed by running `tests/ingestion tests/unit tests/readers`
        together from a fresh reset, where these are the *only* two
        failures and every Post-MVP-specific test passes cleanly.
      - Along the way, also found (and left as a real, separate, pre-existing
        gap, not fixed — out of scope for this feature): the shared dev
        database's `client_profile_versions.is_current` row (submitted by
        earlier User Story 5 testing) carries no `recurring_sync` commitment,
        which silently starves `DetectAbsenceUseCase.list_recurring_
        commitments()` — a cross-feature test-isolation gap from User Story
        5's own real-DB testing, not from this story; resolved for
        verification purposes by the same clean-slate reset above rather
        than by mutating shared state.
      (depends on T059)

**Checkpoint**: User Story 6 is fully functional and independently
testable — three new sources feed five readers (two genuinely extended —
Usage, Tone — one newly activated — Meeting — and two, Absence/Relationship,
confirmed to need zero code changes since their queries were already
source-agnostic), consent-gated where required, with zero regression for a
client that connects none of them, verified via a real clean-slate rebuild.
11 new/extended tests across `test_simulated_collector.py`,
`test_meeting_reader.py`, `test_usage_reader.py`, and
`test_post_mvp_sources_real_db.py`, all passing.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Repo-wide consistency checks this feature's own Constitution
Check names but that don't belong to any single story.

- [X] T061 [P] Re-ran `lint-imports --config ../.importlinter` — all 3
      contracts stay `KEPT`, `app.observability` introduces no forbidden
      import.
- [X] T062 [P] Extended `backend/tests/unit/test_no_llm_imports.py` with a
      second parametrized test covering `weight_router.py`/`tracing.py`/
      `key_store.py`/`encryption.py`, kept as a clearly separate,
      honestly-scoped list rather than merged into feature 010's existing
      one — P2's actual enforcement text only names `app/scoring/`
      (`weight_router.py` is a direct instance of it); the other three are
      outside P2's literal scope but checked anyway as defense-in-depth
      hygiene, documented as such in the test file's own comment.
- [X] T063 [P] Updated `architecture/07-api-spec.md` — `POST /api/profile`
      marked implemented, `/api/profile/reload`'s note corrected to "not
      removed" (not a Post-MVP placeholder anymore), added the
      `PATCH /api/admin/finding-types/{finding_type}` route table entry.
- [X] T064 [P] Updated `data-base/03-schema-ledger.md`'s `data_key_ref` row
      and crypto-shredding note with the real daily-UTC-bucket scheme and
      the now-implemented `RunRetentionUseCase`/`retention_job_runs`.
- [X] T065 [P] Updated `data-base/12-users-and-auth.md` — replaced the "no
      RBAC at all" note with the real, narrower current state: two of five
      roles (`account_executive`, `admin`) are enforced, three are not yet.
- [X] T066 [P] Updated `architecture/03-technology-stack.md`'s Observability
      row — OpenTelemetry marked adopted, describing the real
      `BatchSpanProcessor`/OTLP/`ConsoleSpanExporter` shape (was "Phase 2
      addition").
- [X] T067 Ran the full backend suite against a genuine clean-slate rebuild
      (`docker compose down -v` -> `up -d` -> `alembic upgrade head` ->
      `scripts/seed.py`), multiple times, to separate real regressions from
      pre-existing noise — see T060's note for the full account: one
      genuine bug found and fixed (`test_run_narrator_real_db.py`'s legacy
      `FernetEncryption` usage), two pre-existing/out-of-scope full-suite
      ordering failures confirmed unrelated to this feature's own new code
      (`test_hash_chain.py`, `test_run_readers_use_case.py`'s first test).
      Frontend `lint`/`typecheck`/`test`/`build` were not re-run in this
      pass — no frontend file changed during Phase 8 (User Story 6 is
      backend/fixture-only); frontend verification stands from Phase 7's
      own checkpoint.
- [X] T068 Walked `quickstart.md`'s User Story 6 section live end to end
      against the real running `api` container + Postgres: `POST /auth/
      login` as `marta`, `run_collector.py` (19 envelopes),
      `GET /api/coverage` (confirms `slack`/`csat`/`transcripts`
      connected), `run_readers.py` (`MeetingReader` correctly registered,
      fails honestly with no `ANTHROPIC_API_KEY` configured, isolated from
      the other 7 readers per FR-014a), and a direct `psql` query
      confirming zero `raw_envelopes` rows for the non-consented calendar
      series across 11 accumulated real collector runs (FR-023). Spot-
      verified User Stories 2/4/5's key endpoints live in the same pass
      (`GET /api/dashboard` 200/`POST /api/feedback` 403 for
      `account_executive`; `PATCH /api/admin/finding-types` 403 for
      `cs_lead`/200 for `admin`; `GET /api/profile` reflecting the real
      seeded profile) rather than re-walking their full multi-step
      protocols verbatim, since those were already verified in depth
      during their own implementation phases (this file's US1-US5
      checkpoints). User Story 1/3's worker/OTel-collector-dependent steps
      were not re-walked live in this pass (no `worker`/`otel-collector`
      container started) — already verified during their own
      implementation phases per this file's US1/US3 checkpoints. Full
      results recorded in `specs/ROADMAP.md`'s Log.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup. Blocks every user story.
- **User Stories (Phase 3–8)**: All depend on Foundational. US1, US2, US4,
  and US6 have no dependency on any other story — each is fully compliant
  with its own FRs using only its own tasks (`/speckit-analyze` finding I1
  resolved US1's prior FR-004a coupling to US3: T015 now logs the failure
  independently, and US3's T027 is a strict enhancement on top, not a
  prerequisite). US3 has exactly **one** task, not the whole story, with a
  real cross-story dependency: T027 depends on US1's T016 (it wraps an
  already-shipped retention job with a trace) — every other US3 task
  (T025, T026, T027a, T028, T029, T029a, T030) depends only on Foundational.
  US5 depends on US2's T021 (`require_full_access`) for its new route's
  gate — noted in US5's own phase header with a fallback if delivery order
  is reversed.
- **Polish (Phase 9)**: Depends on all six user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Foundational only — fully independent, including FR-004a's
  failure-alerting half (`/speckit-analyze` finding I1).
- **US2 (P2)**: Foundational (T007).
- **US3 (P3)**: Foundational only, **except T027**, which additionally
  depends on US1's T016 (see above — the one honest cross-story edge in
  this feature's task graph, `/speckit-analyze` finding I2).
- **US4 (P4)**: Foundational (T004, T007). Deliberately does *not* depend
  on US2 despite both `require_full_access` and `require_admin` sharing a
  log-line shape for FR-008 — the two dependencies duplicate a few lines
  rather than share a cross-story helper (T031's note).
- **US5 (P5)**: Foundational, plus US2's T021 (see above).
- **US6 (P6)**: Foundational only.

### Within Each User Story

- Ports before adapters before use cases before routes (P8's Dependency
  Rule, mechanically enforced by `.importlinter`).
- Tests can run any time after the code they exercise exists; every story
  ends with a real-DB/real-route test.

### Parallel Opportunities

- All Setup tasks (T001–T003) in parallel.
- Within Foundational, T005 in parallel with T004; T006/T007 are
  sequential after T005.
- Once Foundational completes: **US1, US2, US3 (all tasks except T027),
  US4, and US6 can all start immediately in parallel** — every one of them
  needs only Foundational. **US3's T027 specifically waits on US1's T016**
  (not marked `[P]`, unlike its five siblings in the same phase). **US5
  should start after US2's T021** (or accept the one-line
  downgrade-then-upgrade noted in its phase header if run in parallel
  anyway).
- Within US1: T008/T009 parallel; T014 parallel with T008–T013; T018/T019
  parallel with each other.
- Within US6: T048/T049/T050 parallel (three independent normalize
  functions); T053–T056 parallel (four independent reader files); T057/T058
  parallel.

---

## Parallel Example: User Story 1

```bash
# Launch the two independent new adapters together:
Task: "Add KeyStorePort to backend/app/ingestion/application/ports.py"
Task: "Implement shredder_session_factory in backend/app/db.py"

# Once both land, the encryption adapter and retention use case can proceed:
Task: "Implement BucketedFernetEncryption in backend/app/ingestion/adapters/encryption.py"
```

## Parallel Example: User Story 6

```bash
# Three independent normalize functions, same file, non-overlapping regions:
Task: "Implement _normalize_slack in simulated_collector.py"
Task: "Implement _normalize_csat in simulated_collector.py"
Task: "Implement _normalize_calendar in simulated_collector.py"

# Four independent reader extensions, four different files:
Task: "Extend absence_reader.py for chat-silence"
Task: "Extend relationship_reader.py for Slack participant graph"
Task: "Extend usage_reader.py for CSAT metric"
Task: "Extend tone_reader.py for CSAT comments"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) + Phase 2 (Foundational).
2. Complete Phase 3 (US1 — retention/crypto-shredding).
3. **STOP and VALIDATE**: `quickstart.md`'s User Story 1 section, against a
   real Postgres, including the idempotency and forced-failure cases.
4. Deploy/demo if ready — closes the single highest-compliance-risk gap
   this whole feature exists to close.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. US1 (P1) → validate → deploy (MVP).
3. US2 (P2) → validate → deploy.
4. US3 (P3) → validate → deploy.
5. US4 (P4) → validate → deploy.
6. US5 (P5) → validate → deploy.
7. US6 (P6) → validate → deploy.
8. Polish (Phase 9) — repo-wide consistency + full-suite regression run.

### Parallel Team Strategy

With multiple developers, once Foundational is done: Developer A takes US1
(the critical path — the only story every other artifact in this feature
was prioritized around); Developer B takes US2 then US5 (the one real
cross-story dependency, same developer avoids a handoff); Developer C
takes US3; Developer D takes US4; Developer E takes US6 (the largest
story by file count, benefits from dedicated focus).

---

## Notes

- [P] tasks = different files, or non-overlapping regions of a shared file,
  with no dependency on an incomplete task.
- [Story] label maps every task to exactly one of US1–US6 for traceability
  back to `spec.md`.
- Commit after each task or logical group, matching this repository's
  established per-feature convention.
- Every real-DB test task runs against the actual containerized Postgres,
  never a mock — matching `tests/strategy.md` and every prior feature's own
  verification standard.
- T004's migration is the one task every single-developer implementation
  order should do first after Setup, regardless of which story comes
  next — it's the one artifact both US1 (indirectly, via the grants) and
  US4 (directly) need, and the one most awkward to retrofit once other
  code depends on its absence.
