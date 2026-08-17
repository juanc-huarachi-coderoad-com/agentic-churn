"""Seed the `meeting_commitment` finding_type_config row.

Revision ID: 0004_meeting_finding_type
Revises: 0003_production_hardening
Create Date: 2026-08-17

specs/011-production-hardening — User Story 6 (Post-MVP sources). A gap found
during implementation, not at plan time: `MeetingReader` (FR-023, REQ-M5-14)
needs a `finding_type_config` row before `ValidationGate` will ever pass one
of its findings (every other reader's finding_type was already seeded in
`data-base/11-seed-data.sql`; the Meeting reader's wasn't, since nothing
scaffolded it beyond the empty `meeting_reader.py` stub feature 005 left
behind). `data-base/11-seed-data.sql` gains the same row for a fresh install;
this migration applies it to every database that already ran that seed once
(`0003`'s own precedent — new rows this feature needs on top of the original
one-time seed go in a migration, not a rewrite of the seed file alone).

`version` is read from whatever value the existing rows currently share
(`SELECT version FROM finding_type_config LIMIT 1`, the same invariant
`SqlAlchemyFindingTypeConfigWriter` (User Story 4) depends on) rather than a
hardcoded `'v1'` literal — a literal would silently break that invariant on
any database where User Story 4's weight-recalibration endpoint has already
bumped the shared version past its initial seed value.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0004_meeting_finding_type"
down_revision = "0003_production_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "INSERT INTO finding_type_config "
        "(finding_type, base_points, confidence_floor, min_evidence_count, "
        "half_life_days, version) "
        "SELECT 'meeting_commitment', 10.00, 0.60, 1, 14, version "
        "FROM finding_type_config LIMIT 1 "
        "ON CONFLICT (finding_type) DO NOTHING;"
    )


def downgrade() -> None:
    op.execute("DELETE FROM finding_type_config WHERE finding_type = 'meeting_commitment';")
