# Quickstart: Embedding Cache (pgvector)

## Prerequisites

- `docker-compose.yml`'s `db` service running the `pgvector/pgvector:pg16` image (this feature's
  own change — a plain `postgres:16` container will fail the new migration).
- No new secrets.

## Setup

1. Migrate: `alembic upgrade head` applies `0008_embedding_cache.py` (`CREATE EXTENSION IF NOT
   EXISTS vector` + `CREATE TABLE embedding_cache`).
2. Nothing else to configure — `CachedEmbeddingAdapter` is wired at the composition root
   (`worker.py`, `scripts/run_readers.py`) unconditionally; there is no feature flag, per P10 (no
   requirement asks for one).

## Validation

**Story 1 (previously-seen content is never re-embedded)**:
1. Seed the ledger and run the Recurrence reader once (`scripts/run_readers.py` or a worker
   `--run-once pipeline`) against a corpus containing at least one repeated title across two
   candidate events.
2. Inspect `embedding_cache` — confirm one row per *distinct* title, not per candidate event.
3. Run the reader again with no new candidates. Confirm (via a request log / call-count check
   against the embeddings provider, or a temporary log line) zero new embedding calls occur.
4. Add one genuinely new candidate title and run again — confirm exactly one new embedding call,
   for that title only.

**Story 2 (a model change never reuses a stale vector)**:
1. With the cache already populated under `OpenAIEmbeddingAdapter.MODEL_ID`, construct
   `CachedEmbeddingAdapter` with a different `model` string for the same content (simulating a
   future model swap) and confirm a fresh embedding call happens rather than a cache hit.
2. Confirm both the old and new model's entries now coexist in `embedding_cache`, keyed
   separately.

**Story 3 (clustering is unaffected)**:
1. Run the Recurrence reader once against a fixed corpus with an empty cache; record its emitted
   findings.
2. Clear findings (not the cache) and run again against the same corpus, now cache-warm.
3. Confirm byte-identical findings both times — same clusters, same magnitude/confidence, same
   cited event IDs.
4. Run the existing `tests/golden_replay/` suite unchanged and confirm it still passes.

## Expected outcome

Repeated candidate titles across Recurrence reader runs cost zero additional embedding-provider
calls; genuinely new content still costs exactly one call each; findings/clustering output is
unchanged from before this feature existed.
