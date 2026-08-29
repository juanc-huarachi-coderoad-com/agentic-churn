# Quickstart: Production Deployment Hardening II

## Prerequisites

- A real Postgres instance (`pgvector/pgvector:pg16`, matching `docker-compose.yml`), migrated
  and seeded (`alembic upgrade head`, `scripts/seed.py`, `scripts/run_collector.py --source
  simulated`).
- `pg_dump`/`pg_restore` available (added to `backend/Dockerfile`'s runtime stage by this
  feature; for local-only validation without rebuilding the image, any locally installed
  `postgresql-client` whose major version matches the running server works too).
- A local HTTP listener to receive webhook POSTs during validation (e.g. `python -m http.server`,
  or `nc -l`) — no real Slack/PagerDuty account needed, since the webhook is a plain JSON POST to
  whatever URL is configured (FR-007).

## Story 1 — Backup job produces a restorable dump, and cleans up old ones

1. Run the backup job once (`RunBackupUseCase` via a one-shot script, matching every other job's
   `--run-once` precedent in `worker.py`).
2. Confirm a new `.dump` file exists under `settings.backup_dir`, and a `backup_job_runs` row
   exists with `status='succeeded'`, a non-null `destination_path`, and `file_size_bytes > 0`.
3. Restore it into a fresh, empty database: `pg_restore --clean --if-exists -d
   <fresh_db_url> <dump_file>`; confirm `SELECT count(*) FROM events` matches the source
   database's own count.
4. Manually place a synthetic old dump file (mtime older than `backup_retention_days`) in
   `backup_dir`; run the job again; confirm the old file is deleted and the new one remains.
5. Point `backup_dir` at an unwritable path; run the job; confirm a `backup_job_runs` row with
   `status='failed'` and a populated `error_detail`, and that the exception propagates (matching
   `RunRetentionUseCase`'s own FR-004a re-raise precedent).

## Story 2 — Alerting fires once, stays quiet when healthy, and de-duplicates

1. Start a local webhook receiver.
2. With a clean database (no failed jobs, no degraded score run), run the alert-check use case
   once; confirm zero HTTP requests reach the receiver, and zero rows are inserted into `alerts`.
3. Insert a `retention_job_runs` row with `status='failed'` directly (matching
   `test_retention_real_db.py`'s own real-DB test-setup pattern); run the alert check; confirm
   exactly one webhook POST arrives with `condition="retention_job_failed"`, and one `alerts` row
   exists with `resolved_at IS NULL`.
4. Run the alert check again without changing anything; confirm **zero** additional webhook POSTs
   (FR-010 — already open, not re-fired) and still exactly one open `alerts` row for that
   condition.
5. Insert a new `retention_job_runs` row with `status='succeeded'`; run the alert check again;
   confirm the previously-open `alerts` row is now resolved (`resolved_at` populated) and no new
   webhook fires for this now-healthy condition.
6. Unset `alert_webhook_url`; force a condition true again; confirm the condition is still
   detected/logged but nothing crashes and no HTTP call is attempted (FR-009).

## Story 3 — Redeploy one service with zero downtime to the others

1. `docker compose up -d --build` the full stack; wait for all services healthy.
2. In a separate terminal, start a tight polling loop against `GET /api/health` (or the web
   frontend's root) that logs any non-200 response with a timestamp.
3. Make a trivial, visible backend code change (e.g. a log line); run `scripts/
   redeploy_service.sh api`.
4. Confirm the script itself reports success only after the container's healthcheck reports
   `healthy`.
5. Confirm the polling loop from step 2 recorded **zero** failed requests throughout the entire
   redeploy window (SC-005) — `worker`/`web`/`db` were never restarted by this operation.
6. Repeat for `worker` (confirm `api`/`web` traffic uninterrupted) and `web`.
7. Run `scripts/redeploy_service.sh db`; confirm the script refuses immediately with a clear
   message and makes no change (FR-013).

## Expected outcomes

- Backup: a dump exists, is restorable, old ones are pruned, and failures are recorded honestly.
- Alerting: exactly the right number of webhooks fire — never zero when something's wrong, never
  more than one per still-ongoing condition, never any when nothing's wrong.
- Redeploy: one service updates; the others provably never went down; `db` is refused outright.
