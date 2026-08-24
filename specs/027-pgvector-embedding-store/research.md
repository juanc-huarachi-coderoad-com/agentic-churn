# Research: Embedding Cache (pgvector)

## Decision 1: Cache key is `(content_hash, model)`, `content_hash = sha256(text)`

**Decision**: `embedding_cache`'s primary key is `(content_hash TEXT, model TEXT)`, where
`content_hash` is the hex SHA-256 digest of the exact candidate title string passed to
`EmbeddingPort.embed()`.

**Rationale**: `RecurrenceReader.interpret()` calls `self._embeddings.embed(c.title)` — the input
is always a full string, never a pre-hashed value, so the cache needs its own stable, fixed-length
key derived from that string; storing the raw title as the key directly would work too but wastes
index space and risks a key-length limit on unusually long titles, where a fixed 64-character hash
never does. SHA-256 is already available in Python's standard library (`hashlib`) — no new
dependency. `spec.md`'s Edge Cases explicitly scope "exact same content" to byte-identical text, no
normalization — hashing the raw string is exactly that: two titles differing only in whitespace
hash differently and are correctly treated as different content (FR-002's own "exact content"
wording).

**Alternatives considered**: Using the title as the primary key directly (TEXT PK) — rejected,
index bloat with no benefit over a fixed-length hash for this access pattern (always exact lookup,
never a range scan or prefix search). A weaker/faster hash (e.g. MD5) — rejected, no measured
performance need to justify a weaker collision guarantee for a security-adjacent, if not
security-critical, cache key.

## Decision 2: A decorator adapter (`CachedEmbeddingAdapter`), not a second port

**Decision**: `CachedEmbeddingAdapter` implements the *existing* `EmbeddingPort` interface
(`app/readers/application/ports.py`, unchanged) — constructed with a database session, a `model`
identifier string, and another `EmbeddingPort` to delegate to on a cache miss. No new
`EmbeddingCachePort` abstraction is added.

**Rationale**: The original roadmap sketch for this feature (the approved production-readiness
plan) proposed a new `EmbeddingCachePort` application-layer interface plus a separate adapter
implementing it, with `RecurrenceReader.interpret()` modified to call cache-then-embed explicitly.
Reading the actual code changes that: `RecurrenceReader` already depends on nothing but
`EmbeddingPort.embed(text) -> list[float]` — it has no idea whether the concrete implementation
calls OpenAI directly, checks a cache first, or does anything else. A decorator adapter that
*is itself* an `EmbeddingPort` implementation achieves every requirement in `spec.md` (cache-check,
cache-write, model-scoped keys, honest failure on a genuine miss) with **zero changes to
`recurrence_reader.py`** — a smaller diff, less surface area to regress P9's determinism
guarantee on, and a cleaner instance of P3 ("each component refuses to do the next one's job"):
the reader doesn't need to know caching exists at all. The composition root
(`worker.py`/`scripts/run_readers.py`) is the only place that changes, wiring
`CachedEmbeddingAdapter(session, model=..., wrapped=OpenAIEmbeddingAdapter(api_key))` in place of
`OpenAIEmbeddingAdapter(api_key)` directly.

**Alternatives considered**: The original two-port sketch (a new `EmbeddingCachePort` +
`RecurrenceReader` modified to call it explicitly) — rejected on inspection: it would touch an
already-correct, already-tested reader for no behavioral gain over the decorator shape, and adds a
second interface (`EmbeddingCachePort`) whose only consumer would be the one adapter that also
implements `EmbeddingPort` — a distinction without a difference here (P10).

## Decision 3: No new Python dependency (`pgvector` PyPI package) — raw SQL, matching every other adapter

**Decision**: `CachedEmbeddingAdapter` reads/writes the `vector` column via plain parameterized
`text()` SQL — serializing `list[float]` to a Postgres vector literal string (`'[0.1,0.2,...]'`)
on write, and parsing the column's text representation back to `list[float]` on read — not the
`pgvector` PyPI package's SQLAlchemy/asyncpg type integration.

**Rationale**: Every existing repository adapter in this codebase is raw parameterized SQL against
the DDL, explicitly documented as deliberate ("no ORM declarative models" —
`app/readers/adapters/sqlalchemy_repository.py`'s own module docstring, matching every other
adapter file in this codebase). Adding the `pgvector` package would introduce the first ORM-style
typed column integration in a codebase that has consistently avoided that pattern everywhere else,
for one table, to save a small amount of string formatting — a real inconsistency for a small,
avoidable convenience (P10).

**Alternatives considered**: The `pgvector` Python package (`pgvector.sqlalchemy.Vector` /
`pgvector.asyncpg` codec) — rejected above. Storing the embedding as `FLOAT8[]` (a plain Postgres
array) instead of `vector` — rejected: this repository's own roadmap plan specifically chose
pgvector as the extension (not a plain array column) partly because it's the standard, and partly
because a `vector` column keeps the door open for a future similarity-search feature to use
pgvector's indexing (`spec.md` Assumptions: explicitly out of scope *now*, but the schema choice
shouldn't foreclose it later for free).

## Decision 4: `OpenAIEmbeddingAdapter`'s model id becomes a public class attribute

**Decision**: `openai_embedding.py`'s private module constant `_MODEL = "text-embedding-3-small"`
becomes a public class attribute, `OpenAIEmbeddingAdapter.MODEL_ID = "text-embedding-3-small"` —
referenced by both the adapter's own `embed()` method and by composition-root code constructing
`CachedEmbeddingAdapter(..., model=OpenAIEmbeddingAdapter.MODEL_ID, ...)`.

**Rationale**: The cache's model-scoping (User Story 2/FR-005) needs *some* string identifying
"which model produced this vector," and that string must never drift out of sync with what
`OpenAIEmbeddingAdapter` actually calls. There is no existing `settings.embedding_model_id` field
(unlike `reader_model_id`/`generation_model_id` for the two Claude models) — introducing one now
would duplicate the same string in two places (`config.py` and `openai_embedding.py`) with no
mechanism keeping them in sync. Exposing the adapter's own already-existing constant as public and
referencing it directly at the one composition-root call site avoids that duplication entirely.

**Alternatives considered**: A new `settings.embedding_model_id` config field, defaulting to
`"text-embedding-3-small"`, read independently by both files — rejected: two independent sources
of truth for the same string is exactly the drift risk `architecture/03-technology-stack.md`
already flags as a real upgrade path ("a config change... if clustering quality ever needs it") —
if that config change ever happens, it must change in exactly one place, not two.

## Decision 5: `db`'s image changes in both `docker-compose.yml` and CI — not just one

**Decision**: `docker-compose.yml`'s `db.image` and `.github/workflows/ci.yml`'s `test` job's
`services.db.image` both change from `postgres:16` to `pgvector/pgvector:pg16`.

**Rationale**: The new Alembic migration runs `CREATE EXTENSION IF NOT EXISTS vector` — that
statement fails outright against a vanilla `postgres:16` image, which does not ship the extension's
binary. Missing the CI image change would be caught immediately by a failing `test` job (matching
`specs/025-ci-cd-github-actions`'s whole point — a real, enforced gate), but it's cheaper to get
right the first time than to rediscover it via a red CI run, per this feature's own task list.
`pgvector/pgvector:pg16` is a drop-in Postgres 16 image with the extension pre-installed — no other
service, port, or volume changes.

**Alternatives considered**: Installing the extension via a custom `Dockerfile`/init script on top
of `postgres:16` instead of switching images — rejected, `pgvector/pgvector:pg16` is the
extension's own officially published image for exactly this Postgres version; building a custom
image to reproduce it would be needless maintenance (P10).
