# Research: Deterministic Findings

## Decision: `Reader.interpret(events, context) -> Finding[]` is the shared interface

**Decision**: Every reader in this feature implements `architecture/08-class-
diagrams.md`'s already-named `Reader` abstract interface — one method,
`interpret(events: list[Event], context: ClientProfileContext) -> list[Finding]`.
No template-method base class beyond the interface itself (unlike `Collector`,
which has a fixed fetch→normalize→persist sequence): each reader's internal shape
differs enough (Commitment reads projections, Recurrence calls an external API)
that forcing a shared template would fight the domain rather than express it.

**Rationale**: This interface is already published, not invented here — building
anything else would silently diverge from `architecture/08`'s own diagram. The
single-method shape also mechanically enforces REQ-M5-P1 (no reader sees another
reader's output — `interpret()` has no parameter that could carry one) and REQ-M5-
P2 (no side-effect capability beyond a return value).

**Alternatives considered**: A `Collector`-style template method (fixed
fetch/normalize/persist steps) — rejected because unlike collectors, which all
share one real shape (pull from a source, normalize, append), these five readers
genuinely differ in what "reading" means (a DB projection query vs. an external
embedding call), so a shared template would need so many override points it stops
being a template.

**`context` sourcing (added during `/speckit-analyze`)**: `RunReadersUseCase`
fetches `ClientProfileContext` once per run — reusing the same read pattern
feature 003's context module already exposes — and passes the same object into
every reader's `interpret()` call. No new port is needed for this: it's a single
upfront read per run, not a per-reader query, so it doesn't belong in the
per-reader port list below.

---

## Decision: rollup computation lives in `app.ingestion`, read by readers via a reader-owned port

**Decision**: `ComputeRollupsUseCase` (REQ-M2-06) is added to
`backend/app/ingestion/application/use_cases.py` — the module that already owns
`event_threads`/`response_pairs` (feature 003's `ReplayUseCase`) and whose schema
doc (`data-base/03-schema-ledger.md`) defines `rollups`. The Usage reader consumes
rollup data through a new port it defines itself — `RollupRepositoryPort` in
`app.readers.application.ports` — implemented by an adapter that queries the same
`rollups` table directly, not by importing `app.ingestion`'s port or adapter
classes.

**Rationale**: Constitution P8: "An entity that spans modules... is defined once,
in the module that owns its lifecycle, and imported by the others — never
redefined per module." `rollups` is M2's entity by REQ-M2-06's own assignment;
readers are a *consumer*, not a co-owner. Feature 004 already established the
concrete pattern for this exact cross-module situation — its own ports read
`client_profile_versions`/`response_pairs` (tables `app.context`/`app.ingestion`
also touch) via scoring-scoped ports, not cross-module adapter imports. Repeating
that convention here keeps every module's adapter layer importable only by its own
application layer, which is what `.importlinter`'s `global-dependency-rule`
contract (layers-per-container) is built to keep true forever, not just today.

**Alternatives considered**: Rollup computation and consumption both living inside
`app.readers` — rejected because it would make `app.readers` the de facto owner of
an M2 entity, contradicting REQ-M2-06's own module assignment and setting up a
future conflict if another M2-adjacent feature also needs rollups. Importing
`app.ingestion.application.ports` directly from `app.readers.application` —
rejected for the same reason feature 004 rejected it: it would couple two
modules' application layers together for a query-shape convenience, when a small,
reader-scoped port is cheap to define and keeps the modules independently
replaceable.

---

## Decision: `RunReadersUseCase` persists directly at `pending_validation`, without calling `ValidationGate`

**Decision**: `architecture/08`'s diagram wires `RunReadersUseCase --> ValidationGate:
every output passes through`. `ValidationGate` (M5a) doesn't exist until feature
007. This feature's `RunReadersUseCase` is therefore a deliberately partial
realization of that diagram: it runs all five readers, isolates each one's failure
(2026-08-14 clarification), and persists every returned `Finding` directly at
`status = pending_validation` — the same status `Reader.interpret()`'s return type
already implies (`architecture/08`: "`interpret()` returns `Finding[]` in
`pending_validation` status only"). No finding this feature produces is ever
`validated` or `quarantined`; that transition is entirely feature 007's to build.

**Rationale**: This mirrors feature 004's own precedent exactly — that feature's
`RecomputeScoreUseCase` reads `damping_weights` for real but never calls
`DampingCalculator`'s formula itself (that's feature 010's job), because the
formula-owning trigger doesn't exist yet. Building a placeholder/stub
`ValidationGate` just to wire the call would be speculative generality (P10) for a
gate whose real four checks (REQ-M5A-01) this feature has no reason to invent
early — and a stub that always passes or always fails would misrepresent what M5a
actually does, worse than the call simply not existing yet.

**Alternatives considered**: Building a minimal `ValidationGate` now (e.g. just the
"cited events exist" check) — rejected because a *partial* gate is worse than no
gate: a finding that "half-passed" validation is a more confusing state than one
that's honestly still `pending_validation` in full.

---

## Decision: rollup statistics computed in Python, not SQL

**Decision**: `ComputeRollupsUseCase`'s adapter fetches historical metric samples
for a subject/window as a plain list of floats; a pure domain function
(`UsageDeviationCalculator.z_score(historical_values, new_value) -> float`, no I/O)
computes mean, **sample standard deviation (n−1 denominator — the conventional
choice for a sample of historical readings, not the full population)**, and the
resulting z-score in Python.

**Revised during `/speckit-analyze`**: the real `warehouse` event schema
(`simulated_collector.py`'s `_normalize_warehouse`) carries only `value_delta_pct`
in its `structured_payload` — there is no separate absolute "value" field. A
rollup "historical value" is therefore each sample's own `value_delta_pct`
reading, not a raw metric value the current event schema doesn't have — a delta
series is still a valid numeric series to compute a mean/stddev/z-score over. This
also surfaced a real data gap: the fixture originally had exactly one warehouse
event, which can never clear FR-008's 3-sample abstention floor — five historical
readings (`usage-tracking_api-w29`..`w33`, `demo/fixtures/meridian-week.json`)
were added so the rollup has real history to compute against
(`data-model.md`'s worked `fnd-3` row has the resulting exact numbers).

**Rationale**: Matches every scoring domain service's own shape (feature 004:
`AgeingCalculator`, `BandClassifier`, etc. — all pure functions over plain values,
adapters only fetch raw rows) and the same reason constitution P8/P9 give for it:
a pure function is unit-testable with `assert` statements against literal
Python floats, no database, which is what makes a property-based test (thousands
of `hypothesis`-generated historical-value lists) practical at all. Doing the
arithmetic in a `STDDEV()`/`AVG()` SQL aggregate would work for the *production*
path but would make the same property-based verification require a live database
per generated case — far slower, and inconsistent with how every other numeric
formula in this codebase has been tested so far.

**Alternatives considered**: Postgres `STDDEV_SAMP()`/`AVG()` aggregates computed
in the adapter's own query — rejected for the testability reason above, not a
performance concern (the data volumes here are small).

---

## Decision: Recurrence embeds ticket/message titles, HDBSCAN with `min_cluster_size=2`

**Decision**: `RecurrenceReader` embeds each candidate ticket/message's title/
subject text (not the full body — titles are shorter, already the field
`SimulatedCollector` normalizes as `payload_text` for `ticket_state_change`
events, and are what a human would use to judge "is this the same problem") via
`EmbeddingPort.embed(text) -> float[]`, then clusters the resulting vectors with
HDBSCAN (`min_cluster_size=2` — the smallest meaningful "this recurred" signal is
two related occurrences; `min_samples` left at HDBSCAN's own default). Any cluster
with 2+ members produces one `recurring_issue` finding per member beyond the
first, citing every event in that cluster.

**Rationale**: `min_cluster_size=2` is the natural floor for "recurrence" — a
single ticket can never recur against itself. Titles rather than full bodies keep
the embedded text focused on *what the problem is* rather than incidental
conversational detail, matching `examples/01` §6's own framing ("is this the same
problem coming back?" — a question about problem identity, not phrasing).

**Alternatives considered**: Embedding full ticket bodies — rejected as noisier
input for a same-problem-identity judgment, and unnecessary given ticket titles
already carry the signal `examples/01`'s own worked example relies on ("Slow API
response" recurring). A configurable `min_cluster_size` — deferred (P10); 2 is the
only value that makes sense given the finding this reader exists to produce.

**`min_samples=1` (added during implementation)**: HDBSCAN's default `min_samples`
(= `min_cluster_size`) estimates local density from nearest-neighbor distances,
which empirically misclassifies even exact-duplicate points as noise at this
feature's small candidate-corpus sizes (verified directly: 2-3 points, including
identical vectors, all labeled noise at default settings; `min_samples=1` — a
single close neighbor is sufficient density evidence — correctly separates a
genuine duplicate pair from unrelated singletons once the corpus reaches a
handful of items). This is a real HDBSCAN small-sample limitation, not a design
error — `min_samples=1` is the documented, conservative fix, and the algorithm's
own `probabilities_` (used as this reader's `confidence`) already discounts
weaker matches rather than treating every cluster membership as equally certain.

**Candidate corpus is filtered to `created`/`reopened` states only (added during
implementation)**: including every `ticket_state_change` event as a candidate
would make a single ticket's own `created` and `resolved` events (identical
title) falsely cluster as a "recurrence" — ticket #398 in the real fixture has
both and was never reopened. Only `created`/`reopened` states represent a new
occurrence of a reported problem worth comparing; `resolved` closes one, it
doesn't report a new one.

**A max-pairwise-distance safety net on top of HDBSCAN's raw output (added
during implementation)**: `min_samples=1` (above) also makes HDBSCAN over-eager
at small sample sizes — verified to sometimes lump several genuinely unrelated
singletons into one shared cluster rather than marking them noise, purely
because there's too little data for its density estimate to separate them
cleanly. A cluster is only trusted if its members' maximum pairwise Euclidean
distance is ≤ `1.0` — a conservative floor for normalized embedding vectors,
favoring a missed recurrence over a fabricated one. The real fixture also gained
one more, clearly unrelated ticket (`zendesk-512-created`, "Login page displays
wrong company logo") so Recurrence's real candidate corpus has 4 items instead
of 3 — empirically, HDBSCAN's small-sample behavior is sensitive to exact corpus
size and geometry, and a slightly larger, more realistic corpus reduces the risk
of landing exactly on a degenerate edge case.

---

## Decision: Commitment reader's magnitude/confidence formulas

**Decision**: `confidence = 1.0` always — the Commitment reader's judgment is
exact arithmetic (elapsed business hours vs. a defined threshold), the same "zero
uncertainty" reasoning `data-base/05-schema-reasoning.md`'s own notes give for
`fnd-1`. `magnitude` for `broken_response_promise` = `min(overdue_ratio, 1.0)`
where `overdue_ratio = (elapsed − threshold) / threshold` (reusing REQ-M6-CAL-01's
exact formula shape from feature 004 — the same ratio scoring's `AgeingCalculator`
already computes, now also driving how *large* this reader considers the
violation, not just how the finding later ages). `magnitude` for `commitment_met`
= `1.0 − (elapsed / threshold)` (how much headroom was left before the promise
would have broken; a response at 0% of the threshold time scores 1.0, a response
at exactly the threshold scores 0.0 — which is also exactly the boundary FR-005
already uses to decide whether to emit `commitment_met` at all).

**Rationale**: Both formulas reuse arithmetic this codebase already trusts
(feature 004's own overdue-ratio shape) rather than inventing a new one, and both
are bounded to `[0, 1]` by construction, satisfying REQ-M5-03 without a separate
clamp. `spec.md`'s SC-001 deliberately doesn't require reproducing
`examples/01`'s exact hand-picked magnitude/confidence numbers (only
`finding_type`/`cited_event_ids`) — those illustrative numbers were chosen for the
narrative, not derived from a formula this feature is obligated to reverse-
engineer.

**Alternatives considered**: A fixed `magnitude = 1.0` for every
`broken_response_promise` (binary: broken or not) — rejected because it would
make every violation look equally severe regardless of how overdue it actually is,
losing information `AgeingCalculator` itself already treats as meaningful.

---

## Decision: Absence reader's magnitude/confidence formulas

**Decision (revised during implementation — the real payload doesn't match this
Decision's original assumption)**: `confidence = 0.85` fixed — the absence event
itself is a hard, already-recorded fact (feature 003's `DetectAbsenceUseCase`),
not a statistical inference, so a high fixed confidence is appropriate (and
happens to match `examples/01` §6's own `fnd-4` value). `magnitude`: `1.0` if the
event's `structured_payload.last_contact_at` is `null` (no prior contact ever);
otherwise `min(silence_days / (2 × cadence_days), 1.0)`, where `silence_days =
(occurred_at − last_contact_at).days` and `cadence_days = (occurred_at −
window_start).days` — both derivable entirely from the real event's own
`structured_payload` (`window_start`, `last_contact_at`) and its `occurred_at`,
no re-parsing of the commitment's `cadence` string needed.

**Correction record**: this Decision originally assumed the absence event's
payload carried a `missed_count` field, based on `examples/01` §5.1's
illustrative walkthrough payload (`{expected: weekly_sync, missed_count: 2,
silent_days: 12}`). The real `DetectAbsenceUseCase`
(`backend/app/ingestion/application/use_cases.py`) does not produce that field —
its actual payload is `{commitment_id, cadence, window_start, last_contact_at}`.
Caught while implementing `T020`/T019, not during planning — the formula above
uses only fields the real event actually carries.

**Rationale**: `window_start`/`last_contact_at` are exactly the facts
`DetectAbsenceUseCase` already computed to decide an absence event was warranted
in the first place — reusing them avoids inventing a second severity signal
alongside data the ledger event already records. `cadence_days`'s reconstruction
(`occurred_at − window_start`) is exact, not an approximation, since that's
literally how `DetectAbsenceUseCase` derived `window_start` in the first place.
The `× 2` scaling is a new, documented default (this feature's status, same as
every other new constant introduced this session) — twice the expected cadence
without contact is a reasonable "this is clearly no longer incidental" floor.

**Alternatives considered**: Re-parsing `cadence` via `_parse_cadence_days`
inside the reader — rejected as redundant: `window_start` already encodes the
same information as a concrete date difference, without needing the reader to
duplicate `DetectAbsenceUseCase`'s own cadence-string parsing logic.

---

## Decision: Relationship reader's window, evidence, and magnitude/confidence formulas

**Decision**: For each stakeholder in the client profile, the reader checks
whether that stakeholder authored/participated in at least one ledger event within
the rolling 4-week window (2026-08-14 clarification). A stakeholder present in an
*earlier* 4-week window but absent from the current one emits a
`relationship_change` finding, citing the most recent event in which they *did*
participate (the evidence that establishes when their activity stopped) plus, if
one exists, the same real `absence`-type event feature 003 produces for that
stakeholder (co-citation is expected, not deduplicated — REQ-M5-P1, `spec.md`'s
Edge Cases). `magnitude = 0.5` fixed, `confidence = 0.7` fixed — this feature's
reduced-strength signal (email/ticket cadence only, no Slack participant graph)
genuinely can't distinguish "quietly stepping back" from "just had a quiet
month" as precisely as a full-strength Phase 2 reader could, so a moderate,
honest fixed pair is more accurate than a false-precision formula.

**Rationale**: Fixed values here (rather than an invented formula, unlike
Commitment/Absence above) are the more honest choice specifically *because* this
reader runs at reduced strength — manufacturing a formula-derived confidence would
overstate a certainty this feature's data genuinely doesn't support.

**Alternatives considered**: Deriving magnitude from message-frequency delta
(e.g. messages in the current window vs. the prior window) — deferred; a real
frequency-based signal is more naturally something Phase 2's fuller data (Slack
participation) can support well, and building a shakier version now risks a
formula this feature would need to redo anyway.

---

## Decision: Recurrence reader's magnitude/confidence formulas

**Decision**: `confidence` = HDBSCAN's own per-point cluster membership
probability (`probabilities_`, a value HDBSCAN already computes — how strongly
this specific occurrence belongs to its assigned cluster, natively bounded to
`[0, 1]`). `magnitude = min((cluster_size − 1) / 3.0, 1.0)` — the same
"divide-by-3, clamp to 1.0" shape as the Absence reader's `missed_count` scaling
above, applied to "how many total occurrences does this recurrence have," since a
2-occurrence recurrence is a milder signal than a 4th reopening of the same
problem.

**Rationale**: Using HDBSCAN's own membership probability for confidence means
this reader's stated certainty is a real, already-computed property of the
clustering result, not a second invented number layered on top of it — the same
"don't fabricate a signal the algorithm didn't actually produce" reasoning
`architecture/08`'s notes give for why `EmbeddingPort.embed()` returns a vector,
never text. The magnitude formula's shape intentionally matches Absence's, for
the same reason feature 004 reused `overdue_ratio`'s shape twice in Commitment's
own formulas above: consistent, already-reviewed arithmetic patterns are easier to
verify correct a second time than a novel one.

**Alternatives considered**: A fixed confidence (mirroring Relationship's honest-
fixed-value reasoning) — rejected here specifically because, unlike Relationship's
genuinely reduced-strength signal, HDBSCAN already computes a real per-point
confidence value; discarding it in favor of a fixed number would throw away
information the clustering step legitimately produced.

---

## Decision: `demo/fixtures/meridian-week.json` gains one new event — ticket #456's original creation

**Decision**: Add a `zendesk-456-created` item to `demo/fixtures/meridian-week.json`
(`state = created`, same `ticket_number = 456`, same title "Slow API response",
`occurred_at` earlier in the fixture's week than the existing `zendesk-456-
reopened` item) — a real, ingestible ledger event, not a synthetic shortcut. This
feature's `fnd-2` (`recurring_issue`) then genuinely cites *two* real events (the
original creation and the reopening), reflecting what real embedding+clustering
actually needs to find a cluster of size ≥ 2.

**Rationale**: `examples/01-end-to-end-walkthrough.md` §6's own `fnd-2` cites only
`[evt-2]` (the reopened event alone) — a narrative shorthand that reads the
event's own `reopen_count: 2` payload field rather than demonstrating real
cross-event clustering. But REQ-M5-09 requires the *mechanism* to be embedding
similarity + clustering, and a single ticket can never cluster with itself
(`min_cluster_size = 2`, the Decision above). Checked directly: the current
fixture has exactly one Zendesk item for ticket #456 (confirmed by inspecting
`demo/fixtures/meridian-week.json`) — ticket #398 already has a `created` +
`resolved` pair, but #456 never got a `created` counterpart, since no earlier
feature (001–004) needed one. This is a genuine, pre-existing fixture gap that
only becomes visible now that a real Recurrence reader needs to cluster against
something. Adding the missing event is more honest than special-casing the
reader to treat `reopen_count` as a clustering shortcut, which would silently
violate REQ-M5-09's "no path to a decision that skips the deterministic
clustering step" intent (`architecture/08`'s own framing for why `EmbeddingPort`
returns a vector, never text).

**Consequence for `spec.md`'s SC-001**: this feature's real `fnd-2` cites *both*
events (`[zendesk-456-created, zendesk-456-reopened]`), not `examples/01`'s
published single-event citation — the same kind of correction feature 004 already
made once for `examples/01` §9.2's Issue A rank order: the real, general
implementation is this feature's actual acceptance criteria, superseding a
narrative shortcut in the published walkthrough for this specific fixture.
`examples/01` itself is unaffected — correcting it is a separate, later concern.

**Alternatives considered**: Special-casing the Recurrence reader to also accept
`reopen_count > 1` as a same-ticket recurrence signal, bypassing clustering for
that case — rejected as exactly the kind of "skip the deterministic step"
shortcut REQ-M5-09 exists to prevent, and as two different mechanisms
(clustering *and* a metadata shortcut) for the same finding type, contradicting
Single Responsibility (constitution P8).

---

## Decision: the REQ-M5-15 cache is a direct query against `findings`, not a new table

**Decision**: Before interpreting an event, each reader (via `RunReadersUseCase`
or the reader's own application logic) checks `SELECT 1 FROM findings WHERE
reader_type = :reader_type AND reader_version = :reader_version AND
:event_id = ANY(cited_event_ids) LIMIT 1` — no dedicated cache table.

**Rationale**: `findings` already carries every field the cache key needs
(`reader_type`, `reader_version`, `cited_event_ids`); a separate cache table would
just duplicate that same information and need its own invalidation story. This
matches feature 004's `resolve_lifecycle` precedent — reading an existing table's
already-present columns rather than introducing new bookkeeping state
specifically to avoid re-deriving something a plain query can answer directly.
(SQL note: the `:event_id = ANY(cited_event_ids)` bind-and-cast form needs the
same `(:param)::type` parenthesization feature 004 already found necessary for
SQLAlchemy's asyncpg dialect — flagged here so implementation doesn't re-discover
that bug.)

**Alternatives considered**: A dedicated `reader_interpretation_cache` table
keyed by `(event_id, reader_type, reader_version)` — rejected as speculative
generality (P10): `findings` already *is* that cache, since a cached "no finding
was produced" state doesn't need representing (an abstaining reader simply has no
row to find — REQ-M5-04 already makes "produced nothing" a valid terminal state,
not a distinct one that needs its own cache entry).

---

## Note: the full cross-module golden-replay test stays skipped, one module closer

`tests/golden_replay/test_placeholder.py` still can't pass for real after this
feature — it needs the Narrator (feature 008) too. This feature does close the gap
by one more module (ledger → readers → score are now all real); `plan.md`'s
Complexity Tracking records the same justification feature 004 already gave,
extended.

## Outcome

All Phase 0 decisions above resolve every open design question from `spec.md`'s
Assumptions and the 2026-08-14 clarification session. No `NEEDS CLARIFICATION`
markers remain. Proceeding to Phase 1 (data-model.md, quickstart.md).
