# Phase 1 Data Model: Production Deployment Hardening II

## `backup_job_runs` (new table)

One row per attempted `pg_dump` run, mirroring `retention_job_runs`' own shape
(specs/011-production-hardening).

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID PRIMARY KEY DEFAULT gen_random_uuid()` | |
| `started_at` | `TIMESTAMPTZ NOT NULL` | |
| `completed_at` | `TIMESTAMPTZ` | `NULL` until the run finishes either way |
| `destination_path` | `TEXT` | `NULL` if the run failed before producing a file |
| `file_size_bytes` | `BIGINT` | `NULL` if the run failed before producing a file |
| `status` | `backup_job_status NOT NULL` | enum: `succeeded`, `failed` |
| `error_detail` | `TEXT` | `NULL` on success |

Constraint: `completed_at IS NULL OR completed_at >= started_at` (matches
`retention_job_runs_completed_after_started`'s own precedent).

Insert-only, like `retention_job_runs`/`collector_runs` — `app_role` gets `GRANT INSERT` only, no
`UPDATE`/`DELETE`.

## `alerts` (new table)

One row per fired notification for one condition's one occurrence; resolved when the condition
next evaluates false.

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID PRIMARY KEY DEFAULT gen_random_uuid()` | |
| `condition_name` | `TEXT NOT NULL` | one of `score_source_degraded`, `backup_job_failed`, `retention_job_failed` — not an enum, so a fourth condition can be added later without a migration (the *set* of conditions the use case checks is still fixed in code per P10 — this is just storage flexibility, not an extensibility mechanism) |
| `message` | `TEXT NOT NULL` | the human-readable text sent in the webhook |
| `fired_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | |
| `resolved_at` | `TIMESTAMPTZ` | `NULL` while the condition is still ongoing |

Constraints:
- `resolved_at IS NULL OR resolved_at >= fired_at`
- `UNIQUE (condition_name) WHERE resolved_at IS NULL` (partial unique index) — enforces FR-010 at
  the database level: at most one open alert per condition, ever.

`app_role` gets `SELECT`, `INSERT`, and `UPDATE` (unlike the insert-only tables above) — resolving
an alert is an `UPDATE ... SET resolved_at = now() WHERE condition_name = ... AND resolved_at IS
NULL`, matching `0006_meeting_series_consent.py`'s own precedent for a table that needs `UPDATE`
where insert-only tables don't.

## Relationships

- `backup_job_runs` and `alerts` are independent of each other and of every other table — the
  alert-check use case *reads* `backup_job_runs`/`retention_job_runs`/`score_runs` but has no
  foreign key into any of them (a condition's truth is re-evaluated fresh each cycle from the
  latest row, not tied to one specific run's id — matching how `RunAlertCheckUseCase` re-derives
  "is this condition true right now," not "was it true when alert X fired").
- No existing table changes.
