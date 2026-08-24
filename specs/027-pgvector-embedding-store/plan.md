# Implementation Plan: Embedding Cache (pgvector)

**Branch**: `main` | **Date**: 2026-08-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/027-pgvector-embedding-store/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add the `pgvector` Postgres extension and one new table, `embedding_cache`, keyed by
`(content_hash, model)`, and a new `CachedEmbeddingAdapter` (`app.readers.adapters`) implementing
the existing `EmbeddingPort` unchanged — it wraps another `EmbeddingPort` (in practice,
`OpenAIEmbeddingAdapter`), checks the cache before delegating, and writes the result back on a
miss. `RecurrenceReader` itself is **not touched at all**: it already only knows
`self._embeddings.embed(text)` (`EmbeddingPort`'s one method), so swapping which concrete
`EmbeddingPort` gets constructed at the composition root (`backend/app/worker.py`,
`backend/scripts/run_readers.py`) is the entire integration surface. `db`'s image moves from
`postgres:16` to `pgvector/pgvector:pg16` in both `docker-compose.yml` and CI's Postgres service
container (`.github/workflows/ci.yml`) — the extension must actually exist in whatever Postgres
the migration runs `CREATE EXTENSION vector` against.

## Technical Context

**Language/Version**: Python 3.12 — unchanged.

**Primary Dependencies**: None new. Deliberately **not** adding the `pgvector` Python package
(`research.md` Decision 3) — the cache adapter uses raw parameterized SQL via `text()`, matching
every other repository adapter in this codebase (`app.readers.adapters.sqlalchemy_repository`'s own
docstring: "Raw parameterized SQL... no ORM declarative models").

**Storage**: PostgreSQL 16 + the `pgvector` extension (new — `CREATE EXTENSION IF NOT EXISTS
vector`), one new table `embedding_cache(content_hash TEXT, model TEXT, embedding vector(1536),
created_at TIMESTAMPTZ, PRIMARY KEY (content_hash, model))`. 1536 matches
`text-embedding-3-small`'s real output dimension (`OpenAIEmbeddingAdapter`'s only model today).

**Testing**: pytest, real-DB style matching this codebase's convention — a test constructs
`CachedEmbeddingAdapter` against a real (test) Postgres with the extension installed, wraps a fake
`EmbeddingPort` that counts calls, and asserts the count stays flat across repeated `embed()` calls
for the same text. `RecurrenceReader`'s own existing test suite is unmodified and must keep passing
unchanged (User Story 3 / FR-006 — proof by construction, since the reader's code doesn't change).

**Target Platform**: Same Docker Compose stack; `db`'s image changes (see Summary). No new
service/container — `pgvector/pgvector:pg16` is a drop-in Postgres 16 image with the extension
pre-installed, not a separate database.

**Project Type**: Web application backend (Python/FastAPI) — no frontend change.

**Performance Goals**: No new latency target of its own — this is a cost/redundant-work reduction
(SC-001/SC-002), not a new speed requirement. Indirectly helps `specs/026`'s 60s cap by removing
the Recurrence reader's re-embedding cost from every cycle where nothing about the candidate corpus
actually changed.

**Constraints**: Must not change `RecurrenceReader`'s clustering output (FR-006) or the system's
existing golden-replay/reconciliation/monotonicity guarantees (P9) — the cache is purely an
`EmbeddingPort` implementation detail, invisible to everything that consumes embeddings.

**Scale/Scope**: One migration, one new adapter file (`~80` lines), one small edit to
`openai_embedding.py` (exposing its model id as a public class attribute instead of a private
module constant — `research.md` Decision 4), composition-root wiring changes in `worker.py` and
`scripts/run_readers.py`, and the two `docker-compose.yml`/`ci.yml` image changes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies? | Assessment |
|---|---|---|
| P1 Evidence or It Does Not Exist | No | Findings/citations unchanged. |
| P2 The Model Interprets, Code Calculates | No | No scoring code touched. |
| P3 Each Component Refuses to Do the Next One's Job | Yes | `CachedEmbeddingAdapter` does exactly one job (cache-then-delegate) and refuses to know anything about clustering, findings, or the Recurrence reader's own logic — it is a pure `EmbeddingPort` implementation, interchangeable with the uncached one. |
| P4 A Human Always Sends | No | No send capability touched. |
| P5 Admit What We Cannot See | No | No coverage/degraded-state reporting change. |
| P6 Silence Is a Success State | No | Not a dashboard/UI feature (though it does reduce redundant background cost, which is the spirit of P6 — this feature is P6's natural extension into a cost dimension, not a UI dimension). |
| P7 Context Over Sentiment | No | No Tone-reader baseline logic touched. |
| P8 Clean Architecture — the Dependency Rule Is Law | Yes | `CachedEmbeddingAdapter` lives in `app.readers.adapters`, implements the existing `app.readers.application.ports.EmbeddingPort` — zero new port needed (`research.md` Decision 2: a decorator adapter is simpler than a second port + adapter pair, and still fully respects the Dependency Rule, since the *application* layer — `RecurrenceReader` — still depends only on the `EmbeddingPort` abstraction it already had). `.importlinter`'s `readers-application-purity` contract is unaffected: `app.readers.application` still never imports `openai` or `app.readers.adapters` directly. |
| **P9 Test-First Determinism** | **Yes — the central constraint of this whole feature.** | FR-006/FR-008 and User Story 3 exist specifically to guarantee the cache cannot change golden-replay/monotonicity behavior. The clustering algorithm (`cluster_candidates`, `app.readers.domain.services`) is untouched; only the vector *source* changes, never its *value* for identical input text. |
| P10 Simplicity Over Speculative Generality (YAGNI) | **Yes.** | No new Python dependency (Decision 3); no new port (Decision 2); no semantic search capability, no incremental-clustering redesign (`spec.md` Assumptions explicitly rule both out) — this is a cache, and only a cache. |
| P11 Frontend | No | No frontend change. |

**Result**: PASS. No violation requires justification in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/027-pgvector-embedding-store/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output — the one new table
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

No `contracts/` — no new API endpoint or external interface; the only "contract" is the
`EmbeddingPort` interface, which is unchanged (`app/readers/application/ports.py`).

### Source Code (repository root)

```text
backend/
├── migrations/versions/
│   └── 0008_embedding_cache.py               # NEW — CREATE EXTENSION vector; CREATE TABLE embedding_cache
├── app/
│   ├── readers/adapters/
│   │   ├── openai_embedding.py               # MODIFIED — _MODEL -> public MODEL_ID class attribute
│   │   └── pgvector_embedding_cache.py       # NEW — CachedEmbeddingAdapter(EmbeddingPort)
│   └── worker.py                             # MODIFIED — construct CachedEmbeddingAdapter, not OpenAIEmbeddingAdapter, directly
└── scripts/
    └── run_readers.py                         # MODIFIED — same composition-root change as worker.py
data-base/
├── 10-ddl-appendix.md                         # MODIFIED — CREATE EXTENSION vector + embedding_cache DDL, schema-discipline first
└── 05-schema-reasoning.md                     # MODIFIED — prose doc for the new table
docker-compose.yml                              # MODIFIED — db image -> pgvector/pgvector:pg16
.github/workflows/ci.yml                        # MODIFIED — test job's Postgres service image -> pgvector/pgvector:pg16
```

**Structure Decision**: The new adapter sits alongside `openai_embedding.py` in
`app/readers/adapters/` (same module, same ring) — it is another `EmbeddingPort` implementation,
not a new architectural layer. Everything else is composition-root wiring (`worker.py`,
`scripts/run_readers.py`) or infrastructure config (Compose/CI images, DDL) — no new module.

## Complexity Tracking

*No Constitution Check violations — this section is intentionally empty.*
