---

description: "Task list for feature 031 — Production Deployment Hardening II"
---

# Tasks: Production Deployment Hardening II

**Input**: Design documents from `specs/031-production-deployment-hardening-ii/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Real-DB tests for the backup job (mirroring `test_retention_real_db.py`); fake-port
unit tests for the alert-check use case (no real DB needed, same shape as
`test_warehouse_collector.py`'s fake-client pattern); a real, live-executed run of
`scripts/redeploy_service.sh` against an actual local Docker Compose stack for User Story 3
(SC-005 cannot be verified any other way).

**Organization**: Tasks are grouped by the three user stories in `spec.md`.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 In `backend/app/config.py`, add `backup_dir: str = "./backups"`,
      `backup_poll_interval_hours: int = 24`, `backup_retention_days: int = 30`,
      `alert_webhook_url: str = ""` (honest-empty-default discipline — FR-009), and
      `alert_poll_interval_minutes: int = 15` (research.md Decisions 1/3).
- [x] T002 [P] In `backend/Dockerfile`'s runtime stage, add `RUN apt-get update && apt-get
      install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*`
      (research.md Decision 2) — `pg_dump`/`pg_restore` don't exist in `python:3.12-slim` today.
- [x] T003 [P] In `docker-compose.yml`, add a `./backups:/app/backups` read-write volume mount
      on the `worker` service only (the backup job runs there, matching every other scheduled
      job), with a comment explaining why (mirrors `./secrets/data-keys`'s own read-write
      comment pattern).

**Checkpoint**: New settings load without error; `pg_dump --version` succeeds inside a rebuilt
worker image; the backups directory is writable from the worker container.

---

## Phase 2: Foundational (Blocking Prerequisites)

- [x] T004 New `backend/migrations/versions/0009_backup_and_alerting.py`: creates
      `backup_job_status` enum (`succeeded`, `failed`), `backup_job_runs` table, `alerts` table,
      and the `alerts_one_open_per_condition` partial unique index
      (`data-model.md`'s exact column/constraint list). Grants: `backup_job_runs` gets
      insert-only `app_role` access (matching `retention_job_runs`); `alerts` gets `SELECT`,
      `INSERT`, `UPDATE` (matching `0006_meeting_series_consent.py`'s own precedent for a table
      that needs `UPDATE`).
- [x] T005 [P] In `.importlinter`, add `app.alerting` to the `global-dependency-rule` contract's
      `containers` list (plan.md's Constitution Check — the new module gets the same
      adapters/application layer-boundary enforcement every other module already has).

**Checkpoint**: `alembic upgrade head` succeeds; `lint-imports --config ../.importlinter` passes
with the new container registered (even before any `app.alerting` code exists — an empty
container is valid).

---

## Phase 3: User Story 1 - Operator trusts that data loss is recoverable (Priority: P1) 🎯 MVP

**Goal**: A scheduled `pg_dump` backup job with retention cleanup, recorded durably.

**Independent Test**: Run the backup job once against a real database; confirm a restorable dump
file exists and a `backup_job_runs` row records it (`quickstart.md` Story 1).

### Implementation for User Story 1

- [x] T006 [US1] In `backend/app/ingestion/application/ports.py`, add `BackupDestinationPort`
      (`async def create_backup(self) -> BackupResult` — returns destination path + file size)
      and `BackupJobRepositoryPort` (`async def record_run(...) -> UUID`, matching
      `RetentionJobRepositoryPort.record_run`'s own signature shape field-for-field where it
      applies).
- [x] T007 [US1] New `backend/app/ingestion/adapters/backup_destination.py`:
      `FilesystemBackupDestination(BackupDestinationPort)` — derives a plain `postgresql://` URL
      from `settings.database_url` (strips `+asyncpg`), shells out to `pg_dump -Fc -f
      <backup_dir>/<UTC timestamp>.dump <plain_url>` via `subprocess.run` (check=True), deletes
      files in `backup_dir` older than `backup_retention_days` (research.md Decision 1/2), and
      returns the new file's path + size. A `pg_dump` failure (non-zero exit) raises.
- [x] T008 [US1] In `backend/app/ingestion/adapters/sqlalchemy_repositories.py`, add
      `SqlAlchemyBackupJobRepository(BackupJobRepositoryPort)` — `INSERT INTO backup_job_runs`,
      matching the existing `record_run` pattern already there for retention.
- [x] T009 [US1] In `backend/app/ingestion/application/use_cases.py`, add `RunBackupUseCase` —
      calls `BackupDestinationPort.create_backup()`, records success via
      `BackupJobRepositoryPort.record_run(status="succeeded", ...)`; on any exception, records
      `status="failed"` with `error_detail=str(exc)` and re-raises (exact mirror of
      `RunRetentionUseCase`'s own try/except shape, FR-004a-equivalent).
- [x] T010 [US1] In `backend/app/worker.py`: add `_run_backup` (sync wrapper, matching
      `_run_retention`'s exact shape) constructing `FilesystemBackupDestination` +
      `SqlAlchemyBackupJobRepository` + `RunBackupUseCase`; register
      `scheduler.add_job(_run_backup, "interval", hours=settings.backup_poll_interval_hours,
      id="backup_job")`; add `"backup": _run_backup` to `_RUN_ONCE_JOBS`.

### Tests for User Story 1

- [x] T011 [P] [US1] New `backend/tests/ingestion/test_backup_real_db.py` (real-DB, mirroring
      `test_retention_real_db.py`'s own structure): a successful run produces a `.dump` file with
      nonzero size and a `backup_job_runs` row with `status='succeeded'`; a `pg_restore` of that
      file into a fresh scratch database reproduces the source row counts (`quickstart.md` Story
      1, step 3 — SC-002); a run against an unwritable `backup_dir` records `status='failed'`
      with a populated `error_detail` and re-raises; a second run with an artificially-aged dump
      file present deletes it and keeps the new one (FR-003).

**Checkpoint**: User Story 1 fully functional and independently verified — a real backup exists,
is restorable, and old ones are pruned.

---

## Phase 4: User Story 2 - Operator learns about a real problem without watching logs (Priority: P1)

**Goal**: A scheduled alert check for three fixed real conditions, provider-agnostic webhook,
DB-enforced de-duplication.

**Independent Test**: Force one real condition true, confirm exactly one webhook fires and one
`alerts` row opens; confirm silence when nothing is wrong; confirm no re-fire on a second check
(`quickstart.md` Story 2).

### Implementation for User Story 2

- [x] T012 [US2] New `backend/app/alerting/__init__.py`,
      `backend/app/alerting/application/__init__.py`,
      `backend/app/alerting/adapters/__init__.py` (new module skeleton — application + adapters
      only, no domain layer, matching `app.narrator`/`app.experience`'s own precedent, plan.md's
      Constitution Check).
- [x] T013 [US2] New `backend/app/alerting/application/ports.py`: `AlertConditionReaderPort`
      (`async def is_score_source_degraded(self) -> bool`; `async def
      backup_job_failure_message(self) -> str | None`; `async def
      retention_job_failure_message(self) -> str | None` — each `None` means "not currently
      true"); `AlertRepositoryPort` (`async def has_open_alert(self, condition_name: str) ->
      bool`; `async def open_alert(self, condition_name: str, message: str) -> None`; `async def
      resolve_alert(self, condition_name: str) -> None`, idempotent no-op if none open);
      `WebhookNotifierPort` (`async def send(self, condition_name: str, message: str,
      occurred_at: datetime) -> None`).
- [x] T014 [US2] New `backend/app/alerting/application/use_cases.py`: `RunAlertCheckUseCase` —
      evaluates the three fixed conditions (research.md Decision 3's exact list, no
      dynamic/pluggable registry per P10); for each currently-true condition without an open
      alert, opens one and sends the webhook; for each currently-true condition with an already-
      open alert, does nothing (FR-010); for each currently-false condition, resolves any open
      alert for it.
- [x] T015 [US2] New `backend/app/alerting/adapters/sqlalchemy_condition_reader.py`:
      `SqlAlchemyAlertConditionReader(AlertConditionReaderPort)` — reads the latest `score_runs`
      row's `source_degraded`, the latest `backup_job_runs` row's `status`/`error_detail`, the
      latest `retention_job_runs` row's `status`/`error_detail`, directly via SQL (matching
      `app.narrator`'s own `SqlAlchemyScoreContextRepository` precedent of reading another
      module's table via its own adapter, never importing that module's repository classes).
- [x] T016 [US2] New `backend/app/alerting/adapters/sqlalchemy_alert_repository.py`:
      `SqlAlchemyAlertRepository(AlertRepositoryPort)` — `has_open_alert`/`open_alert`/
      `resolve_alert` against the new `alerts` table (data-model.md).
- [x] T017 [US2] New `backend/app/alerting/adapters/webhook_notifier.py`:
      `HttpxWebhookNotifier(WebhookNotifierPort)` — if `settings.alert_webhook_url` is unset,
      logs and returns without attempting a request (FR-009); otherwise POSTs the three-field
      JSON payload (research.md Decision 3) via `httpx.AsyncClient`.
- [x] T018 [US2] In `backend/app/worker.py`: add `_run_alert_check` (sync wrapper) constructing
      the three new adapters + `RunAlertCheckUseCase`; register
      `scheduler.add_job(_run_alert_check, "interval",
      minutes=settings.alert_poll_interval_minutes, id="alert_check")`; add `"alert_check":
      _run_alert_check` to `_RUN_ONCE_JOBS`.

### Tests for User Story 2

- [x] T019 [P] [US2] New `backend/tests/unit/test_alert_check_use_case.py`: fake
      `AlertConditionReaderPort`/`AlertRepositoryPort`/`WebhookNotifierPort` implementations (no
      real DB needed, matching `test_warehouse_collector.py`'s fake-client pattern) — assert: a
      newly-true condition opens exactly one alert and sends exactly one webhook; a still-true
      condition with an already-open alert sends zero additional webhooks (FR-010); an all-false
      check opens zero alerts and sends zero webhooks (FR-008); a condition transitioning from
      true to false resolves its open alert.
- [x] T020 [P] [US2] Same file or a dedicated one: `HttpxWebhookNotifier` with
      `alert_webhook_url` unset makes zero HTTP calls and does not raise (FR-009).

**Checkpoint**: User Story 2 fully functional and independently verified — real conditions alert
exactly once each, silence otherwise.

---

## Phase 5: User Story 3 - Operator ships a fix without downtime (Priority: P2)

**Goal**: A real, tested one-service-at-a-time redeploy script; `db` explicitly refused.

**Independent Test**: Live-execute against a real running local Docker Compose stack — redeploy
one service while polling the others for zero failed requests throughout (`quickstart.md` Story
3 — this cannot be verified by reading the script alone).

### Implementation for User Story 3

- [x] T021 [US3] New `scripts/redeploy_service.sh` (repo root, executable): validates the one
      argument is `api`, `worker`, or `web` — hard-refuses `db`/`migrate`/`otel-collector` with a
      clear message and exits non-zero without touching anything (FR-013, research.md Decision
      4's stated reason); runs `docker compose up -d --no-deps --build <service>`; polls `docker
      compose ps --format json <service>` for `Health == "healthy"` with a bounded timeout,
      failing clearly (not hanging) if it's never reached (FR-012); while polling, also checks
      every other already-running service never reports unhealthy.

### Validation for User Story 3 (live, not just written)

- [x] T022 [US3] Live-execute `quickstart.md` Story 3 end to end against a real local `docker
      compose up -d --build` stack: start a continuous `/api/health` polling loop in a separate
      process, redeploy `api` via the script, confirm zero failed polls throughout and that the
      script only reports success after the container's own healthcheck passes; repeat for
      `worker` and `web`; run the script against `db` and confirm it refuses immediately with no
      side effects (SC-005, FR-011/012/013 — the one task in this feature that cannot be
      satisfied by unit tests alone).

**Checkpoint**: User Story 3 verified against a real running stack, not assumed correct from
reading the script.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T023 [P] Run `ruff`/`mypy`/`lint-imports --config ../.importlinter` clean across all
      changed and new files (including the new `app.alerting` module against its own contract).
- [x] T024 [P] Confirm `specs/ROADMAP.md` and `README.md` are intentionally left unmodified,
      matching `specs/025`–`030`'s own precedent.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Phase 1 (T004's migration needs no settings, but T005's
  `.importlinter` change is logically paired with the module Phase 4 will populate).
- **User Story 1 (Phase 3)**: Depends on Phases 1–2 (T004's `backup_job_runs` table).
- **User Story 2 (Phase 4)**: Depends on Phases 1–2 (T004's `alerts` table) and, for its
  `backup_job_failed` condition to ever have real data to read, benefits from Phase 3 existing
  first — but T012–T020 do not *require* Phase 3's code to exist to be implemented or unit-tested
  (T019 uses fakes). Built after US1 in this list for that reason, not a hard blocking
  dependency.
- **User Story 3 (Phase 5)**: Depends on nothing this feature builds elsewhere — independent of
  Phases 3–4.
- **Polish (Phase 6)**: Depends on Phases 3–5.

### Parallel Opportunities

- T002/T003 (Dockerfile, docker-compose.yml — independent files) can run together.
- T013–T017 (new module's ports + three adapters — independent files once T013's ports exist)
  can be drafted together after T013.
- T019/T020 (independent test cases) can be drafted together.
- Phase 5 (US3) has no dependency on Phases 3–4 and can be built in parallel with either.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 (Setup) → Phase 2 (Foundational).
2. Phase 3 (User Story 1) — a real, restorable, retention-pruned backup exists.
3. **STOP and VALIDATE** via `quickstart.md` Story 1.

### Incremental Delivery

1. Setup + Foundational → Phase 3 (US1) → validate → data loss is now recoverable.
2. Phase 4 (US2) → validate → an operator is notified of real problems without watching logs.
3. Phase 5 (US3) → validate live → a redeploy no longer risks silently taking the stack down.
4. Phase 6 (Polish) → final sign-off.

## Notes

- No `[Story]` label on T001–T005 (Setup/Foundational) or T023–T024 (Polish).
- T022 is unusually load-bearing for this feature specifically: SC-005 ("zero failed requests to
  the other services during a redeploy") is not something a unit test can prove — it requires a
  real running stack and a real continuous poller running alongside a real redeploy.
- KMS and cloud-specific Terraform IaC are intentionally absent from this task list — FR-014,
  spec.md Assumptions, plan.md Constitution Check (P10) all document this as a deliberate
  deferral tied to no cloud provider being chosen yet, not an oversight.

## Verification log (how each task was actually confirmed, not just assumed)

- **T001–T003**: New settings load with no unset-value error. `backend/Dockerfile` rebuild
  confirmed live (see T007 below) — the runtime image ends up with `pg_dump (PostgreSQL) 17.11
  (Debian 17.11-0+deb13u1)` (Debian trixie's default `postgresql-client`, not version-pinned to
  16 — see T007's own note on why this is fine in practice). `./backups` volume mount confirmed
  writable from inside a real `worker` container.
- **T004/T005**: `alembic upgrade head` applies `0009_backup_and_alerting` cleanly against a real
  `pgvector/pgvector:pg16` database; `lint-imports --config ../.importlinter` passes with
  `app.alerting` registered (4 contracts kept, `app.alerting` container present).
- **T006–T010**: `BackupDestinationPort`/`BackupJobRepositoryPort`/`FilesystemBackupDestination`/
  `SqlAlchemyBackupJobRepository`/`RunBackupUseCase` implemented and wired into `worker.py`;
  `ruff check .`, `uv run mypy app`, `lint-imports` all clean on first pass.
- **T011**: New `backend/tests/ingestion/test_backup_real_db.py` (3 tests) — all passing,
  including a genuine `pg_restore` of a real dump into a freshly `CREATE DATABASE`d scratch
  database on the same server, confirming the restored `events` row count matches the source
  exactly (SC-002). Required installing `postgresql@16` locally via Homebrew to get
  `pg_dump`/`pg_restore` on the host's own `PATH` for local test runs (documented in
  `quickstart.md` Prerequisites) — the CI/production path gets these from `backend/Dockerfile`'s
  new install instead.
- **T012–T018**: New `app.alerting` module (ports, `RunAlertCheckUseCase`,
  `SqlAlchemyAlertConditionReader`, `SqlAlchemyAlertRepository`, `HttpxWebhookNotifier`) built and
  wired into `worker.py`'s `_run_alert_check` job. `ruff`/`mypy`/`lint-imports` clean.
- **T019/T020**: New `backend/tests/unit/test_alert_check_use_case.py` (6 tests, fake ports —
  healthy-system silence, newly-true fires once, still-true de-duplicates, resolves on recovery,
  three-conditions-independent, unconfigured-webhook doesn't raise) — all passing.
- **Live verification beyond the automated tests (User Story 2)**: brought up the real local
  `docker compose` stack (`docker compose up -d --build`) and, against the running `worker`
  container: (1) ran `alert_check` with a clean database — zero rows in `alerts`, confirmed
  silent (FR-008); (2) inserted a real failed `retention_job_runs` row, ran `alert_check` again
  pointed at a real local webhook receiver (`host.docker.internal`) — exactly one HTTP POST
  received, exact payload
  `{"condition":"retention_job_failed","message":"...","occurred_at":"..."}`; (3) ran
  `alert_check` again unchanged — **zero** additional webhook calls (FR-010, DB-verified: the
  `alerts` row stayed open, `resolved_at IS NULL`, no new row); (4) inserted a succeeding
  `retention_job_runs` row, ran `alert_check` again — the open `alerts` row's `resolved_at`
  populated, condition auto-resolved; (5) inserted another failed row with
  `alert_webhook_url` **unset** — the job logged a clear warning and completed normally, zero
  HTTP attempts, zero crash (FR-009). All five scenarios matched `quickstart.md` Story 2 exactly.
- **T021**: New `scripts/redeploy_service.sh`, executable, refuses `db`/unknown args/no args with
  a clear message and nonzero exit before touching anything.
- **T022 (live, not just written)**: Brought up the full local stack; made a real, temporary code
  change to `backend/app/main.py` (reverted immediately after, confirmed via `git diff` showing
  no residual change) to prove a redeploy actually picks up new code — `docker inspect`'s image
  digest changed after each redeploy. Ran two continuous pollers (`/health` on `api`, `/` on
  `web`) throughout. Redeployed `api`: **zero** failed polls to `web` during the operation (`api`
  itself, being the one redeployed, briefly failed its own poll during the swap — expected and
  outside SC-005's scope, which is about the *other* services). Redeployed `worker`: **zero**
  failed polls to either `api` or `web` (`worker` has no HTTP surface to poll itself). Redeployed
  `web`: **zero** failed polls to `api`. Ran the script against `db`: refused immediately, exit
  code 2, `docker compose ps db` confirmed the container was never recreated (same uptime as
  before). Ran with no argument and with an unknown service name: both printed usage and exited
  1 without touching anything. SC-005 and FR-011/012/013 all confirmed against a real stack, not
  assumed from reading the script.
- **T023**: `ruff check .`, `uv run mypy app` (128 source files), `lint-imports --config
  ../.importlinter` (4/4 contracts kept, `app.alerting` included) all clean.
- **Full backend suite**: `tests/golden_replay/ tests/scoring/ tests/unit/ tests/ingestion/` —
  **233 passed, 1 skipped, 0 failed** (run against a freshly migrated, seeded, real
  `pgvector/pgvector:pg16` database via the actual `docker compose` stack this feature's own
  User Story 3 testing had already brought up) — the known pre-existing `test_hash_chain.py`
  full-suite-only flake (documented in `specs/ROADMAP.md`'s feature-011 log entry) did not occur
  in this run.
- **T024**: `specs/ROADMAP.md` and `README.md` intentionally left unmodified, matching
  `specs/025`–`030`'s own precedent.

**Outstanding**: none. Unlike features 029/030, this feature had no external-credential gap —
every user story was fully verifiable locally (a real Postgres for the backup job, a real local
webhook receiver for alerting, a real local Docker Compose stack for the redeploy script). The
one deliberate, documented non-goal is KMS/cloud IaC (FR-014), not a gap in what was tested.
