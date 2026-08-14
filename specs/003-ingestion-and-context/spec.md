# Feature Specification: Ingestion and Context

**Feature Branch**: `003-ingestion-and-context` *(no `before_specify` git hook is configured in `.specify/extensions.yml`, so no dedicated branch was auto-created — this work continues on `feature/setup-sdd`, same as features 001–002)*

**Created**: 2026-08-14

**Status**: Draft

**Input**: User description: "The event ledger and client profile — build-order Phase 3 (`base/Churn-Sentiment-Agent-Product-Specification.md` §16), per `decisions/01-mvp-scope-and-phasing.md`'s framing that M2 and M3 can't be partial. This is the first feature with real business logic (M1, M2, M3) rather than infrastructure/auth."

## Note on scope for this feature

Requirement content is **not** restated here — every functional requirement cites the
`REQ-<ID>` that is its source of truth. Four deliberate scope boundaries, each because a
downstream consumer or a real external dependency doesn't exist yet:

- **One real, fully-testable collector, not three live API integrations.** No live
  Gmail/Zendesk/warehouse credentials exist in this environment. This feature builds the
  `Collector` interface (the contract every source-specific adapter implements) and one
  concrete implementation — `SimulatedCollector`, reading a committed fixture file
  (`demo/fixtures/meridian-week.json`, created from `examples/01-end-to-end-
  walkthrough.md`'s Phase-1 subset: email + two tickets + a usage measurement). This is
  not an improvised shortcut — it's exactly the approach `demo/03-environment-and-
  fixtures-checklist.md` already documents for testing and demo purposes. Real
  Gmail/Zendesk/warehouse adapters are a follow-up, implementing the same interface.
- **Minimal thread stitching.** `REQ-M2-04` gets a real but simple heuristic
  (ticket-reference matching — a message mentioning "#456" links to that ticket's
  events), not exhaustive cross-channel sophistication.
- **No rollup/baseline computation yet.** `REQ-M2-06`'s "per-person rollups" projection
  is deferred — no reader exists yet to consume a baseline (Usage is Phase 5, Tone is
  Phase 7). Computing rollups with no consumer would be speculative generality
  (constitution P10); the table exists (feature 001) but this feature doesn't populate it.
- **Message-body encryption is real, not deferred.** Unlike the above, this is never
  phased — `REQ-M1-P4` and the privacy boundaries hold from the first line of code.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The client profile becomes queryable, versioned context (Priority: P1)

The CS lead's hand-authored YAML profile (spec §6.2's format) is parsed, schema-validated,
and stored as an immutable, versioned set of rows — stakeholders with influence
multipliers, product areas with criticality multipliers, commitments, and exclusions —
that every later module can query and trust.

**Why this priority**: Nothing else in this feature (or any later one) has anything to
resolve identity against, redact by, or weight by until this exists. `decisions/01-mvp-
scope-and-phasing.md` explicitly calls M3 one of the two modules "that can't be partial."

**Independent Test**: Submit the Meridian Logistics YAML (spec §6.2's worked example),
confirm a new `client_profile_versions` row plus its `stakeholders`/`product_areas`/
`commitments` rows exist with the right multiplier values; submit an invalid edit
(missing a required field, or zero `signs_renewal` stakeholders) and confirm it's
rejected before it can affect anything.

**Acceptance Scenarios**:

1. **Given** a valid client profile YAML, **When** it is submitted, **Then** a new
   `client_profile_versions` row is created with `is_current = true`, the previous
   current version flips to `false`, and it is never deleted (`REQ-M3-02`).
2. **Given** the submitted profile's stakeholders, **When** the version is stored,
   **Then** each stakeholder's `influence_multiplier` and each product area's
   `criticality_multiplier` are stored exactly as specified (`REQ-M3-03`).
3. **Given** a profile missing a required field, or with zero stakeholders marked
   `signs_renewal: true`, **When** it is submitted, **Then** it is rejected with a
   specific validation error and no new version is created (`REQ-M3-07`).
4. **Given** a new profile version is accepted, **When** the acceptance completes,
   **Then** a full replay is triggered (`REQ-M3-06`, `REQ-M2-07`).

---

### User Story 2 - Events append immutably to a tamper-evident, replayable ledger (Priority: P1)

Every accepted signal becomes a permanent, hash-chained event; a client message and its
reply become a business-hours-measured response pair against the client's own working
calendar; nothing is ever updated or deleted.

**Why this priority**: The other module `decisions/01-mvp-scope-and-phasing.md` calls
un-phaseable. Every later reasoning module (M5 onward) depends on this ledger being
correct and honest from day one — "auditability cannot be added later."

**Independent Test**: Append a sequence of events reproducing `examples/01`'s ticket
scenario (ticket #456: 19 business hours against a 4-hour promise; ticket #398: 2 hours),
confirm the hash chain verifies end to end, and confirm the response-pair arithmetic
matches exactly.

**Acceptance Scenarios**:

1. **Given** an accepted envelope, **When** it is appended, **Then** a new `events` row
   is created with both `occurred_at` and `recorded_at` populated, and the row is never
   subsequently updated or deleted (`REQ-M2-01`, `REQ-M2-02`).
2. **Given** a correction to a prior event, **When** it arrives, **Then** a new event is
   appended referencing the prior one via `supersedes_event_id`; the prior row is
   untouched (`REQ-M2-03`).
3. **Given** any sequence of appended events, **When** the hash chain is verified,
   **Then** every event's `event_hash` matches the recomputed value and links correctly
   to `prev_event_hash` (`REQ-M2-08`).
4. **Given** a client message and a qualifying reply, **When** the response pair is
   computed, **Then** the elapsed business hours are calculated against the client
   profile's working calendar and timezone, matching `examples/01`'s worked numbers
   exactly: 19.0 hours (`open_overdue`) for ticket #456, 2.0 hours (`resolved`) for
   ticket #398 (`REQ-M2-05`).
5. **Given** a message referencing an existing ticket by number, **When** thread
   stitching runs, **Then** the message's event is linked to that ticket's thread with a
   recorded confidence (`REQ-M2-04`).

---

### User Story 3 - Signals are collected, identified, redacted, and reported on honestly (Priority: P2)

A `SimulatedCollector` — implementing the same interface a real Gmail/Zendesk/warehouse
adapter would — reads the Meridian Phase-1 fixture, resolves each participant against the
client profile's stakeholders (or honestly marks them unresolved), strips anything on the
profile's exclusion list before storage, and produces a coverage report proving what was
and wasn't seen.

**Why this priority**: Depends on User Story 1 (identity/exclusion targets) and User
Story 2 (a ledger to append into) already existing — it's the pipe connecting them to the
outside world, not a foundation itself.

**Independent Test**: Run `SimulatedCollector` against `demo/fixtures/meridian-week.json`
twice in a row; confirm the first run produces one event per fixture item (six items —
`data-model.md`, adapted from `examples/01` §4's Phase-1 sources, including both
ticket #398's creation and resolution so its response pair is a genuine two-timestamp
computation, plus a sixth item exercising redaction) plus a coverage report, and the
second run produces zero new events (idempotent) with `duplicates_skipped` reflecting
exactly that.

**Acceptance Scenarios**:

1. **Given** the Meridian Phase-1 fixture, **When** `SimulatedCollector` runs, **Then**
   every item becomes an envelope with a deterministic idempotency key
   (`hash(source_type, source_native_id)`) and every field required by the standard
   envelope shape is populated (`REQ-M1-03`, `REQ-M1-10`).
2. **Given** the same fixture is processed twice, **When** the second run completes,
   **Then** zero new events are appended and `collector_runs.duplicates_skipped`
   reflects the collision count (`REQ-M1-03`, engineering acceptance criterion
   REQ-NFR-27).
3. **Given** Ana's email address is a known stakeholder identifier and the Zendesk
   reporter's contact is not, **When** identity resolution runs, **Then** Ana's envelope
   resolves to her stakeholder row and the ticket's envelope is honestly marked
   `identity_status = unresolved` — never a guessed match (`REQ-M1-04`, `REQ-M1-05`,
   `REQ-M1-P5`).
4. **Given** content matching the client profile's `exclusions` list, **When** an
   envelope is built, **Then** the matching portion is stripped before storage and the
   redaction is recorded in `redacted_fields` (`REQ-M1-09`).
5. **Given** a completed collector run, **When** the run finishes, **Then** a coverage
   report exists stating sources read, the covered window, and any gap reason — even for
   a run where a source failed (`REQ-M1-07`, `REQ-M1-08`).

---

### User Story 4 - The absence collector notices what didn't happen (Priority: P3)

A scheduled job compares each commitment's expected cadence (e.g. a weekly sync) against
the ledger's latest matching contact, and appends an `absence` event when the expected
contact is overdue.

**Why this priority**: Depends on User Story 1 (commitments to check against) and User
Story 2 (events to query for "last contact") — the smallest, most self-contained piece,
and the one place this feature directly implements product principle P6's opposite case:
noticing silence.

**Independent Test**: Seed a `recurring_sync` commitment with a weekly cadence and no
contact event in the last two weeks; run the absence collector; confirm an `absence`
event is appended citing the missed window.

**Acceptance Scenarios**:

1. **Given** a commitment with a defined cadence and no matching contact within its
   window, **When** the absence collector runs, **Then** an `absence` event is appended
   (`REQ-M1-06`).
2. **Given** a commitment whose cadence was just satisfied, **When** the absence
   collector runs, **Then** no `absence` event is appended for it.

---

### Edge Cases

- What happens when the same YAML profile is submitted twice, unchanged? A new version
  is still created (append-only, `REQ-M3-02`) — the system doesn't attempt to detect and
  skip a "no-op" edit; two identical profile versions are a valid, if unusual, state.
- What happens when a source is unreachable mid-run? The run completes for the sources it
  could reach, the coverage report names the gap, and the run is not retried
  automatically within this feature's scope (`REQ-M1-08`) — graceful degradation, not
  all-or-nothing.
- What happens when an envelope's participant matches more than one stakeholder
  identifier (e.g. a shared inbox)? Out of scope for this feature — the fixture data has
  no such case; the identity resolver's contract (`REQ-M1-P5`) already requires
  abstaining below a confidence threshold, which covers this case structurally even
  though it isn't exercised by the fixture.
- What happens if the encryption key file at `ENCRYPTION_KEY_PATH` is missing at
  startup? The collector must fail loudly at startup rather than silently storing
  plaintext — message-body encryption is a hard boundary, never optional (`REQ-M1-P4`).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST parse and schema-validate a submitted client profile YAML
  against the fields in `REQ-M3-01`, rejecting one missing a required field or with zero
  `signs_renewal: true` stakeholders (`REQ-M3-07`).
- **FR-002**: The system MUST store an accepted profile as a new, immutable
  `client_profile_versions` row (plus its `stakeholders`/`product_areas`/`commitments`/
  `profile_history_entries` rows), never overwriting a prior version (`REQ-M3-02`).
- **FR-003**: The system MUST supply the `influence` and `criticality` multipliers from
  the current profile version for later modules to consume (`REQ-M3-03`).
- **FR-004**: The system MUST trigger a full replay when a new profile version is
  accepted (`REQ-M3-06`).
- **FR-005**: The system MUST append every accepted envelope as an immutable `events`
  row with both `occurred_at` and `recorded_at`, and MUST NEVER update or delete an
  existing event (`REQ-M2-01`, `REQ-M2-02`, `REQ-M2-P2`).
- **FR-006**: The system MUST hash-chain every event per the algorithm in
  `data-base/03-schema-ledger.md` (SHA-256, canonical field order, genesis value for the
  first event) and MUST make the chain verifiable end to end (`REQ-M2-08`).
- **FR-007**: The system MUST compute response pairs in business hours against the
  current client profile's working calendar and timezone (`REQ-M2-05`).
- **FR-008**: The system MUST perform thread stitching using a ticket-reference heuristic
  at minimum, recording a confidence score for each stitched link (`REQ-M2-04`).
- **FR-009**: The system MUST implement one common `Collector` interface (`fetch`,
  `normalize`, `resolve_identity`, `emit_envelope`) and MUST provide `SimulatedCollector`
  as a concrete implementation reading `demo/fixtures/meridian-week.json` (`REQ-M1-01`).
- **FR-010**: The system MUST de-duplicate using an idempotency key derived from the
  source's native record ID, such that running a collector twice over an overlapping
  window produces zero duplicate events (`REQ-M1-03`, `REQ-NFR-27`).
- **FR-011**: The system MUST resolve each envelope's participant against the current
  client profile's stakeholder identifiers, marking `identity_status = unresolved` rather
  than guessing when no confident match exists (`REQ-M1-04`, `REQ-M1-05`, `REQ-M1-P5`).
- **FR-012**: The system MUST redact content matching the client profile's `exclusions`
  list before an envelope is persisted, and MUST record that a redaction occurred
  (`REQ-M1-09`).
- **FR-013**: The system MUST encrypt every envelope's payload and every event's body
  before storage, keyed from the deployment's `ENCRYPTION_KEY_PATH`, and MUST fail
  loudly at startup if that key is missing (`REQ-M1-P4`, spec §6.4).
- **FR-014**: The system MUST produce a coverage report for every collector run, stating
  sources read, the covered time window, and any gap reason, including for a run where a
  source failed (`REQ-M1-07`, `REQ-M1-08`).
- **FR-015**: The system MUST run a scheduled absence collector that appends an
  `absence` event when a commitment's defined cadence is not satisfied by any matching
  contact event within its window (`REQ-M1-06`).

### Key Entities

No new tables — `client_profile_versions`, `stakeholders`, `product_areas`,
`commitments`, `profile_history_entries` (`data-base/04-schema-context.md`); `sources`,
`collector_runs`, `coverage_reports`, `identity_map`, `raw_envelopes`
(`data-base/02-schema-ingestion.md`); `events`, `event_threads`, `response_pairs`
(`data-base/03-schema-ledger.md`) all already exist from feature 001's migration. This
feature is the first to read and write them for real.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Running the same collection twice over the same window produces zero
  duplicate events, 100% of the time.
- **SC-002**: The event ledger's hash chain verifies with zero broken links after any
  sequence of appends this feature produces.
- **SC-003**: Every response-pair calculation matches a hand-computed business-hours
  result exactly, including across a timezone and a weekend boundary.
- **SC-004**: An unresolved participant is never silently attached to the wrong
  stakeholder — 100% of low-confidence matches are marked unresolved, never guessed.
- **SC-005**: A coverage report exists for 100% of collector runs, including runs where a
  source failed.
- **SC-006**: Submitting an invalid client profile edit is rejected with a specific,
  actionable validation error in 100% of tested invalid cases.

## Assumptions

- Real Gmail/Zendesk/warehouse API adapters are out of scope for this feature (see scope
  note above) — `SimulatedCollector` is the one concrete adapter built and tested here.
- Rollup/baseline computation (`REQ-M2-06`'s per-person rollups) is deferred until a
  reader exists to consume it (Phase 5 Usage reader at the earliest) — building it now
  would be speculative generality with no consumer to validate against.
- The client profile is authored via direct YAML file edit by the CS lead
  (`decisions/00-open-questions-resolved.md` Q2) — no profile editor UI, which is
  Post-MVP.
- `demo/fixtures/meridian-week.json` is created as part of this feature, derived from
  `examples/01-end-to-end-walkthrough.md`'s Phase-1 subset (sources 1–3: email, tickets,
  product usage) — the same fixture `tests/strategy.md`'s golden-replay suite and the
  demo's contingency path will later depend on, per `demo/03-environment-and-fixtures-
  checklist.md`.
