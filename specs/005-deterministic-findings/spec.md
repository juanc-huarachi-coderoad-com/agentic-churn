# Feature Specification: Deterministic Findings

**Feature Branch**: `005-deterministic-findings`

**Created**: 2026-08-14

**Status**: Draft

**Input**: User description: "Deterministic findings — build-order Phase 5
(`base/Churn-Sentiment-Agent-Product-Specification.md` §16): 'Deterministic
interpreters (commitment, usage, recurrence, absence)... Real findings, no model
risk.' This feature builds the five non-LLM M5 readers for real, turning ledger
facts (events, response_pairs, the real absence events feature 003 already
produces) into structured `findings` rows — the first real (non-fixture) findings
this system has ever produced. The three LLM readers (Tone, Intent, Meeting) and the
M5a validation gate are feature 007's scope, not this one."

## Clarifications

### Session 2026-08-14

- Q: When `RunReadersUseCase` runs all five readers and one fails (e.g., Recurrence's
  `OPENAI_API_KEY` is missing), do the other four still run and persist their
  findings? → A: Per-reader isolation — each reader's failure is caught and reported
  independently; the other four still run and persist findings normally, matching
  the constitution's existing per-source isolation principle for M1 collectors and
  feature 003's `RunCollectorUseCase.fail_sources` precedent.
- Q: Usage's variance check and Relationship's participant diff both reference a
  "rolling window"/"historical distribution" without a concrete duration. What
  lookback window should this feature use? → A: Different windows per reader,
  configurable — Usage uses 8 weeks (matching `examples/01` §5.3's own worked
  number, "usage down 22% vs 8-week average"), Relationship uses 4 weeks (a new
  default, shorter, since a stakeholder disengaging is worth noticing sooner than a
  slow usage drift). Each is a named, product-maintained constant in this feature's
  own code — the same "small, explicit default" pattern `finding_type_config`
  already established — not a new `client-profile.yaml` field (constitution P10;
  promoting either to per-client profile configuration is a future feature's
  concern if a real need for it appears).
- Q: `requirements/05-interpreters-readers.md`'s own non-functional constraint says
  "only affected windows are re-read on new events — not a full re-read of history
  per event." Does this apply to the Recurrence reader's embedding+clustering step
  in this feature? → A: No — this feature re-embeds and re-clusters the full
  candidate corpus (every ticket/message the reader can see) on every run. Simpler
  and still fully correct/deterministic at this feature's fixture-sized data volume;
  real incremental clustering (deciding whether a new item joins an existing cluster
  vs. forms a new one) is deferred until real data volume demands it (constitution
  P10, YAGNI) — REQ-M5-15's per-event cache still prevents re-emitting a duplicate
  finding for an already-interpreted event even though clustering itself re-runs.
- Q: REQ-M5-08 says Usage must flag deviation using "a statistically defined
  variance threshold," not a fixed percentage, but doesn't pin the exact method.
  Which statistical method should this feature use? → A: Standard deviation
  (z-score) — flag a new value when it falls more than 2 standard deviations from
  the rolling window's mean (`|z| > 2`), simple to compute and test
  deterministically from a small rolling-window sample. (User Story 2's own
  Independent Test wording was corrected to say "2 standard deviations" during
  `/speckit-analyze` — it originally said "one," a terminology drift against this
  answer.)

## Note on scope for this feature

Requirement content is **not** restated here — every functional requirement cites
the `REQ-<ID>` that is its source of truth. Five readers are in scope: Commitment,
Usage, Recurrence, Absence, Relationship — every non-LLM reader in
`requirements/05-interpreters-readers.md`'s eight-reader table.

**Relationship's phase assignment, resolved for this feature**: the product spec's
build-order table (§16) lists Phase 5's deliverable as "commitment, usage,
recurrence, absence" — Relationship isn't named there, even though it's deterministic
(a graph diff, no LLM) and paired with Absence everywhere else in the document as a
reduced-strength MVP reader. Rather than leave it with no owning feature, or bundle a
non-LLM reader in with feature 007's LLM readers, this feature includes it alongside
its fellow non-LLM readers (`specs/ROADMAP.md` records this decision).

Six deliberate scope boundaries, each because a downstream producer doesn't exist
yet or a capability is explicitly deferred:

- **Findings land `pending_validation`, never `validated`.** M5a (the validation
  gate that would promote or quarantine a finding) doesn't exist until feature 007.
  Feature 004's `RecomputeScoreUseCase.list_validated()` correctly ignores every
  finding this feature produces until then — proving a reader worked means querying
  `findings` directly, not observing a score change.
- **Tone, Intent, Meeting, and M5a are explicitly out of scope**, even though they
  share `requirements/05-interpreters-readers.md` with the five readers this feature
  builds. REQ-M5-04/06/12/13/14 and REQ-M5A-01..04 belong to feature 007.
- **Rollup/baseline computation (REQ-M2-06) is built here, scoped narrowly.** The
  `rollups` table exists since feature 001 but is deliberately unpopulated
  (`specs/003-ingestion-and-context/spec.md`'s own documented boundary: "no reader
  exists yet to consume a baseline (Usage is Phase 5, Tone is Phase 7)... this
  feature doesn't populate it"). This feature is Usage's first real consumer and
  builds exactly the aggregation Usage's variance check needs — not a general
  analytics engine. `rollups.is_baseline`/`baseline_confirmations` (the human-
  confirmation-survives-replay mechanism, `data-base/03-schema-ledger.md`) stays out
  of scope: no reader here needs a *confirmed* baseline, only a computed one.
- **Absence and Relationship run at reduced strength in this feature**, honestly —
  `examples/01-end-to-end-walkthrough.md` §6 marks both as needing a Phase 2 source
  (Slack participant/silence data) for full strength; this feature gives both
  everything email/ticket-cadence data can offer, and no more, rather than quietly
  assuming full strength.
- **No new HTTP route, no dashboard changes.** Findings become visible via direct
  DB query or a verification script — the same "prove it via script + tests" pattern
  feature 004 established. Feature 006 (dashboard evidence trace) is the first
  feature to surface findings on a screen.
- **Reader triggering is manual only.** `RunReadersUseCase` (the named pattern,
  `architecture/09-clean-architecture-and-patterns.md`) runs via a script mirroring
  `scripts/run_collector.py`/`compute_score.py`'s pattern — event-driven/real-time
  triggering needs a live pipeline this feature doesn't build (matching feature
  004's own "only wire a trigger with a real caller" discipline).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A broken promise and a kept one both leave a receipt (Priority: P1)

A late response to ticket #456 becomes a real, evidenced `broken_response_promise`
finding; a fast response to ticket #398 becomes a real `commitment_met` finding —
both derived from data feature 003 already computes (`response_pairs`), with zero
new external dependencies.

**Why this priority**: The simplest of the five readers — it reads already-computed
`response_pairs` rows (feature 003's `ReplayUseCase`) and applies a single, already-
calibrated threshold comparison (REQ-M6-CAL-01, reused verbatim from feature 004's
own ageing calculation). No new infrastructure, no external API, the lowest-risk
foundation to build and verify first.

**Independent Test**: Run the Commitment reader against the real, already-ingested
Meridian fixture (tickets #456 and #398, both already in the ledger from feature
003/004's work) and confirm it produces exactly `examples/01` §6's `fnd-1`
(`broken_response_promise`, citing ticket #456's reopened event) and `fnd-9`
(`commitment_met`, citing ticket #398's resolved event).

**Acceptance Scenarios**:

1. **Given** a `response_pairs` row in `open_overdue` state, **When** the Commitment
   reader runs, **Then** it emits a `broken_response_promise` finding citing the
   pair's `client_event_id`, with `reader_type = commitment` (REQ-M5-07).
2. **Given** a `response_pairs` row in `resolved` state where `business_hours_
   elapsed` is comfortably under the commitment's threshold, **When** the Commitment
   reader runs, **Then** it emits a `commitment_met` finding citing the same event
   (REQ-M5-07; the positive-signal counterpart to `broken_response_promise`, matching
   `data-base/05-schema-reasoning.md`'s seeded `finding_type_config` row for it).
3. **Given** a `response_pairs` row in `resolved` state where `business_hours_
   elapsed` exceeded the threshold before it was eventually resolved, **When** the
   Commitment reader runs, **Then** it emits `broken_response_promise` — the promise
   was broken regardless of whether the ticket has since closed (Appendix A design
   commitment #9: unresolved problems never fade, and a late-then-resolved response
   is a fact about what happened, not erased by the eventual resolution).
4. **Given** a `response_pairs` row already interpreted by the same `reader_version`,
   **When** the Commitment reader runs again over the same event, **Then** no
   duplicate finding is produced (REQ-M5-15).
5. **Given** a finding this reader emits, **When** inspected, **Then** its
   `magnitude`/`confidence` are set deterministically from the elapsed-vs-threshold
   arithmetic — never a fixed constant — and `cited_event_ids` is non-empty
   (REQ-M5-02/03/05).

---

### User Story 2 - Activity that's actually unusual gets flagged, not activity that's merely different (Priority: P1)

A real drop in `tracking_api` usage — genuinely far outside its own historical
range — becomes a `usage_deviation` finding. A metric bouncing around inside its
normal week-to-week variance produces nothing.

**Why this priority**: This is the first real implementation of `rollups` (REQ-M2-06)
— deferred since feature 003 specifically because no consumer existed yet. Getting
the baseline computation right here is foundational: it's the shape every future
statistics-based reader (and this feature's own Usage reader) depends on.

**Independent Test**: Run the Usage reader against the real warehouse usage events
already in the ledger and confirm it reproduces `examples/01` §6's `fnd-3`
(`usage_deviation`, `tracking_api` usage down 22% against its own 8-week average) —
and confirm a synthetic metric held within 2 standard deviations of its own history
produces no finding.

**Acceptance Scenarios**:

1. **Given** a metric's historical values for a subject (stakeholder, product area,
   or account), **When** the rollup computation runs, **Then** it derives that
   metric's own statistical distribution (not a fixed percentage threshold)
   (REQ-M2-06, REQ-M5-08).
2. **Given** a new metric value that falls outside its own statistically defined
   variance threshold, **When** the Usage reader runs, **Then** it emits a
   `usage_deviation` finding citing the triggering event, with `magnitude` reflecting
   how far outside normal the value fell (REQ-M5-08, REQ-M5-03).
3. **Given** a new metric value within its own normal variance, **When** the Usage
   reader runs, **Then** it emits no finding (REQ-M5-04's "no history, no opinion"
   principle applied by extension: no *unusual* opinion, either, when nothing unusual
   happened).
4. **Given** a subject with fewer historical samples than a defined minimum, **When**
   the Usage reader runs, **Then** it abstains rather than computing a distribution
   from too little data (REQ-M5-04).

---

### User Story 3 - Missing contact is judged against a real commitment, never a guessed silence window (Priority: P2)

Diego's 12 days of silence against a weekly-sync commitment becomes a real
`contact_absence` finding — because a *defined expectation* was missed, not because
12 days felt like a long time.

**Why this priority**: Builds directly on feature 003's already-real
`DetectAbsenceUseCase` output (a real `absence`-type ledger event) — this reader
only has to interpret an existing fact, not detect the absence itself.

**Independent Test**: Run the Absence reader against the real `absence`-type event
already in the ledger (produced during feature 004's own verification) and confirm
it reproduces `examples/01` §6's `fnd-4` (`contact_absence`, citing that event).

**Acceptance Scenarios**:

1. **Given** a real `absence`-type ledger event (a defined expectation — a
   commitment, a recurring meeting cadence — that went unmet), **When** the Absence
   reader runs, **Then** it emits a `contact_absence` finding citing that event
   (REQ-M5-10).
2. **Given** no `absence`-type event exists for a subject, **When** the Absence
   reader runs, **Then** it emits nothing — it never infers a silence duration on its
   own; that judgment already happened at ledger-append time (REQ-M5-10, "never
   against an arbitrary silence duration").

---

### User Story 4 - A quietly shrinking cast of stakeholders becomes visible (Priority: P2)

When someone who used to be part of the conversation — Diego — effectively stops
participating, that shift becomes a real `relationship_change` finding, diffed
against the client profile's own stakeholder list.

**Why this priority**: Deterministic and self-contained (no new external
dependency), but lower-value alone than Commitment/Usage until Relationship's
Phase-2 strength (Slack participant data) lands — still real and correct at reduced
strength today.

**Independent Test**: Run the Relationship reader against the real ledger and
profile data and confirm it reproduces `examples/01` §6's `fnd-5`
(`relationship_change`, Diego's participation drop).

**Acceptance Scenarios**:

1. **Given** the client profile's stakeholder list and a rolling 4-week window of
   ledger participants, **When** the Relationship reader runs, **Then** it diffs the
   active set against the profile's list and flags additions/disappearances
   (REQ-M5-11).
2. **Given** a stakeholder present in the profile but absent from the rolling
   window's participant activity, **When** the Relationship reader runs, **Then** it
   emits a `relationship_change` finding citing the stakeholder's most recent
   active event (REQ-M5-11, REQ-M5-05) — `commitments` carries no `stakeholder_id`
   column, so a real `absence`-type event can never be attributed to a specific
   stakeholder; this finding's citation is that one event, not a co-citation
   (corrected during implementation from an earlier assumption).
3. **Given** a rolling window where every profiled stakeholder remains active,
   **When** the Relationship reader runs, **Then** it emits nothing.

---

### User Story 5 - The same recurring problem is recognized as one story, not several (Priority: P2)

Ticket #456's second reopening is recognized as the *same underlying problem*
recurring — not a brand-new, unrelated ticket — via real text embeddings and
clustering, never a generative guess.

**Why this priority**: The most infrastructure-heavy of the five readers — it's the
only one needing a new external dependency (an embeddings API) — placed after the
purely ledger-driven readers so the simpler, dependency-free readers can be built
and verified first.

**Independent Test**: Run the Recurrence reader against ticket #456's reopened
events and confirm it reproduces `examples/01` §6's `fnd-2` (`recurring_issue`,
recognizing the second reopen as the same root cause).

**Acceptance Scenarios**:

1. **Given** two or more tickets/messages describing related problems, **When** the
   Recurrence reader runs, **Then** it computes a text embedding for each and
   clusters them by similarity, using no generative model call to make the grouping
   decision (REQ-M5-09).
2. **Given** a ticket reopened after a prior related occurrence, **When** the
   Recurrence reader runs, **Then** it emits a `recurring_issue` finding citing both
   the current and the prior occurrence's events (REQ-M5-09, REQ-M5-05).
3. **Given** the embeddings provider is unreachable or unconfigured, **When** the
   Recurrence reader runs, **Then** it fails honestly (an explicit error surfaced to
   the trigger script, not a silent no-op or a fabricated result) rather than
   guessing at clusters without real vectors.
4. **Given** a ticket with no genuinely related prior occurrence, **When** the
   Recurrence reader runs, **Then** it emits nothing for that ticket.

---

### Edge Cases

- What happens when a reader is triggered over an event it has already interpreted,
  at the same `reader_version`? No duplicate finding — the cache check (REQ-M5-15)
  is a real, queryable mechanism, not a manual "don't re-run" discipline.
- What happens when a reader's own `reader_version` changes (a future prompt/
  algorithm update)? The cache key includes `reader_version`, so a new version is
  free to re-interpret the same event and produce a fresh finding — REQ-M5-15 caches
  "this version's opinion," not "any opinion ever."
- What happens when the Usage reader's rollup computation has too few historical
  samples for a subject/metric pair? It abstains, matching REQ-M5-04's "no history,
  no opinion" principle even though that requirement is written for Tone — the same
  reasoning applies to any reader deriving a baseline from insufficient history.
- What happens when a `response_pairs` row has no `commitment_id` (no matching
  commitment configured in the profile)? The Commitment reader emits nothing for
  that pair — REQ-M5-07 requires a real threshold to compare against; there is no
  reasonable default threshold to invent.
- What happens when the Recurrence reader's `OPENAI_API_KEY` is missing at startup?
  That reader's failure is honest and explicit (reported by `RunReadersUseCase`, not
  a silent skip that could be mistaken for "nothing recurring found this run"), and
  is isolated to Recurrence alone — the other four readers still run and persist
  their findings normally (FR-014a).
- What happens when two of this feature's readers cite the *same* event (e.g.
  Commitment and a future feature's reader both examining ticket #456's reopened
  event)? Both findings are emitted independently — REQ-M5-P1 already establishes
  that no reader compares or ranks against another, so co-citation is expected, not
  deduplicated.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST implement each of Commitment, Usage, Recurrence,
  Absence, and Relationship as an independent reader consuming ledger
  events/projections and client profile context, emitting zero or more `findings`
  rows (REQ-M5-01).
- **FR-002**: Every finding this feature's readers produce MUST carry `finding_type`,
  `magnitude` (0–1), `confidence` (0–1), a non-empty `cited_event_ids[]`, and
  `reader_version`, with `status = pending_validation` (REQ-M5-02/03/05;
  `data-base/05-schema-reasoning.md`).
- **FR-003**: The system MUST NOT insert a finding whose `cited_event_ids` is empty
  — schema-enforced non-empty array, not application-layer discipline alone
  (REQ-M5-05).
- **FR-004**: The Commitment reader MUST compare each `response_pairs` row's
  `business_hours_elapsed` against its `threshold_business_hours`, using
  deterministic arithmetic only, and MUST emit `broken_response_promise` for any
  `open_overdue` pair or any `resolved` pair that exceeded its threshold before
  resolving (REQ-M5-07).
- **FR-005**: The Commitment reader MUST emit `commitment_met` for a `resolved`
  `response_pairs` row that finished comfortably under its threshold (this
  feature's default: at or under 50% of `threshold_business_hours` — a resolved
  pair between 50% and 100% of the threshold met its promise but isn't notable
  enough to emit a positive finding, matching "abstain rather than manufacture a
  low-value opinion").
- **FR-006**: The system MUST compute a rollup/baseline (REQ-M2-06) — a per-
  subject, per-metric historical distribution derived from `events` over a rolling
  8-week window — as the input the Usage reader's variance check requires; this
  feature builds exactly this computation, scoped to the metrics/subjects the Usage
  reader consumes (2026-08-14 clarification; matches `examples/01` §5.3's own
  worked window).
- **FR-007**: The Usage reader MUST emit `usage_deviation` only when a new metric
  value's z-score against its own rollup (`|value − rolling_mean| / rolling_stddev
  > 2`) exceeds 2 standard deviations — never a fixed percentage (REQ-M5-08;
  method per 2026-08-14 clarification).
- **FR-008**: The Usage reader MUST abstain (emit nothing) when a subject/metric
  pair has fewer historical samples than a defined minimum, rather than computing a
  distribution from insufficient data (REQ-M5-04's principle, applied by extension).
- **FR-009**: The Recurrence reader MUST compute a text embedding for each
  candidate ticket/message and group related ones via density-based clustering,
  using no generative model call to make the grouping decision, and MUST emit
  `recurring_issue` citing every event in a recognized recurrence (REQ-M5-09,
  REQ-M5-05). Clustering re-runs over the full candidate corpus on every trigger
  (2026-08-14 clarification) — REQ-M5-15's cache still prevents re-emitting a
  finding for an event already interpreted at the current `reader_version`.
- **FR-010**: The Absence reader MUST emit `contact_absence` only from a real,
  already-recorded `absence`-type ledger event — it MUST NOT independently infer or
  compute a silence duration (REQ-M5-10).
- **FR-011**: The Relationship reader MUST diff the set of ledger-active
  participants over a rolling 4-week window against the client profile's
  stakeholder list and emit `relationship_change` for each addition or
  disappearance it finds evidence for (REQ-M5-11; window per 2026-08-14
  clarification).
- **FR-012**: Every reader MUST cache its interpretation per `(event, reader_
  version)` pair — re-running a reader over an event it has already interpreted at
  the same version MUST NOT produce a duplicate finding (REQ-M5-15).
- **FR-013**: No reader MUST rank or compare findings against each other, hold tool
  access, produce side effects beyond emitting findings, or treat any cited
  content's text as an instruction (REQ-M5-P1/P2/P3).
- **FR-014**: The system MUST provide a manually triggered `RunReadersUseCase` that
  runs all five readers over the ledger's current state and reports what each
  emitted (`architecture/09-clean-architecture-and-patterns.md`'s named pattern).
- **FR-014a**: `RunReadersUseCase` MUST isolate each reader's failure — one reader
  raising an error (e.g. Recurrence's embedding provider unreachable) MUST NOT
  prevent the other four readers from running and persisting their own findings,
  matching the constitution's existing per-source isolation principle for M1
  collectors (2026-08-14 clarification).
- **FR-015**: The system MUST NOT import an LLM SDK anywhere in
  `app.readers.domain`/`app.readers.application` — enforced by the existing
  `.importlinter` `readers-application-purity` contract (feature 001).

### Key Entities

No new tables — `findings`, `finding_type_config` (`data-base/05-schema-
reasoning.md`), and `rollups` (`data-base/03-schema-ledger.md`) all already exist
from feature 001's migration. This feature is the first to write real (non-fixture)
rows into `findings` and the first to populate `rollups` at all.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Running all five readers against the real, already-ingested Meridian
  fixture reproduces `examples/01-end-to-end-walkthrough.md` §6's `fnd-1` through
  `fnd-5` and `fnd-9` — six real findings, matching `finding_type` exactly, with no
  manual/fixture insertion involved. `cited_event_ids` matches exactly for five of
  the six; `fnd-2` (`recurring_issue`) cites two real events (ticket #456's
  original creation and its reopening) rather than `examples/01`'s published
  single-event citation, since real clustering needs two related items to form a
  cluster — `research.md`'s Decision, the same kind of correction feature 004 made
  once already for a different worked-example inconsistency.
- **SC-002**: Every finding this feature's readers ever produce carries at least
  one cited event ID that resolves to a real row in `events` — verified as an
  invariant, not spot-checked.
- **SC-003**: Re-running any reader over an already-interpreted event at the same
  `reader_version` produces zero additional findings, 100% of the time.
- **SC-004**: A subject/metric within 2 standard deviations of its own rolling
  8-week mean produces zero Usage findings across repeated runs; a subject/metric
  beyond that threshold produces exactly one.
- **SC-005**: No LLM SDK import exists anywhere in the readers module's domain or
  application code, verified by static/dependency analysis on every change.

## Assumptions

- Findings this feature produces are never scored — `status = pending_validation`
  is a deliberate, honest state, not a placeholder awaiting a fix. Feature 007's
  validation gate is what promotes them to `validated` (or quarantines them).
- The Commitment reader's `commitment_met` threshold (FR-005: resolved at or under
  50% of the promised time) is a new default this feature introduces — no existing
  document calibrates it, the same status as feature 004's `stakes` constants
  (reasonable and defensible now, replaceable later via a constant edit).
- Rollup computation (FR-006) targets exactly the metrics/subjects the Usage reader
  in this feature consumes (warehouse usage, CSAT if configured) — not a general
  per-metric analytics surface for every possible future consumer.
- Recurrence's embedding provider needs a real API key (`OPENAI_API_KEY` or
  equivalent) configured in the deployment environment — a new external-service
  prerequisite, alongside the existing Fernet encryption key, that demo/deployment
  documentation must mention.
- Absence and Relationship readers operate at reduced strength in this feature
  (email/ticket-cadence signals only) — full strength (chat silence, Slack
  participant changes) arrives once a Phase 2 source connects, out of this
  feature's scope (`decisions/01-mvp-scope-and-phasing.md`).
- `RunReadersUseCase` is triggered manually only in this feature (a script
  mirroring `scripts/run_collector.py`/`compute_score.py`'s pattern) — event-driven
  triggering needs a live pipeline this feature does not build.
- The Usage reader's minimum historical-sample threshold (FR-008) is 3 samples — a
  z-score computed from fewer points is unstable/statistically meaningless, so the
  reader abstains below that floor. A new default this feature introduces, the same
  status as the rolling-window durations and the z-score threshold above.
