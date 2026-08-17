"""Production hardening: retention job audit trail, weight-change audit trail,
and the grants both need.

Revision ID: 0003_production_hardening
Revises: 0002_ask_insufficient_history
Create Date: 2026-08-16

specs/011-production-hardening — User Story 1 (retention/crypto-shredding) needs
a durable, queryable record of each retention job run (FR-002) independent of
`shredder_role`'s existing, previously-unused `UPDATE (body_encrypted) ON events`
grant (data-base/10-ddl-appendix.md, granted since 0001 but never exercised by a
real connection until this feature). No new grant for `raw_envelopes` is added
here — a real design correction found while implementing the retention job
itself: `raw_envelopes.payload_encrypted` is `NOT NULL`, and the DDL's own
crypto-shredding note already says destroying the key alone is sufficient for
that table (no row ever needs touching); only `events.body_encrypted` was ever
designed to be nulled. An earlier draft of this migration granted `UPDATE
(payload_encrypted)`/`SELECT` on `raw_envelopes` to `shredder_role` for exactly
that mistaken reason — removed before this revision was ever applied anywhere
but a local dev database.

This revision does add one narrow grant `0001` didn't anticipate: `SELECT
(data_key_ref, body_encrypted) ON events TO shredder_role`. Found only by
actually running the retention job against a real Postgres, not by inspection:
Postgres requires read access to every column an `UPDATE ... WHERE` clause
references, not just the column being written — `shredder_role`'s original
`UPDATE (body_encrypted)`-only grant let it write the column but not evaluate
`WHERE data_key_ref = ... AND body_encrypted IS NOT NULL`, so the very first
real shredding attempt failed with `InsufficientPrivilegeError`. Scoped to
exactly the two columns the query touches, not a blanket `SELECT ON events`.

User Story 4 (weight recalibration) needs a durable audit trail of every
`finding_type_config.base_points` edit (FR-014) and, since nothing has ever
written to `finding_type_config` before this feature, a fresh `UPDATE` grant for
`app_role` on it.

User seeding (`ae-demo`/`admin-demo`, User Stories 2 & 4) is NOT in this
migration — this codebase seeds users via `data-base/11-seed-data.sql` +
`scripts/seed.py`, not a migration (found during implementation; earlier
`tasks.md` guidance to seed them here was corrected before this file was
written).
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_production_hardening"
down_revision = "0002_ask_insufficient_history"
branch_labels = None
depends_on = None


# asyncpg (this codebase's async driver) rejects multiple statements in one prepared
# execution — 0001_initial_schema.py hit this first and solved it with a dollar-quote-
# aware splitter for its much larger DDL block; this migration is small enough that one
# `op.execute()` call per statement is simpler and needs no such helper.
_STATEMENTS = [
    "CREATE TYPE retention_job_status AS ENUM ('succeeded', 'failed');",
    """
    CREATE TABLE retention_job_runs (
        id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        started_at          TIMESTAMPTZ NOT NULL,
        completed_at        TIMESTAMPTZ,
        buckets_evaluated   INTEGER NOT NULL DEFAULT 0,
        buckets_shredded    INTEGER NOT NULL DEFAULT 0,
        status              retention_job_status NOT NULL,
        error_detail        TEXT,
        CONSTRAINT retention_job_runs_shredded_le_evaluated
            CHECK (buckets_shredded <= buckets_evaluated),
        CONSTRAINT retention_job_runs_completed_after_started
            CHECK (completed_at IS NULL OR completed_at >= started_at)
    );
    """,
    """
    CREATE TABLE finding_type_config_changes (
        id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        finding_type            TEXT NOT NULL REFERENCES finding_type_config(finding_type),
        previous_base_points    NUMERIC(6,2) NOT NULL,
        new_base_points         NUMERIC(6,2) NOT NULL CHECK (new_base_points >= 0),
        changed_by_user_id      UUID NOT NULL REFERENCES users(id),
        changed_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
        config_version_after    TEXT NOT NULL
    );
    """,
    # retention_job_runs/finding_type_config_changes are both insert-only audit
    # tables (data-model.md), matching replay_runs/collector_runs' existing
    # precedent of no UPDATE/DELETE grant to app_role.
    "GRANT INSERT ON retention_job_runs, finding_type_config_changes TO app_role;",
    # Postgres requires read access to every column an UPDATE ... WHERE clause
    # references, not just the column being written — found only by actually
    # running the retention job against a real Postgres (see module docstring).
    "GRANT SELECT (data_key_ref, body_encrypted) ON events TO shredder_role;",
    # finding_type_config has never had a writer before this feature (only ever
    # seeded once, in data-base/11-seed-data.sql).
    "GRANT UPDATE (base_points, version) ON finding_type_config TO app_role;",
]


def upgrade() -> None:
    for statement in _STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in [
        "REVOKE UPDATE (base_points, version) ON finding_type_config FROM app_role;",
        "REVOKE SELECT (data_key_ref, body_encrypted) ON events FROM shredder_role;",
        "REVOKE INSERT ON retention_job_runs, finding_type_config_changes FROM app_role;",
        "DROP TABLE finding_type_config_changes;",
        "DROP TABLE retention_job_runs;",
        "DROP TYPE retention_job_status;",
    ]:
        op.execute(statement)
