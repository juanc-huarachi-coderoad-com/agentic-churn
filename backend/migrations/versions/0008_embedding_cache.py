"""Add the pgvector extension and the embedding_cache table.

Revision ID: 0008_embedding_cache
Revises: 0007_draft_finding_anchor
Create Date: 2026-08-24

specs/027-pgvector-embedding-store — a pure cache table for the Recurrence reader's
embeddings, keyed by (content_hash, model), with no foreign key in or out of the rest
of the schema. Downgrade drops only the table, leaving the extension installed —
matching this repository's own precedent for `pgcrypto` in 0001_initial_schema.py,
which is likewise never dropped by any later migration.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0008_embedding_cache"
down_revision = "0007_draft_finding_anchor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute(
        "CREATE TABLE embedding_cache ("
        "content_hash TEXT NOT NULL, "
        "model TEXT NOT NULL, "
        "embedding vector(1536) NOT NULL, "
        "created_at TIMESTAMPTZ NOT NULL DEFAULT now(), "
        "PRIMARY KEY (content_hash, model)"
        ");"
    )


def downgrade() -> None:
    op.execute("DROP TABLE embedding_cache;")
