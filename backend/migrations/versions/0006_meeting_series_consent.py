"""Add `meeting_series_consent` — the auditable, append-only consent gate for
meeting audio ingestion.

Revision ID: 0006_meeting_series_consent
Revises: 0005_ask_queries_response_mode
Create Date: 2026-08-19

specs/019-meeting-audio-ingestion, User Story 2 (FR-004/FR-005). Replaces the
fixture-only `consent_documented` boolean `SimulatedCollector` previously read
directly (specs/019-meeting-audio-ingestion/research.md Decision 3) with a
real, durable, queryable audit trail: one row per consent decision (grant or
revoke), never updated in place — "current status" is always the latest row
per `series_id` (`data-model.md`'s query pattern), the same append-only shape
`retention_job_runs`/`collector_runs` already use.

The `status != 'granted' OR all_parties_confirmed` CHECK constraint enforces
FR-005's all-party rule at the database level too, not only at the
application boundary — the same defense-in-depth precedent
`findings.cited_event_ids`'s non-empty CHECK already sets (constitution P1).

`app_role` needs both SELECT and INSERT here (unlike `retention_job_runs`,
which only ever needed INSERT — that table is never read back through
`app_role`): `GET /api/meeting-audio/consent` and `AudioCollector`/
`SimulatedCollector`'s consent-gate check both read this table back.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0006_meeting_series_consent"
down_revision = "0005_ask_queries_response_mode"
branch_labels = None
depends_on = None

# asyncpg rejects multiple statements in one prepared execution (0003's own note) —
# one op.execute() call per statement.
_STATEMENTS = [
    "CREATE TYPE meeting_series_consent_status AS ENUM ('granted', 'revoked');",
    """
    CREATE TABLE meeting_series_consent (
        id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        series_id               TEXT NOT NULL,
        status                  meeting_series_consent_status NOT NULL,
        all_parties_confirmed   BOOLEAN NOT NULL,
        documented_by_user_id   UUID NOT NULL REFERENCES users(id),
        documented_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
        note                    TEXT,
        CONSTRAINT meeting_series_consent_granted_requires_all_parties
            CHECK (status != 'granted' OR all_parties_confirmed)
    );
    """,
    "CREATE INDEX idx_meeting_series_consent_series_id "
    "ON meeting_series_consent (series_id, documented_at DESC);",
    "GRANT SELECT, INSERT ON meeting_series_consent TO app_role;",
]


def upgrade() -> None:
    for statement in _STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in [
        "REVOKE SELECT, INSERT ON meeting_series_consent FROM app_role;",
        "DROP TABLE meeting_series_consent;",
        "DROP TYPE meeting_series_consent_status;",
    ]:
        op.execute(statement)
