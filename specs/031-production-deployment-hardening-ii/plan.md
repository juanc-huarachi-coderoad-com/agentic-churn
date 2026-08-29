# Implementation Plan: Production Deployment Hardening II

**Branch**: `031-production-deployment-hardening-ii` | **Date**: 2026-08-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/031-production-deployment-hardening-ii/spec.md`

## Summary

Closes the last piece of the 7-feature production-readiness roadmap, scoped down by an
explicit user decision (no cloud provider chosen yet): a scheduled `pg_dump` backup job with
retention, recorded durably (`backup_job_runs`, mirroring `retention_job_runs`'s own shape);
a new `app.alerting` module that evaluates a fixed set of real conditions
(`score_runs.source_degraded`, the backup job's own last-run failure, the retention job's own
last-run failure) and POSTs a minimal, provider-agnostic webhook, de-duplicated via a DB-enforced
"one open alert per condition" constraint; and a real, tested `scripts/redeploy_service.sh` that
redeploys one non-`db` service at a time against a live local Docker Compose stack, polling each
service's own healthcheck before moving on. Cloud-vendor KMS and Terraform IaC are explicitly
out of scope (FR-014) — `KeyStorePort` already anticipates a later `KmsKeyStore` adapter with no
interface change needed.

## Technical Context

**Language/Version**: Python 3.12 (backend/worker), Bash (redeploy script) — matches every prior feature this session.

**Primary Dependencies**: No new Python dependency — `pg_dump` is invoked as a subprocess (the
`postgresql-client` OS package, newly added to `backend/Dockerfile`'s runtime stage — not
currently installed there); the alert webhook uses `httpx`, already a main dependency since
specs/029-real-zendesk-connector.

**Storage**: PostgreSQL (existing `pgvector/pgvector:pg16` instance) — two new tables
(`backup_job_runs`, `alerts`), one new Alembic migration.

**Testing**: pytest (real-DB tests matching `tests/ingestion/test_retention_real_db.py`'s own
pattern for the backup/alert use cases); a real, live-executed validation of
`redeploy_service.sh` against an actual running Docker Compose stack (not just written and
assumed correct — spec.md SC-005 requires this).

**Target Platform**: Linux server (Docker Compose), same "one stack per client" model as every
other feature.

**Project Type**: Web application (existing `backend/` + `frontend/` + repo-root ops layer) — this
feature adds the repo's first `scripts/` directory at the repo root (distinct from
`backend/scripts/`, which holds app-internal Python tooling) for operator-run shell scripts,
since a Compose redeploy operates repo-root-relative, not `backend/`-relative.

**Performance Goals**: N/A (scheduled background jobs and an operator-invoked script, not a
request-path change).

**Constraints**: The backup job must not hold long-lived locks or block the api/worker's own
request handling (`pg_dump` runs against `DATABASE_URL` in a separate subprocess, not inside the
app's own async connection pool). The redeploy script must observe zero failed requests to
unchanged services during a single-service redeploy (SC-005).

**Scale/Scope**: Single-tenant per deployment (unchanged) — the alert de-duplication design is
therefore "at most one open alert per condition name," not per-client, since there is exactly one
client per running stack.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **P6 — Silence Is a Success State**: FR-008 (no notification when nothing is wrong) and FR-010
  (no repeat notification for an already-open condition) are both direct applications of this
  principle to a new surface (outbound alerts) rather than the dashboard UI P6 was originally
  written for. The alert-check job's own default output on a healthy system is "checked, nothing
  to report" — logged, never pushed anywhere. **PASS.**
- **P8 — Clean Architecture**: `BackupDestinationPort` + `BackupJobRepositoryPort` join
  `KeyStorePort`/`RetentionJobRepositoryPort` in `app.ingestion.application.ports` (retention
  already established that an "operational safety job over this deployment's own database" lives
  in `app.ingestion`, not a new module, even though it's not really about *ingesting* external
  data). The alert-check use case is genuinely cross-module (it reads `score_runs`, owned by
  `app.scoring`, and the two job-run tables, owned by `app.ingestion`) — this gets its own new
  `app.alerting` module (application + adapters only, no domain layer, matching
  `app.narrator`/`app.experience`'s own precedent of reading another module's tables directly via
  its own port + adapter, never by importing that module's repository classes). `.importlinter`'s
  `global-dependency-rule` container list gains `app.alerting`. **PASS**, with one new module
  justified by a genuine cross-module read need, not a speculative one.
- **P9 — Test-First Determinism**: Not implicated — this feature touches no `ledger`/`scoring`
  code path. (`points_to_score`'s own fix, specs/030, is unrelated prior work.)
- **P10 — YAGNI**: FR-014 is this principle applied directly — no `KmsKeyStore`, no cloud
  object-storage adapter, no Terraform module, because no concrete provider exists to build
  against or verify against yet. The webhook payload is three fields (condition, message,
  timestamp) — no templating engine, no per-channel formatting (Slack vs PagerDuty vs anything
  else all receive the same flat JSON). **PASS.**
- **Constitution's "one Docker Compose stack per client" permanent constraint**: The redeploy
  script operates on one stack, in place — it does not introduce a second orchestrator, a
  blue/green second stack, or any multi-tenant assumption. `db` is explicitly excluded from the
  one-at-a-time redeploy loop (spec.md Assumptions) — restated technically in research.md.
  **PASS.**

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── ingestion/
│   │   ├── application/
│   │   │   ├── ports.py            # + BackupDestinationPort, BackupJobRepositoryPort
│   │   │   └── use_cases.py        # + RunBackupUseCase (mirrors RunRetentionUseCase)
│   │   └── adapters/
│   │       ├── backup_destination.py   # FilesystemBackupDestination (pg_dump subprocess)
│   │       └── sqlalchemy_repositories.py  # + SqlAlchemyBackupJobRepository
│   ├── alerting/                   # new module — application + adapters only, no domain
│   │   ├── application/
│   │   │   ├── ports.py            # AlertConditionPort(s), AlertRepositoryPort, WebhookPort
│   │   │   └── use_cases.py        # RunAlertCheckUseCase
│   │   └── adapters/
│   │       ├── sqlalchemy_repository.py  # reads score_runs/backup_job_runs/retention_job_runs
│   │       ├── sqlalchemy_alert_repository.py  # alerts table (open/resolve)
│   │       └── webhook_notifier.py       # httpx POST
│   ├── config.py                   # + backup_dir, backup_poll_interval_hours,
│   │                                #   backup_retention_days, alert_webhook_url,
│   │                                #   alert_poll_interval_minutes
│   ├── worker.py                   # + _run_backup, _run_alert_check jobs
│   └── Dockerfile                  # + postgresql-client (pg_dump) in the runtime stage
├── migrations/versions/
│   └── 0009_backup_and_alerting.py # backup_job_runs, backup_job_status enum, alerts,
│                                    #   alerts_one_open_per_condition partial unique index
└── tests/
    ├── ingestion/test_backup_real_db.py    # mirrors test_retention_real_db.py
    └── unit/test_alert_check_use_case.py   # fake condition ports, no real DB needed

scripts/                            # NEW at repo root (distinct from backend/scripts/) —
└── redeploy_service.sh             #   operator-run, repo-root-relative to docker-compose.yml

docker-compose.yml                  # + ./backups volume mount on worker (read-write)
```

**Structure Decision**: Backup lives inside the existing `app.ingestion` module, following
`RunRetentionUseCase`/`KeyStorePort`'s own precedent of "an operational safety job over this
deployment's own database lives here." Alerting is genuinely cross-module (reads `app.scoring`'s
`score_runs` and `app.ingestion`'s two job-run tables) and gets its own small new module with no
domain layer, matching `app.narrator`/`app.experience`'s existing shape. The redeploy script is
the repo's first repo-root `scripts/` directory, since it operates on `docker-compose.yml`
(repo-root-relative), not on the Python backend the existing `backend/scripts/` tooling targets.

## Complexity Tracking

*No Constitution Check violations — nothing to justify here.*
