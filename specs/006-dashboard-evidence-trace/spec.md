# Feature Specification: Dashboard Evidence Trace

**Feature Branch**: `006-dashboard-evidence-trace`

**Created**: 2026-08-15

**Status**: Draft

**Input**: User description: "Dashboard evidence trace — build-order Phase 6
(`specs/ROADMAP.md`): the full M8 health dashboard. Feature 002 built only the
dashboard *shell* — a permanent `learning` state showing the client's name and
"still learning" copy, with `score_block`/`contribution_bars`/`pulse_timeline`/
`stakeholder_cards`/`coverage_line` explicitly absent from its response (`specs/
002-dashboard-shell/contracts/dashboard.md`: "the rest is feature 006's job").
This feature fills in the rest of `architecture/07-api-spec.md`'s
`DashboardResponse` schema from real data that now exists — `score_runs`/
`score_contributions` (feature 004), `findings`/`events` (feature 005),
`coverage_reports`/identity resolution (feature 003) — and builds the evidence
trace panel (REQ-M8-08, `base/...md` §11.4: "the most important component in the
product"), the door from every number back to its source message."

## Clarifications

### Session 2026-08-15

- Q: How far back should the pulse timeline and score trend look? → A: A
  14-day rolling window for both — deliberately distinct from the Usage
  reader's 8-week window (feature 005), which is a statistical baseline, not a
  "what's recent" window.

## Note on scope for this feature

Requirement content is **not** restated here — every functional requirement
cites the `REQ-<ID>` that is its source of truth
(`requirements/08-health-dashboard.md`).

`requirements/08-health-dashboard.md` is titled "the full M8," but three of its
named UI touchpoints depend on modules that don't exist until *later* features in
`specs/ROADMAP.md`'s own build order. Rather than build fake affordances for
capabilities that don't exist yet — a discipline this codebase already enforces
elsewhere (REQ-M8-P2: never manufacture a concern-looking element;
`specs/002-dashboard-shell/contracts/dashboard.md`: absent fields, "not present
as empty arrays/nulls masquerading as no data yet") — this feature draws the
same kind of explicit boundary feature 005 drew around Tone/Intent/Meeting:

- **The Ask bar is out of scope.** REQ-M8-02 lists it as a dashboard component,
  but its behavior is `/api/ask` (M9, `requirements/09-ask-agent.md`) — feature
  008's scope. This feature does not render an ask bar, functional or stubbed.
- **Feedback controls are out of scope.** `base/...md` §11.4 item 6 lists
  correct/false-alarm/resolved controls on the evidence trace panel, but their
  effect — `damping_weights`, `requirements/04-feedback-memory.md` — is feature
  010's scope. This feature's evidence trace panel is read-only.
- **Narrator headline/reasons/actions text is out of scope.** REQ-M8-01 lists
  `narrator_outputs` as an input table, but it stays empty until feature 008's
  Narrator exists. Checked against `architecture/07-api-spec.md`'s own
  `DashboardResponse`/`EvidenceTraceResponse` schemas: neither actually contains
  a headline/reasons/actions field — every field either schema does define
  (`score_block`, `contribution_bars`, `pulse_timeline`, `stakeholder_cards`,
  `coverage_line`, plus the evidence trace's comparison/what-changed/quoted-
  messages/arithmetic-explanation) is derivable today from `score_runs`/
  `score_contributions`/`findings`/`events`/`coverage_reports` alone. Nothing in
  this feature's actual response shape is blocked on Narrator.

One reduced-strength field, honestly labeled rather than silently assumed, the
same pattern feature 005 used for Absence/Relationship:

- **`stakeholder_cards[].tone_trajectory` is always `unknown`.** The Tone reader
  (feature 007, `requirements/05-interpreters-readers.md`) is what would compute
  `stable`/`deteriorating`/`improving`; the schema's own enum already anticipates
  this (`architecture/07-api-spec.md`'s `StakeholderCard.tone_trajectory`
  includes `unknown`). `status` (`active`/`quiet`/`unresolved_identity`) is real
  today, derived from ledger activity and identity resolution (feature 003)
  rather than from Tone.

Two capabilities that are genuinely real today, worth naming so they aren't
mistaken for stubs:

- **`/api/coverage`'s quarantine list is real, but will always be empty until
  feature 007.** Quarantine entries (`failed_check`) are M5a's (`ValidationGate`)
  output; feature 005's own `research.md` already documents that M5a doesn't
  exist until feature 007. An empty list here is an honest reflection of "no
  finding has ever been quarantined yet," not a placeholder.
- **The "Unresolved person" state is real today**, built from
  `raw_envelopes.identity_status = 'unresolved'` (feature 003's identity
  resolution, already tested against a real Zendesk reporter in
  `tests/unit/test_simulated_collector.py`) — no new detection logic, just a
  read of an existing column.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The score, its causes, and the recent pulse are real, not a shell (Priority: P1)

The dashboard stops showing a permanent "still learning" message once real
scoring data exists — the CS lead sees the actual score, its trend, which
findings are pulling it up or down, and a timeline of what happened recently,
all read directly from already-computed tables.

**Why this priority**: This is the dashboard's core promise — "does anything
need me today?" — and it's currently unanswerable; feature 002 deliberately left
every data-bearing component absent. Nothing else in this feature matters if the
numbers themselves aren't on the screen.

**Independent Test**: With a real `score_runs` row and its `score_contributions`
already computed (feature 004's fixture/worked example), call `GET /api/dashboard`
and confirm the response's `score_block`, `contribution_bars`, and
`pulse_timeline` match those rows exactly — no client-side computation, no
narrative text invented.

**Acceptance Scenarios**:

1. **Given** a current `score_runs` row exists, **When** the dashboard loads,
   **Then** it renders the score number, band, and trend read directly from that
   row and its predecessors — never computed in the browser (REQ-M8-01, REQ-M8-P1).
2. **Given** `score_contributions` rows for the current run, **When** the
   dashboard loads, **Then** each renders as a contribution bar labeled by its
   finding type with its real point value, positive contributions visually
   distinguished (green) from negative ones (REQ-M8-02).
3. **Given** an account with zero negative findings, **When** the dashboard
   loads, **Then** the contribution bars area renders empty — not a "no data"
   placeholder, an honest empty state (REQ-M8-02, `base/...md` §11.3).
4. **Given** real ledger events cited by findings within the last 14 days,
   **When** the dashboard loads, **Then** the pulse timeline renders them in
   order with a severity dot and, when the event carries a real client message,
   that message's actual text rendered in a serif typeface as a quote (REQ-M8-02,
   REQ-M8-04).
5. **Given** the dashboard has just loaded, **When** the score block renders,
   **Then** the score visibly animates from its previous value to its current
   one (REQ-M8-03).
6. **Given** the score is Healthy with no findings pending action, **When** the
   dashboard loads, **Then** it displays "Nothing needs you today. Last checked
   [N] minutes ago." instead of the normal component set (REQ-M8-05).

---

### User Story 2 - Every number opens to its proof (Priority: P1)

Clicking any score, contribution bar, or pulse event opens the evidence trace
panel: how this behavior compares to normal, what specifically changed, the
actual quoted messages behind it, and the scoring arithmetic written out in
plain sentences — all the way down to a real, timestamped source message.

**Why this priority**: This feature's namesake, and `base/...md` §11.4's own
framing: "the most important component in the product." A number nobody can
verify is a number nobody will trust; REQ-M8-08 requires this to work for
*every* number, not a sample.

**Independent Test**: Call `GET /api/evidence/{score_contribution_id}` for a
real contribution tied to a real finding (e.g. feature 005's worked
`broken_response_promise` finding) and confirm the response's baseline/current
comparison, what-changed list, quoted messages, and arithmetic explanation all
trace to real `findings`/`events`/`score_contributions` rows — reproducing
`base/...md` §11.4's own worked example shape ("base 12, doubled because Ana
signs the renewal, reduced because the reader was 80% confident").

**Acceptance Scenarios**:

1. **Given** any rendered score, contribution bar, or pulse event on the
   dashboard, **When** a user clicks it, **Then** the evidence trace panel opens
   showing that specific item's finding (REQ-M8-08).
2. **Given** an evidence trace panel is open, **When** it renders, **Then** it
   shows a side-by-side comparison of normal-vs-current behavior rather than a
   single summarized value (`base/...md` §11.4 rule 1).
3. **Given** an evidence trace panel is open, **When** it renders the scoring
   arithmetic, **Then** every factor is written as a plain sentence citing the
   real number that produced it — never a bare formula (`base/...md` §11.4 rule
   2, "the arithmetic in words").
4. **Given** a finding's `cited_event_ids`, **When** the evidence trace panel
   renders quoted messages, **Then** each quote is the real decrypted message
   text, timestamped and attributed, in the serif client-quote typeface
   (REQ-M8-04, `base/...md` §11.4 item 4).
5. **Given** a `score_contribution_id` that doesn't exist, **When** the evidence
   endpoint is called, **Then** it returns a 404 rather than a fabricated or
   empty-but-200 response.

---

### User Story 3 - A quiet score can be trusted, or explained, at a glance (Priority: P2)

The CS lead can immediately tell whether a quiet dashboard means "genuinely
healthy" or "we're blind right now" — which sources are currently readable, how
current the data is, and (on the dedicated system health screen) exactly which
sources are down and what, if anything, has been quarantined.

**Why this priority**: Directly serves `requirements/08-health-dashboard.md`'s
own stated purpose distinction ("a quiet score means healthy versus we're blind
right now") — without it, silence is ambiguous, which undermines the entire
"quiet weeks are quiet" design goal.

**Independent Test**: With a real `coverage_reports` row showing a degraded
source (feature 003's own coverage-gap test scenario), call `GET /api/dashboard`
and `GET /api/coverage` and confirm both surface the same real gap — the
dashboard's coverage line summarizes it, the coverage screen enumerates it by
source.

**Acceptance Scenarios**:

1. **Given** the most recent `coverage_reports` row, **When** the dashboard
   loads, **Then** the coverage line states how many of the connected sources
   are currently readable and how current the data is (REQ-M8-06).
2. **Given** one or more sources are degraded or disconnected, **When** the
   system health screen loads, **Then** each source's real status and last
   successful sync time renders individually (`GET /api/coverage`,
   `architecture/07-api-spec.md`'s `CoverageResponse`).
3. **Given** no finding has ever failed a validation check, **When** the system
   health screen loads, **Then** the quarantine list renders empty — a real
   state, not a hidden or stubbed section.

---

### User Story 4 - The cast of stakeholders is visible, including who's gone quiet (Priority: P2)

Every stakeholder from the client profile appears as a card showing their role,
when they were last active, and whether their identity has resolved cleanly —
so a quietly disengaging sponsor or an unidentified frequent sender is visible
without digging.

**Why this priority**: Directly serves REQ-M8-02's stakeholder-cards component
and is real, ledger-backed data today (feature 003's identity resolution,
feature 005's Relationship reader) — lower priority than US1/US2 only because
the dashboard is still meaningful without it.

**Independent Test**: With the real Meridian profile's two stakeholders (one
active, one — per feature 005's fixture fix — inactive for over 28 days), call
`GET /api/dashboard` and confirm both render with the correct `status` and a
real `last_seen_at`, and that `tone_trajectory` is honestly `unknown` rather
than fabricated.

**Acceptance Scenarios**:

1. **Given** the current client profile's stakeholder list, **When** the
   dashboard loads, **Then** each stakeholder renders as a card with their real
   name, role, and most recent ledger activity timestamp (REQ-M8-02).
2. **Given** a stakeholder with no ledger activity in the current window,
   **When** their card renders, **Then** `status` is `quiet` rather than
   `active`.
3. **Given** a sender who has written multiple times but doesn't match any
   profiled stakeholder's identifiers, **When** the dashboard loads, **Then** a
   corresponding entry renders with `status = unresolved_identity` — visible,
   not silently dropped.
4. **Given** no Tone reader exists yet in this build order, **When** any
   stakeholder card renders, **Then** `tone_trajectory` is always `unknown` —
   never a fabricated `stable`/`deteriorating`/`improving` value.

---

### User Story 5 - The screen looks like what's actually true, not a generic loading state (Priority: P3)

Beyond the Healthy and Learning states already covered, the dashboard renders
the exact required copy for Source down, Catching up, and Unresolved person
whenever the underlying data says so — never a spinner or a made-up-sounding
message standing in for a real, nameable condition.

**Why this priority**: Polish on top of US1/US3's real data — every state this
story renders is already computable from data US1/US3 already expose; this
story is specifically about matching `base/...md` §11.5's exact required copy
per state, not new data.

**Independent Test**: Force each precondition in turn (a `coverage_reports` row
with a `source_down` gap; a stale-but-partial coverage window; an
`identity_status = 'unresolved'` sender with 3+ messages) and confirm the
dashboard's `state` field and message match `base/...md` §11.5's copy exactly
for each.

**Acceptance Scenarios**:

1. **Given** a source hasn't been successfully read since a specific past time,
   **When** the dashboard loads, **Then** it displays "[Source] hasn't been read
   since [time] — reconnect." (REQ-M8-07, `base/...md` §11.5).
2. **Given** the current data is partial and behind schedule, **When** the
   dashboard loads, **Then** it displays "Partial data — [N] minutes behind."
   (REQ-M8-07).
3. **Given** an unresolved sender has written 3 or more times, **When** the
   dashboard loads, **Then** it displays "Someone at [domain] has written [N]
   times and isn't in the profile. Who is this?" (REQ-M8-07).
4. **Given** more than one state's precondition is simultaneously true, **When**
   the dashboard loads, **Then** exactly one state is shown, by a defined
   precedence (see Edge Cases) — never more than one banner at once.

---

### Edge Cases

- What happens when `score_runs` has never run at all (a freshly provisioned
  deployment, before feature 004's triggers have ever fired)? The dashboard
  falls back to the existing `learning`/`no_profile` states feature 002 already
  defined — this feature adds new real states, it doesn't remove the honest
  fallback that already exists.
- What happens when a finding's `cited_event_ids` includes an event whose
  message body fails to decrypt? The evidence trace panel surfaces that
  specific quote as unavailable rather than failing the whole panel — the rest
  of the trace (comparison, what-changed, arithmetic) still renders from data
  that doesn't require decryption.
- What happens when more than one of Healthy/Learning/Source down/Catching
  up/Unresolved person could apply at once (e.g. a source is down *and* an
  unresolved sender exists)? A fixed precedence applies, most-actionable first:
  Source down > Unresolved person > Catching up > Learning > Healthy — a
  concrete gap is always surfaced over an ambient one.
- What happens when a `score_contribution_id` belongs to a `pending_validation`
  finding (feature 007's validation gate hasn't run yet, or the finding failed
  it)? It never appears as a contribution bar in the first place —
  `RecomputeScoreUseCase.list_validated()` (feature 004) already excludes
  anything not `validated`, so this case can't reach the evidence endpoint via a
  real dashboard click; a direct API call with a stale ID still gets a 404 (User
  Story 2, Acceptance Scenario 5).
- What happens to the pulse timeline when a cited event has no client-authored
  text (e.g. a warehouse usage reading)? `quoted_text` renders `null` — no
  fabricated quote — and the event still appears with its severity dot and
  timestamp.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `GET /api/dashboard` MUST render the full `DashboardResponse`
  shape (`architecture/07-api-spec.md`) — client header, score block,
  contribution bars, pulse timeline, stakeholder cards, coverage line — read
  directly from `score_runs`/`score_contributions`/`findings`/`events`/
  `coverage_reports`/`stakeholders`, with no scoring, ranking, or aggregation
  performed in this feature's own code beyond direct reads and formatting
  (REQ-M8-01, REQ-M8-02, REQ-M8-P1).
- **FR-002**: The score block MUST include the last 14 days of `score_runs`
  history (a trend/sparkline) so the frontend can animate from the previous
  value to the current one on load (REQ-M8-03).
- **FR-002a**: The pulse timeline MUST render cited ledger events from the last
  14 days only — a rolling window, distinct from the Usage reader's 8-week
  statistical baseline window (feature 005), which measures normalcy, not
  recency (REQ-M8-02).
- **FR-003**: Client-authored quoted text (pulse timeline, evidence trace
  quoted messages) MUST render in a visually distinct serif style from
  system-generated text, enforced as a reusable UI convention, not per-component
  styling (REQ-M8-04).
- **FR-004**: WHEN the account is Healthy with no pending items, THE SYSTEM
  MUST render "Nothing needs you today. Last checked [N] minutes ago." in place
  of the normal component set (REQ-M8-05).
- **FR-005**: THE SYSTEM MUST render a coverage line stating how many connected
  sources are currently readable and how current the data is (REQ-M8-06).
- **FR-006**: THE SYSTEM MUST render one of the defined states verbatim
  (Healthy, Learning, Source down, Catching up, Unresolved person) whenever its
  real precondition holds, using `base/...md` §11.5's exact copy per state, with
  the fixed precedence defined in Edge Cases when more than one applies
  (REQ-M8-07).
- **FR-007**: Every score, contribution bar, and pulse event rendered on the
  dashboard MUST be clickable through to `GET /api/evidence/{score_contribution_id}`
  (REQ-M8-08).
- **FR-008**: `GET /api/evidence/{score_contribution_id}` MUST return, for a
  real contribution: the finding's identity and point value, a baseline-vs-
  current comparison, an observable-only what-changed list, every cited
  message's real decrypted text with timestamp and attribution, and the scoring
  arithmetic rendered as plain-language sentences citing the real numbers
  involved — and MUST return 404 for an ID that doesn't resolve to a real
  contribution (REQ-M8-08, `base/...md` §11.4).
- **FR-009**: `GET /api/coverage` MUST return real per-source status and last-
  successful-sync data, plus the quarantine list (real, and empty until feature
  007's validation gate exists) (REQ-M8-06, `architecture/07-api-spec.md`'s
  `CoverageResponse`).
- **FR-010**: Stakeholder cards MUST render each profiled stakeholder's real
  name, role, most recent ledger activity, and a `status` of `active`, `quiet`,
  or `unresolved_identity` derived from real ledger/identity-resolution data;
  `tone_trajectory` MUST always be `unknown` in this feature (REQ-M8-02).
- **FR-011**: THE SYSTEM MUST NOT render any of the explicitly forbidden chart
  types (ticket-volume charts, per-message sentiment lines, monthly sentiment
  averages, category pie charts) or any metric that would not change a
  decision if it changed value (REQ-M8-09).
- **FR-012**: THE SYSTEM MUST NOT render the risk accent color (red) unless a
  promise has been broken or a sponsor has disengaged; amber covers drift;
  healthy states use no risk color (REQ-M8-10).
- **FR-013**: `GET /api/dashboard` and `GET /api/evidence/{id}` responses MUST
  each complete in under 1 second against a warm database (REQ-NFR-01,
  `requirements/08-health-dashboard.md`'s non-functional constraint).
- **FR-014**: This feature MUST NOT render an Ask bar or feedback controls
  (correct/false alarm/resolved) anywhere on the dashboard or evidence trace
  panel — both depend on modules out of this feature's scope (see Note on scope).

### Key Entities

No new tables — every field this feature renders already exists:
`score_runs`/`score_contributions` (`data-base/06-schema-scoring.md`, feature
004), `findings`/`finding_type_config` (`data-base/05-schema-reasoning.md`,
feature 005), `events`/`coverage_reports`/`raw_envelopes` (`data-base/02`/`03`,
feature 003), `stakeholders`/`client_profile_versions` (`data-base/04`, feature
003). This feature is a pure read/formatting layer over data every prior
feature already produces for real.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `GET /api/dashboard` and `GET /api/evidence/{id}` both complete in
  under 1 second against a warm, realistically populated database.
- **SC-002**: Every rendered score, contribution bar, and pulse event has a
  working click-through that opens the evidence trace panel for that specific
  item — verified for at least one real instance of each component type.
- **SC-003**: Every value shown in an opened evidence trace panel — the
  comparison, what-changed list, quoted messages, and arithmetic explanation —
  traces to a real row in `findings`/`events`/`score_contributions`; zero
  fabricated or placeholder values appear anywhere in the panel.
- **SC-004**: None of the explicitly forbidden chart types exist anywhere in the
  frontend component library, verified by inspection of the component set, not
  runtime sampling.
- **SC-005**: Given a real degraded-source scenario, a CS lead can determine
  "healthy" vs. "we're blind right now" from the dashboard's coverage line alone,
  without visiting a second screen.
- **SC-006**: The Healthy state renders with `base/...md` §11.5's exact copy
  when its real precondition (Healthy band, zero pending items) holds.

## Assumptions

- `score_runs` already exists for real accounts by the time this feature's
  dashboard is viewed — feature 004's hourly heartbeat trigger keeps it current
  even with zero new findings; this feature never needs to trigger scoring
  itself, only read its output.
- The "N minutes ago" / "N minutes behind" freshness language in REQ-M8-05/
  §11.5's Catching-up state is computed at read time from `computed_at`/
  `coverage_reports` timestamps against the current request time — not a stored
  column.
- "3 or more times" (the Unresolved person state's threshold, `base/...md`
  §11.5) is this feature's own default, matching the illustrative example
  verbatim — no existing document pins an exact count, the same status as
  feature 005's own newly-introduced numeric defaults (e.g. its commitment-met
  threshold).
- The fixed state precedence in Edge Cases (Source down > Unresolved person >
  Catching up > Learning > Healthy) is this feature's own default — no existing
  document specifies an order when multiple states' preconditions hold
  simultaneously.
- `tone_trajectory: unknown` and an always-empty quarantine list are permanent-
  for-now, honest values in this feature, not placeholders silently swapped
  later without a spec change — matching `specs/002-dashboard-shell/contracts/
  dashboard.md`'s own established precedent for how this codebase documents a
  cross-feature data dependency.
- The Ask bar and evidence-trace feedback controls are entirely absent from
  this feature's rendered UI (not stubbed/disabled) — features 008 and 010
  respectively will add them to the same screens this feature builds.
