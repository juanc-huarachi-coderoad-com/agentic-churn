"""Anchor `draft_messages` to a `score_contribution` instead of an `issue`.

Revision ID: 0007_draft_finding_anchor
Revises: 0006_meeting_series_consent
Create Date: 2026-08-21

`issues`/`finding_issue_map` (specs/004-score-engine) were always documented
as fixture-only data, populated solely by `backend/scripts/
seed_score_fixture.py`'s hand-authored worked example — no use case,
background job, or reader in this codebase ever writes a real row into
either table (confirmed by inspection, and by live testing against the
`demo-wara` account through both its Stage 1 and Stage 2 fixtures: every
`score_contributions.issue_id` came back `NULL`, so the Ask agent's
`write_to_stakeholder` handoff always produced `issue_id: null` and the
Draft Composer link never rendered — a live-verified dead end, not a
theoretical one).

Feature 009 (Draft Composer) built `draft_messages.issue_id NOT NULL
REFERENCES issues(id)` on the assumption that finding-to-issue clustering
(promised as "feature 005" in specs/004-score-engine/spec.md) would exist by
the time it shipped. It never did. Every other read path this feature
actually needs — evidence, damping disclosure, feedback — already keys off
`score_contributions.id` (specs/008-narrator-and-ask-agent's evidence trace),
so this migration re-anchors the one column that didn't, rather than
building the promised-but-never-implemented clustering just to unblock a
single foreign key. `issues`/`finding_issue_map` themselves are untouched —
still available, unchanged, for a future real clustering effort.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0007_draft_finding_anchor"
down_revision = "0006_meeting_series_consent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # `issue_id` becomes nullable rather than being dropped outright — any
    # pre-existing row (e.g. from the `seed_score_fixture.py` worked
    # example) keeps its value; every new row goes through the application
    # layer's `score_contribution_id`-only path instead (Pydantic's
    # `DraftRequest` makes it a required field, so every INSERT this code
    # base performs from here on always sets it).
    op.execute("DROP INDEX IF EXISTS idx_draft_messages_issue_id;")
    op.execute("ALTER TABLE draft_messages ALTER COLUMN issue_id DROP NOT NULL;")
    op.execute(
        "ALTER TABLE draft_messages "
        "ADD COLUMN score_contribution_id UUID REFERENCES score_contributions(id);"
    )
    op.execute(
        "CREATE INDEX idx_draft_messages_score_contribution_id "
        "ON draft_messages(score_contribution_id);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_draft_messages_score_contribution_id;")
    op.execute("ALTER TABLE draft_messages DROP COLUMN score_contribution_id;")
    op.execute("ALTER TABLE draft_messages ALTER COLUMN issue_id SET NOT NULL;")
    op.execute("CREATE INDEX idx_draft_messages_issue_id ON draft_messages(issue_id);")
