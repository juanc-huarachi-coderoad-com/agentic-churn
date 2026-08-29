"""Backup job audit trail and provider-agnostic alerting.

Revision ID: 0009_backup_and_alerting
Revises: 0008_embedding_cache
Create Date: 2026-08-28

specs/031-production-deployment-hardening-ii. Two new tables:

`backup_job_runs` mirrors `retention_job_runs`' own shape (0003_production_hardening) —
one row per attempted `pg_dump` run, insert-only, `app_role` gets `INSERT`. Unlike
`retention_job_runs`, it also gets `SELECT` for `app_role`: the new alert-check use case
(this same feature) reads the latest row back to detect a failed backup run — the exact
reason `meeting_series_consent` (0006) needed both grants where `retention_job_runs` alone
didn't.

`alerts` records one row per fired notification for one condition's one occurrence,
resolved when the condition next evaluates false. The `alerts_one_open_per_condition`
partial unique index enforces "at most one open alert per condition" at the database
level (`research.md` Decision 3) — the same defense-in-depth precedent
`retention_job_runs_shredded_le_evaluated`/`findings.cited_event_ids` already set.
`app_role` needs `SELECT`, `INSERT`, and `UPDATE` here (resolving an alert is an
`UPDATE ... SET resolved_at = now()`), matching `meeting_series_consent`'s own precedent
for a table application code needs to both write and later mutate.

Also grants `app_role` `SELECT` on the pre-existing `retention_job_runs` table — a genuinely
new need introduced by this feature (the alert-check use case reads its latest row too),
not present in 0003 because nothing needed to read it back before now.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0009_backup_and_alerting"
down_revision = "0008_embedding_cache"
branch_labels = None
depends_on = None


_STATEMENTS = [
    "CREATE TYPE backup_job_status AS ENUM ('succeeded', 'failed');",
    """
    CREATE TABLE backup_job_runs (
        id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        started_at          TIMESTAMPTZ NOT NULL,
        completed_at        TIMESTAMPTZ,
        destination_path    TEXT,
        file_size_bytes     BIGINT,
        status              backup_job_status NOT NULL,
        error_detail        TEXT,
        CONSTRAINT backup_job_runs_completed_after_started
            CHECK (completed_at IS NULL OR completed_at >= started_at)
    );
    """,
    """
    CREATE TABLE alerts (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        condition_name  TEXT NOT NULL,
        message         TEXT NOT NULL,
        fired_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
        resolved_at     TIMESTAMPTZ,
        CONSTRAINT alerts_resolved_after_fired
            CHECK (resolved_at IS NULL OR resolved_at >= fired_at)
    );
    """,
    # The database-enforced de-duplication guarantee itself (research.md Decision 3) —
    # a partial unique index, not an application-level check, so it holds even if two
    # alert-check cycles somehow overlap.
    "CREATE UNIQUE INDEX alerts_one_open_per_condition "
    "ON alerts (condition_name) WHERE resolved_at IS NULL;",
    "GRANT SELECT, INSERT ON backup_job_runs TO app_role;",
    "GRANT SELECT, INSERT, UPDATE ON alerts TO app_role;",
    "GRANT SELECT ON retention_job_runs TO app_role;",
]


def upgrade() -> None:
    for statement in _STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in [
        "REVOKE SELECT ON retention_job_runs FROM app_role;",
        "REVOKE SELECT, INSERT, UPDATE ON alerts FROM app_role;",
        "REVOKE SELECT, INSERT ON backup_job_runs FROM app_role;",
        "DROP INDEX alerts_one_open_per_condition;",
        "DROP TABLE alerts;",
        "DROP TABLE backup_job_runs;",
        "DROP TYPE backup_job_status;",
    ]:
        op.execute(statement)
