---

description: "Task list for feature 027 — Embedding Cache (pgvector)"
---

# Tasks: Embedding Cache (pgvector)

**Input**: Design documents from `specs/027-pgvector-embedding-store/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: A real-DB test of `CachedEmbeddingAdapter` against a real Postgres with the extension
installed, matching this codebase's convention; `RecurrenceReader`'s own existing test suite is the
non-regression proof for User Story 3 (FR-006) — it needs zero changes and must keep passing.

**Organization**: Tasks are grouped by the three user stories in `spec.md`.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 Change `docker-compose.yml`'s `db.image` from `postgres:16` to `pgvector/pgvector:pg16`
      (`research.md` Decision 5).
- [x] T002 Change `.github/workflows/ci.yml`'s `test` job `services.db.image` from `postgres:16`
      to `pgvector/pgvector:pg16` — without this, `alembic upgrade head` fails on `CREATE
      EXTENSION vector` in CI (`research.md` Decision 5).
- [x] T003 Add `embedding_cache`'s DDL to `data-base/10-ddl-appendix.md` (schema discipline —
      DDL first), in the "05 · Reasoning" section near `cluster_method`, per `data-model.md`.
- [x] T004 [P] Add a short "embedding_cache" subsection to `data-base/05-schema-reasoning.md`,
      matching that file's existing table-doc style (plain-terms summary + field table).
- [x] T005 New migration `backend/migrations/versions/0008_embedding_cache.py` (`revision =
      "0008_embedding_cache"`, `down_revision = "0007_draft_finding_anchor"`): `op.execute` for
      `CREATE EXTENSION IF NOT EXISTS vector;` then the `embedding_cache` table DDL from
      `data-model.md`; `downgrade()` drops only the table (`DROP TABLE embedding_cache`), leaving
      the extension installed — confirmed precedent: `pgcrypto`'s own `CREATE EXTENSION` in
      `0001_initial_schema.py` is never dropped by any later migration either; an installed-but-
      unused extension is harmless, and dropping a shared Postgres extension is a heavier
      operation than this feature's own downgrade path needs to own.

**Checkpoint**: `alembic upgrade head` succeeds against a `pgvector/pgvector:pg16` container; the
table exists.

---

## Phase 2: Foundational (Blocking Prerequisites)

- [x] T006 In `backend/app/readers/adapters/openai_embedding.py`, change `_MODEL` (private module
      constant) to `MODEL_ID` (public class attribute on `OpenAIEmbeddingAdapter`), updating the
      one internal reference in `embed()` (`research.md` Decision 4). No behavior change — same
      string value (`"text-embedding-3-small"`), just made addressable from outside the module.

**Checkpoint**: `OpenAIEmbeddingAdapter.MODEL_ID` is importable and equals the same string
`embed()` already uses internally — confirmed by the existing Recurrence reader tests still
passing unchanged.

---

## Phase 3: User Story 1 - Previously-seen content is never re-embedded (Priority: P1) 🎯 MVP

**Goal**: A `CachedEmbeddingAdapter` implementing `EmbeddingPort`, wired at the composition root in
place of `OpenAIEmbeddingAdapter` directly.

**Independent Test**: Run the Recurrence reader twice with an unchanged corpus; confirm zero
embedding-provider calls on the second run (`quickstart.md` Story 1).

### Implementation for User Story 1

- [x] T007 [US1] New `backend/app/readers/adapters/pgvector_embedding_cache.py`:
      `CachedEmbeddingAdapter(EmbeddingPort)`, constructor `(session: AsyncSession, model: str,
      wrapped: EmbeddingPort)`. `embed(text)`: compute `content_hash =
      hashlib.sha256(text.encode()).hexdigest()`; `SELECT embedding::text FROM embedding_cache
      WHERE content_hash = :h AND model = :m`; on hit, parse the `vector`'s text representation
      (`[0.1,0.2,...]`) back into `list[float]` and return it; on miss, call
      `await self._wrapped.embed(text)`, then `INSERT INTO embedding_cache (content_hash, model,
      embedding) VALUES (:h, :m, :v::vector) ON CONFLICT (content_hash, model) DO NOTHING`
      (serializing the returned `list[float]` as a `'[...]'` literal string for the `:v` bind
      param — `research.md` Decision 3, no `pgvector` package), and return the freshly-computed
      vector. FR-007: a miss whose delegate call raises MUST propagate that exception unchanged
      (no swallowing, no partial cache write) — the reader's existing honest-failure behavior for
      a genuine miss is preserved exactly.
- [x] T008 [US1] In `backend/app/worker.py`'s `_orchestrate_pipeline()`, replace
      `RecurrenceReader(..., OpenAIEmbeddingAdapter(settings.openai_api_key), ...)` with
      `RecurrenceReader(..., CachedEmbeddingAdapter(session, OpenAIEmbeddingAdapter.MODEL_ID,
      OpenAIEmbeddingAdapter(settings.openai_api_key)), ...)`.
- [x] T009 [US1] Same composition-root change in `backend/scripts/run_readers.py` (the manual
      verification script — must exercise the same cached path, not silently diverge from
      `worker.py`'s wiring).

### Tests for User Story 1

- [x] T010 [P] [US1] New `backend/tests/unit/test_cached_embedding_adapter.py`: a fake
      `EmbeddingPort` counting calls; assert `CachedEmbeddingAdapter.embed()` called twice with
      the same text against a real (test) Postgres results in exactly one call to the fake, and
      the second call's returned vector matches the first's exactly.
- [x] T011 [P] [US1] Same file: assert two *different* texts each cause one call to the fake
      (SC-002's "only new content" behavior, not just "the cache exists").

**Checkpoint**: User Story 1 fully functional — repeated content costs zero additional provider
calls.

---

## Phase 4: User Story 2 - A model change never reuses a stale vector (Priority: P2)

**Goal**: Confirm the `model` half of the cache key actually isolates different models' entries.

**Independent Test**: Populate under model A, query under model B for the same text, confirm a
fresh call happens (`quickstart.md` Story 2).

### Tests for User Story 2

- [x] T012 [US2] Same test file: construct two `CachedEmbeddingAdapter`s sharing one session but
      different `model` strings ("model-a", "model-b") wrapping two separate counting fakes;
      `embed()` the same text through both; assert **both** fakes were called once (no cross-model
      reuse), and that `embedding_cache` now holds two distinct rows for that one `content_hash`.

**Checkpoint**: User Stories 1 and 2 both independently verified.

---

## Phase 5: User Story 3 - Clustering results are unaffected by caching (Priority: P3)

**Goal**: Prove FR-006/FR-008 — no behavior change downstream of the embedding source.

**Independent Test**: Same corpus, cold vs. warm cache, byte-identical findings
(`quickstart.md` Story 3).

### Implementation for User Story 3

*No new implementation* — `RecurrenceReader`/`cluster_candidates` are untouched by design
(`research.md` Decision 2); this story is entirely verification that the decorator shape actually
delivered on that promise.

- [x] T013 [US3] Live-verify: run `tests/scoring/test_worked_example.py` and
      `tests/golden_replay/` unchanged, against a database with `CachedEmbeddingAdapter` wired in
      — confirm both still pass with no modification to either test file, proving the cache is
      invisible to the worked-example/replay guarantees by construction.
- [x] T014 [US3] Live-verify: run the Recurrence reader twice against the same corpus (cold cache,
      then warm cache) via `scripts/run_readers.py`, and diff the resulting `findings` rows for
      that reader — confirm byte-identical `magnitude`/`confidence`/`cited_event_ids` both times.

**Checkpoint**: All three user stories independently functional and verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T015 [P] Run `ruff`/`mypy`/`lint-imports --config ../.importlinter` clean across all changed
      files — confirm the `readers-application-purity` and `global-dependency-rule` contracts
      still hold (the new adapter lives in `app.readers.adapters`, imports nothing from
      `app.readers.application` it isn't already allowed to).
- [x] T016 [P] Run `quickstart.md`'s full validation sequence end to end against a freshly
      recreated `pgvector/pgvector:pg16` container as final sign-off.
- [x] T017 Confirm `specs/ROADMAP.md` is intentionally left unmodified, matching the established
      precedent from `specs/025`/`specs/026`'s own tasks.md.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — the DDL/migration/image changes must land before anything
  else can run against a real database.
- **Foundational (Phase 2)**: Depends on Phase 1 only loosely (T006 doesn't need the DB at all,
  but is foundational because User Story 1 needs `MODEL_ID` to exist first).
- **User Story 1 (Phase 3)**: Depends on Phases 1–2. This is the MVP.
- **User Story 2 (Phase 4)**: Depends on Phase 3's `CachedEmbeddingAdapter` existing; adds no new
  implementation, only tests.
- **User Story 3 (Phase 5)**: Depends on Phase 3; adds no new implementation, only verification
  that nothing downstream changed.
- **Polish (Phase 6)**: Depends on Phases 3–5.

### Parallel Opportunities

- T004 (doc) and T003 (DDL) touch different files but T003 should land first since T004 describes
  what T003 defines — sequential, not parallel, despite both being early Setup-adjacent tasks.
- T010/T011/T012 (same new test file, independent test cases) can be drafted in parallel.
- T015/T016 (independent checks) can run in parallel.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 (Setup) → Phase 2 (Foundational).
2. Phase 3 (User Story 1) — the cache exists and is wired in.
3. **STOP and VALIDATE** via `quickstart.md` Story 1.

### Incremental Delivery

1. Setup + Foundational → Phase 3 (US1) → validate → already delivers the feature's core value.
2. Phase 4 (US2) → validate → model-swap safety locked in by a real test.
3. Phase 5 (US3) → validate → non-regression proof against the existing worked-example/golden-
   replay suite, unchanged.
4. Phase 6 (Polish) → final sign-off.

## Notes

- No `[Story]` label on T001–T006 (Setup/Foundational) or T015–T017 (Polish).
- User Story 3 has no implementation tasks by design — it's a verification-only story, proving the
  decorator pattern (Decision 2) actually kept `RecurrenceReader` untouched, not adding new
  behavior of its own.

## Verification log (how each task was actually confirmed, not just assumed)

- **T001/T002**: `docker-compose.yml` and `.github/workflows/ci.yml` both updated; confirmed by
  successfully running `alembic upgrade head` (including the new `0008_embedding_cache` revision)
  against a freshly pulled `pgvector/pgvector:pg16` container — `CREATE EXTENSION vector` succeeds,
  which it would not against a vanilla `postgres:16` image.
- **T003/T004/T005**: DDL, prose doc, and migration all added; `ruff`/`mypy` clean; migration
  applies cleanly on top of `0007_draft_finding_anchor` against a real container.
- **T006**: `OpenAIEmbeddingAdapter.MODEL_ID` is now public; `embed()`'s internal reference updated;
  confirmed by the existing Recurrence-reader-dependent tests still passing unchanged.
- **T007–T009**: `CachedEmbeddingAdapter` implemented and wired into both `worker.py` and
  `scripts/run_readers.py`; `ruff`/`mypy`/`lint-imports` all clean (4/4 import-linter contracts
  still kept — the new adapter lives in `app.readers.adapters`, same ring as
  `openai_embedding.py`).
- **T010–T012**: New `backend/tests/unit/test_cached_embedding_adapter.py` (4 tests, not 3 as
  originally scoped — an extra test for FR-007's "a failed miss caches nothing and a retry still
  works" was added during implementation, found worth covering once the adapter's actual shape was
  written), all passing against a real `pgvector/pgvector:pg16` container. Fixture vectors had to
  be corrected from illustrative 3-element lists to real 1536-dimension vectors partway through —
  Postgres's `vector(1536)` column genuinely rejects a shorter vector (`expected 1536 dimensions,
  not 3`), caught by actually running the test against a real column, not by inspection.
- **T013**: `tests/scoring/test_worked_example.py` and `tests/golden_replay/` both re-run,
  unmodified, against a database with `CachedEmbeddingAdapter` wired in — both still pass. Full
  suite: **185 passed, 1 skipped** (up from feature 026's 181 — 4 new tests, zero regressions),
  confirmed twice: once with `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` explicitly cleared (matching
  CI's real environment) and once with real keys configured.
- **T014**: Live-verified with **real** OpenAI API calls, not mocked — `scripts/run_readers.py` run
  three times in sequence against the same seeded corpus: run 1 (cold cache) persisted real
  findings and populated 15 `embedding_cache` rows; run 2 (warm cache) reproduced the same
  already-covered-events dedup `RunReadersUseCase` already guarantees (0 new findings, expected —
  proves nothing broke); run 3, specifically checked for real HTTP calls to
  `api.openai.com/v1/embeddings` in the process's own request log — **zero**, confirming SC-001 for
  real, not just via a unit test double.
- **T015/T016**: `ruff check .`, `uv run mypy app`, `lint-imports --config ../.importlinter` all
  clean; `quickstart.md`'s scenarios are covered by T013/T014's live runs above.
- **T017**: `specs/ROADMAP.md` intentionally left unmodified, matching `specs/025`/`specs/026`'s
  own precedent.
