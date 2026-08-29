# Phase 0 Research: Production Deployment Hardening II

## Decision 1 — Backup destination and retention window

**Decision**: A new `backup_dir: str = "./secrets/backups"`-style setting — actually a distinct
top-level `./backups` directory (not nested under `./secrets`), mounted read-write on the
`worker` service only (`docker-compose.yml`), matching `client_profile_path`/`collector_fixture_
path`'s own "a real file location, not a secret" precedent from `config.py`. Default backup
interval: `backup_poll_interval_hours = 24` (once daily, matching `RunRetentionUseCase`'s own
daily cadence). Default retention window: `backup_retention_days = 30`.

**Rationale**: Backups aren't cryptographic secrets themselves (they're `pg_dump` output — the
same encrypted-at-rest ciphertext plus plaintext metadata the live database already holds), so
they don't belong under `./secrets`, but they are sensitive (they contain everything the live
database does) — a dedicated, clearly-named directory keeps that visible rather than burying
backups inside a directory named for something else. 30 days is a standard operational backup
retention window (long enough to recover from a slow-to-notice problem, short enough not to
accumulate unbounded storage) and is a **deliberately different** number from
`retention_window_days=90` — that setting governs when *live* row data is crypto-shredded for
compliance; this one governs how long *backup files* are kept for disaster recovery. Conflating
them would be a real bug (a backup surviving past the compliance retention window would defeat
crypto-shredding's whole purpose — the shredded key wouldn't matter if an old backup still has the
plaintext key file sitting next to it). Because of that, this decision also requires:
`backup_retention_days` must always be `<=` the *encryption key* rotation/shredding horizon in
practice — documented here, not enforced in code, since the two features are configured
independently per deployment and a hard runtime coupling would be over-engineering (P10) for a
constraint an operator can honor by policy.

**Alternatives considered**:
- *Match `retention_window_days` exactly*: rejected — conflates two different compliance/DR
  concerns, as above.
- *No retention/cleanup, keep every backup forever*: rejected — spec.md FR-003 requires cleanup;
  unbounded local disk growth on a single-VM-per-client deployment is a real operational hazard.
- *Cloud object storage with its own lifecycle policy*: rejected for this feature per FR-014 (no
  provider chosen) — the local filesystem approach is designed so a later `S3BackupDestination`
  (or GCS) is a new adapter behind the same `BackupDestinationPort`, zero changes to
  `RunBackupUseCase`.

## Decision 2 — How `pg_dump` is invoked, and the backup-run record's shape

**Decision**: `RunBackupUseCase` shells out to `pg_dump` via `subprocess.run` (not the app's own
`asyncpg`/SQLAlchemy connection pool — a separate OS process against a plain `postgresql://` URL
derived from `settings.database_url` by stripping the `+asyncpg` driver qualifier SQLAlchemy
needs but `pg_dump` doesn't understand). Output: a single custom-format dump
(`pg_dump -Fc -f <dest>/<timestamp>.dump "$PLAIN_URL"`) — custom format because it's
`pg_restore`-compatible, compressed by default, and (unlike plain SQL) restorable with
`pg_restore --clean --if-exists` for a clean idempotent restore. `backend/Dockerfile`'s runtime
stage installs the `postgresql-client` Debian package (not currently present — verified via `RUN
apt-get`), so `pg_dump`'s major version tracks whatever Debian's `python:3.12-slim` base image
(bookworm) ships by default; this is checked for a real version match against the running
`pgvector/pgvector:pg16` server as part of this feature's own validation (`quickstart.md`), not
assumed compatible.

`backup_job_runs` (new table, mirrors `retention_job_runs` field-for-field where the concept
maps):

```
CREATE TYPE backup_job_status AS ENUM ('succeeded', 'failed');
CREATE TABLE backup_job_runs (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at        TIMESTAMPTZ NOT NULL,
    completed_at      TIMESTAMPTZ,
    destination_path  TEXT,
    file_size_bytes    BIGINT,
    status            backup_job_status NOT NULL,
    error_detail      TEXT,
    CONSTRAINT backup_job_runs_completed_after_started
        CHECK (completed_at IS NULL OR completed_at >= started_at)
);
```

A run also deletes files older than `backup_retention_days` from the destination directory as
its last step (FR-003), inside the same try/except as the dump itself, so a cleanup failure is
recorded the same honest way a dump failure is.

**Rationale**: Directly follows `RunRetentionUseCase`'s own established shape (`app/ingestion/
application/use_cases.py`) — try the operation, record success or failure either way, re-raise on
failure so the caller's own schedule naturally retries (identical FR-004a precedent). Custom
format (`-Fc`) over plain SQL (`-Fp`) because `pg_restore`'s `--clean --if-exists` flag makes
restoring into a non-empty database safe to re-run, which a plain `psql < dump.sql` replay does
not guarantee against a partially-restored prior attempt.

**Alternatives considered**:
- *A Python-native backup (SQLAlchemy `COPY` per table)*: rejected — reinvents what `pg_dump`
  already does correctly (schema + data + constraints + sequences), a textbook P10 violation.
- *Plain-SQL dump format*: rejected — worse restore safety, as above.
- *Streaming the dump directly to a cloud bucket without a local file*: rejected per FR-014 (no
  provider chosen); also would remove the "confirm the file exists and has a nonzero size" check
  this feature's own validation performs locally.

## Decision 3 — Alert conditions, webhook payload shape, and de-duplication

**Decision**: Exactly three conditions, matching spec.md's own enumeration — no dynamic/
pluggable condition registry (P10; the constitution explicitly rejects a "plugin/dynamic-
discovery system" for the readers, and the same reasoning applies here: these are the three
things this system can actually already detect, not a framework for hypothetical future ones):

1. `score_source_degraded` — true iff the most recent `score_runs` row has `source_degraded =
   true`.
2. `backup_job_failed` — true iff the most recent `backup_job_runs` row has `status = 'failed'`.
3. `retention_job_failed` — true iff the most recent `retention_job_runs` row has `status =
   'failed'`.

Webhook payload (POSTed as JSON to `settings.alert_webhook_url` via `httpx.AsyncClient`, already
a main dependency since specs/029):

```json
{"condition": "backup_job_failed", "message": "Backup run <uuid> failed: <error_detail>", "occurred_at": "2026-08-28T12:00:00+00:00"}
```

Three fields, no templating, no per-destination formatting — Slack, PagerDuty, or a client's own
custom receiver all get the same flat JSON (FR-007's "configured per deployment," not
per-destination-vendor).

De-duplication (FR-010) is a new `alerts` table with a **database-enforced** "at most one open
alert per condition" constraint — a partial unique index, the same style of DB-level guarantee
this project already relies on for `score_runs.score`'s `CHECK`, `retention_job_runs`'
`buckets_shredded <= buckets_evaluated`, etc.:

```
CREATE TABLE alerts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    condition_name  TEXT NOT NULL,
    message         TEXT NOT NULL,
    fired_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at     TIMESTAMPTZ,
    CONSTRAINT alerts_resolved_after_fired
        CHECK (resolved_at IS NULL OR resolved_at >= fired_at)
);
CREATE UNIQUE INDEX alerts_one_open_per_condition
    ON alerts (condition_name) WHERE resolved_at IS NULL;
```

`RunAlertCheckUseCase.execute()` per condition: if the condition is currently true and no open
(`resolved_at IS NULL`) row exists for it, insert one and send the webhook (a fresh occurrence).
If the condition is currently true and an open row already exists, do nothing (already notified,
still ongoing — FR-010). If the condition is currently false and an open row exists, mark it
resolved (so the *next* true occurrence fires fresh, rather than the condition being permanently
muted after its first firing).

**Rationale**: A DB constraint makes "at most one open alert per condition" true by construction,
the same reasoning this codebase already applies everywhere else it needs an invariant to
actually hold (not just be usually true because the application code remembered to check) —
matches `envelope_exists()`'s own idempotency-by-key spirit for collectors, applied here to a
*resolvable* condition rather than a permanent fact.

**Alternatives considered**:
- *In-memory/process-state de-duplication (a module-level set of already-fired conditions)*:
  rejected — `_last_seen_event_at`'s own precedent in `worker.py` already shows the cost of
  process-local state: it resets on every restart, meaning a redeploy (User Story 3 of this very
  feature!) would silently re-arm every alert. A durable DB record survives restarts by
  construction.
- *Rich alert-state machine (acknowledged/snoozed/escalated)*: rejected — P10; spec.md only
  requires "don't repeat a still-ongoing notification," not an incident-management system.

## Decision 4 — Redeploy script mechanics, and why `db` is excluded

**Decision**: `scripts/redeploy_service.sh <service>` (bash, repo-root, POSIX-portable where
practical): validates `<service>` is one of `api`, `worker`, `web` (hard-rejects `db` and
`migrate`/`otel-collector` with a clear message, not a silent no-op); runs `docker compose up -d
--no-deps --build <service>`; then polls `docker compose ps --format json <service>` for that
container's own Docker `Health` status (`starting` → `healthy`, using each service's *existing*
`HEALTHCHECK`/`healthcheck:` — already real for `api` (an actual HTTP `/health` call, `backend/
Dockerfile` + `docker-compose.yml`) and `web` (an actual HTTP fetch), and honestly noted as a
weaker signal for `worker` (its `healthcheck:` is `python -c exit(0)` — interpreter liveness only,
`docker-compose.yml`'s own comment already says so — the script polls the same signal the rest of
the stack already trusts, it doesn't invent a stronger one this feature would need to build) —
with a timeout (matching the container's own `healthcheck.retries × interval`, ~30-50s depending
on service) after which the script exits non-zero with a clear failure message (FR-012) rather
than hanging forever. While polling the redeployed service, the script also confirms the *other*
already-running services never report unhealthy (`docker compose ps` for all services, checked
once per poll iteration) — this is the script's own proof of SC-005 ("the other services were
never unreachable"), not an assumption.

`db` is explicitly excluded — not merely "not implemented yet" but a documented, permanent
exclusion for this script: redeploying `db` mid-operation risks in-flight transaction loss and
briefly disconnects every other service simultaneously (`api`/`worker` both hold live connection
pools to it) — a fundamentally different, higher-risk operation (planned maintenance window,
likely paired with the backup job this same feature just built) than a stateless service's
rolling image swap. Folding it into the same one-line script would misrepresent its risk as
equivalent to redeploying `api`.

**Rationale**: Reuses `docker-compose.yml`'s own already-correct healthchecks rather than
inventing a second liveness-check mechanism (P10) — this script's only new contribution is the
one-at-a-time sequencing and the "don't declare success until the container's own healthcheck
says so" polling loop, both of which are the actual gap spec.md identifies (today, an operator
running a bare `docker compose up -d --build` themselves has no such confirmation step).

**Alternatives considered**:
- *A Python script under `backend/scripts/`*: rejected — this operates on `docker-compose.yml`
  at the repo root, and every other `backend/scripts/*.py` file assumes a `backend/`-relative
  runtime (matching `collector_fixture_path`'s own documented CWD-relative convention) — putting
  a repo-root operational tool there would be a real, confusing mismatch of assumptions.
- *A generic "rolling redeploy all services" one-command script*: rejected — spec.md is explicit
  about one-at-a-time, operator-initiated per service; a "redeploy everything" mode is exactly the
  kind of automation this project's constitution (Isolation model, "an operator directly controls
  a deploy") doesn't ask for, and db's exclusion makes an "all services" mode ambiguous anyway
  (does it skip db silently, or fail? — better not to build the ambiguity at all, P10).
