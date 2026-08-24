# Data Model: Embedding Cache (pgvector)

## `embedding_cache`

One row per (content, model) pair ever embedded — a pure cache table, never referenced by any
other table's foreign key, never read by anything except `CachedEmbeddingAdapter`.

| Field | Type | Description |
|---|---|---|
| `content_hash` | TEXT, part of PK | Hex SHA-256 of the exact candidate title string embedded (`research.md` Decision 1) |
| `model` | TEXT, part of PK | The embedding model identifier that produced this vector (`OpenAIEmbeddingAdapter.MODEL_ID`, `research.md` Decision 4) |
| `embedding` | `vector(1536)` NOT NULL | The embedding itself — 1536 dimensions, matching `text-embedding-3-small`'s real output size |
| `created_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | When this entry was first written — diagnostic only, not read by any lookup |

**Primary key**: `(content_hash, model)` — a lookup is always an exact match on both columns
together (FR-002/FR-005); no other query shape exists against this table.

**No foreign keys in or out.** This table is deliberately disconnected from the rest of the schema
— `findings`, `events`, and everything the Recurrence reader actually produces continue to cite
real event IDs exactly as before (P1); `embedding_cache` is purely a performance detail behind
`EmbeddingPort`, invisible to every other table and every other reader.

**No deletion path in this feature.** Nothing in `spec.md` requires evicting stale entries — a
title's embedding under a given model never changes, so there is no "staleness" to clean up within
one model's entries; entries under a retired model simply stop being read (User Story 2), not
actively purged. Retention/cleanup of this table, if ever needed, is out of scope here (P10 — no
requirement asks for it).

## DDL (added to `data-base/10-ddl-appendix.md`, "05 · Reasoning" section, per schema discipline)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE embedding_cache (
    content_hash TEXT NOT NULL,
    model        TEXT NOT NULL,
    embedding    vector(1536) NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (content_hash, model)
);
```
