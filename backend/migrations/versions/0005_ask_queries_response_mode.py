"""Add `ask_queries.response_mode`.

Revision ID: 0005_ask_queries_response_mode
Revises: 0004_meeting_finding_type
Create Date: 2026-08-17

specs/014-ask-agent-response-formats — the Ask agent gains a third response
shape (Markdown text) and a fourth (a component-and-text hybrid) alongside
its existing two (a structured component, or a decline/fallback). Without
this column, a `text_only` answer (no component) is indistinguishable in the
log from a genuine decline — both currently look like "no component"
(`rendered_component IS NULL`). Nullable and additive, matching this
project's schema-discipline convention (`data-base/10-ddl-appendix.md`
updated in the same change) — `NULL` for decline/fallback rows, mirroring
`rendered_component`'s existing `NULL`-for-fallback convention rather than
inventing a new sentinel.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0005_ask_queries_response_mode"
down_revision = "0004_meeting_finding_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE ask_queries ADD COLUMN response_mode TEXT;")


def downgrade() -> None:
    op.execute("ALTER TABLE ask_queries DROP COLUMN response_mode;")
