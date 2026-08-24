# Feature Specification: Embedding Cache (pgvector)

**Feature Branch**: `027-pgvector-embedding-store`

**Created**: 2026-08-24

**Status**: Draft

**Input**: User description: "Add pgvector as a Postgres extension and persist/cache embeddings for the Recurrence reader — currently every run re-embeds the full candidate corpus from scratch via OpenAI, with nothing ever cached. Scope deliberately narrow: pgvector as a caching layer, not a redesign of clustering — RecurrenceReader keeps re-clustering the full corpus every run, unchanged. Third feature in the 7-feature production-readiness roadmap; matters more now that feature 026 made the Recurrence reader run automatically every ~30s (when new signals exist) instead of only via a manually-triggered script."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Previously-seen content is never re-embedded (Priority: P1)

When the Recurrence reader runs and encounters a ticket/message title it has already embedded on
a prior run, it reuses that stored embedding instead of calling the embeddings provider again for
the exact same text. Only genuinely new or changed content triggers a new embedding call.

**Why this priority**: This is the entire point of the feature. `RecurrenceReader` currently
re-embeds its *entire* candidate corpus on every single run — a cost that was tolerable when the
reader only ran via a manually-triggered script, but now runs automatically roughly every 30
seconds whenever new signals exist (the prior feature in this roadmap). Without this story, that
automation multiplies a real, recurring external-API cost for content that never changes between
runs.

**Independent Test**: Run the Recurrence reader twice in a row with no new candidate content
between runs, and confirm (via call count/log inspection) that the second run makes zero calls to
the embeddings provider for titles already embedded in the first run.

**Acceptance Scenarios**:

1. **Given** a candidate title was embedded on a prior run, **When** the Recurrence reader runs
   again and encounters that exact same title, **Then** it reuses the stored embedding and makes
   no new call to the embeddings provider for it.
2. **Given** a candidate title has never been embedded before, **When** the Recurrence reader
   encounters it, **Then** it calls the embeddings provider once, and the result becomes available
   for reuse on every subsequent run.
3. **Given** a mix of previously-seen and brand-new candidate titles in the same run, **When** the
   Recurrence reader processes the corpus, **Then** only the brand-new titles trigger a provider
   call — the previously-seen ones are all served from the cache.

---

### User Story 2 - A future embedding model change can never silently return a stale vector (Priority: P2)

If the embeddings provider or model is ever changed, the cache does not return an embedding that
was computed by the old model under the new model's name — a cached vector is only ever reused
when it was produced by the exact same model currently configured.

**Why this priority**: `architecture/03-technology-stack.md` already documents a fine-tuned quality
upgrade to a different embedding model as "a config change, not an architecture change" if
clustering quality ever needs it. Without this story, that documented future config change would
silently mix embeddings from two different models in the same clustering pass, corrupting
similarity comparisons in a way that would be very hard to diagnose. It's second priority because
it protects a scenario that hasn't happened yet, but must be correct from day one of the cache
existing — retrofitting it after a model swap would be too late.

**Independent Test**: Populate the cache under one model identifier, then run the Recurrence reader
configured with a different model identifier for the same content, and confirm a new embedding is
computed rather than the old model's cached one being reused.

**Acceptance Scenarios**:

1. **Given** a title's embedding is cached under model A, **When** the reader is later configured
   to use model B for the same title, **Then** a new embedding is computed under model B, not
   served from model A's cached entry.
2. **Given** both a model-A and a model-B cached entry exist for the same title, **When** the
   reader runs configured for model A, **Then** it reuses model A's entry specifically.

---

### User Story 3 - Clustering results are unaffected by caching (Priority: P3)

Introducing the cache changes nothing about which findings the Recurrence reader produces — the
same candidate corpus yields the exact same clusters, membership, and findings whether an
embedding came from the cache or a fresh provider call.

**Why this priority**: This is a correctness guarantee, not new user-facing value — it exists to
make sure Stories 1 and 2's optimization is genuinely invisible to everything downstream
(clustering, findings, the score, the dashboard, and this system's replay/determinism guarantees).
It is lower priority only because it is a non-regression check on the other two stories' behavior,
not a capability on its own.

**Independent Test**: Run the Recurrence reader once with an empty cache, record its findings;
clear all findings/state but keep the now-populated cache, run it again on the same corpus, and
confirm byte-identical findings both times.

**Acceptance Scenarios**:

1. **Given** the same candidate corpus, **When** the Recurrence reader runs once with a cold cache
   and once with a warm cache, **Then** both runs produce identical clusters and findings.
2. **Given** the system's existing full-replay determinism guarantee (same ledger + same versions
   → identical score, always), **When** a full replay is performed after the cache has been
   populated, **Then** the reconstructed dashboard state is still byte-identical to the original.

---

### Edge Cases

- What happens when the embeddings provider is unreachable or misconfigured for a genuinely new
  (uncached) title? The reader must fail exactly as honestly as it does today for that one title —
  the cache only removes *redundant* calls, it never changes what happens on an actual cache miss.
- What happens to content that is byte-identical but reformatted (e.g. whitespace differences)? It
  is treated as different content and embedded separately — this feature does not attempt any
  content normalization beyond exact-match reuse.
- What happens the very first time the system runs, with an empty cache? Every title is a cache
  miss — behavior is identical to today's always-re-embed behavior for that one run, and every run
  after it benefits from what was just cached.
- What happens if two different clients' deployments ever shared infrastructure? They don't and
  never will (the product's permanent one-deployment-per-client isolation model) — this feature's
  cache lives inside that same single-deployment database, never shared across clients.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST persist a computed embedding so it can be reused across separate
  runs of the Recurrence reader, not only within a single run.
- **FR-002**: Before calling the embeddings provider for a piece of candidate content, the system
  MUST first check whether an embedding for that exact content, under the currently configured
  model, already exists.
- **FR-003**: On a cache hit, the system MUST reuse the stored embedding and MUST NOT call the
  embeddings provider for that content.
- **FR-004**: On a cache miss, the system MUST call the embeddings provider exactly as it does
  today, and MUST store the resulting embedding for future reuse before the run completes.
- **FR-005**: A stored embedding MUST be tied to the specific model that produced it, such that a
  future run configured with a different model never reuses another model's cached vector for the
  same content (User Story 2).
- **FR-006**: The Recurrence reader's clustering behavior (which candidates group together, what
  findings result) MUST be unaffected by whether a given embedding came from the cache or a fresh
  provider call (User Story 3) — this feature changes how an embedding is *obtained*, never how
  clustering *interprets* it.
- **FR-007**: A cache miss for content whose embedding cannot be obtained (provider unreachable,
  missing credential) MUST fail exactly as honestly and visibly as it does today for that same
  content — no different, and no more silent.
- **FR-008**: The cache MUST NOT change or bypass any existing determinism/replay guarantee — a
  full replay after the cache is populated must still reconstruct byte-identical dashboard state.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After a candidate title has been embedded once, every subsequent Recurrence reader
  run that encounters the exact same title makes zero additional calls to the embeddings provider
  for it.
- **SC-002**: A candidate corpus with 90% previously-seen titles and 10% brand-new ones results in
  embedding-provider calls for only the 10% new titles, not the full corpus.
- **SC-003**: Findings produced by the Recurrence reader are identical, run-for-run, on an
  unchanged corpus, regardless of whether the cache was cold or warm for that run.
- **SC-004**: A deployment that later reconfigures its embedding model produces zero incorrectly-
  reused cache hits from the prior model — every title is freshly embedded under the new model at
  least once before any cache reuse occurs for it.

## Assumptions

- This feature only changes how the Recurrence reader *obtains* an embedding vector; nothing about
  which readers exist, what they read, or how findings are validated/scored changes.
- The scope is a cache, not a search/similarity index — no new query capability (e.g. semantic
  search over historical tickets) is being added anywhere in the product by this feature. A future
  feature could build on this same persisted-vector foundation for that, but that is explicitly out
  of scope here (P10 — build for today's requirement, not a speculative future one).
- "Exact same content" means byte-identical input text to the embeddings call — no normalization,
  fuzzy matching, or semantic deduplication of near-identical titles is part of this feature.
- Per the approved production-readiness roadmap, this is implemented as a Postgres extension
  (pgvector) within the deployment's existing single database — not a separate vector database
  service, consistent with the product's one-deployment-per-client, no-shared-infrastructure model.
