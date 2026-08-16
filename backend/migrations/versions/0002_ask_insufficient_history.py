"""Add 'insufficient_history' to the declined_reason enum.

Revision ID: 0002_ask_insufficient_history
Revises: 0001_initial_schema
Create Date: 2026-08-15

specs/008-narrator-and-ask-agent — the Ask agent's "is this normal for X?"
intent reuses the Tone reader's per-stakeholder baseline (feature 007), which
honestly abstains below 5 confirmed-baseline messages. That failure mode is
distinct from `source_not_connected` (the source IS connected, there just
isn't enough of this person's history yet) — Clarifications, 2026-08-15.
`declined_reason` is a real Postgres ENUM type (data-base/10-ddl-appendix.md),
not a CHECK constraint, so this value has to be added via a migration, not
just a documentation update (research.md Decision 6).
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_ask_insufficient_history"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Postgres 12+ allows ADD VALUE inside a transaction as long as the new
    # value isn't used in the same transaction — Alembic's default
    # transactional-DDL behavior is fine here.
    op.execute("ALTER TYPE declined_reason ADD VALUE IF NOT EXISTS 'insufficient_history';")


def downgrade() -> None:
    # Postgres has no ALTER TYPE ... DROP VALUE. Reversing this cleanly would
    # mean rebuilding the enum type from scratch (rename old type, CREATE TYPE
    # with the original 4 values, cast the column, drop the renamed old type)
    # and would fail outright if any row already uses 'insufficient_history' —
    # the same "big-bang, no partial downgrade" posture 0001_initial_schema.py
    # already takes for this schema. Left as a no-op; a genuine downgrade of
    # this revision is a full-database restore from a pre-migration snapshot,
    # not a scripted ALTER.
    pass
