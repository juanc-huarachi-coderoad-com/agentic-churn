# Feature Specification: Feedback Memory

**Feature Branch**: `010-feedback-memory`

**Created**: 2026-08-16

**Status**: Draft

## Clarifications

### Session 2026-08-16

- Q: When a verdict is submitted scoped to a whole issue (`issue_id` set, no
  `finding_id`) — an issue can group findings from several different readers
  (`data-base/05-schema-reasoning.md`'s Issue B: tone, escalation language,
  CSAT, and silence findings, from two different people) — how should it
  determine which damping pattern(s) to update? → A: No fan-out needed.
  `false_alarm`/`correct` verdicts always target a specific `finding_id`;
  they are never submitted at issue level. Issue-scoped verdicts are
  effectively always `resolved` in practice, and REQ-M6-CAL-03b already
  says `resolved` never touches the weight formula — so this case never
  needs to pick a pattern, and one click can never touch several different
  readers' weights at once (REQ-M4-P2).
- Q: `pattern_signature`'s third component, "event_signature_class"
  (`data-base/07-schema-feedback.md`), has no definition anywhere else in
  the requirements/architecture docs. What should it be? → A:
  `events.event_type` — the existing 7-value closed enum already defined on
  `events` (`message`, `ticket_state_change`, `usage_measurement`,
  `survey_response`, `meeting`, `absence`, `crm_change`,
  `data-base/03-schema-ledger.md`). No new taxonomy. **Corrected during
  `/speckit-plan` (2026-08-16):** the already-shipped, already-verified
  scoring engine (feature 004, `RecomputeScoreUseCase.execute`,
  `backend/app/scoring/application/use_cases.py:155`) reads
  `pattern_signature` as literally `f"{finding.reader_type}+{finding.finding_type}"`
  — **two** components, with no event-type join at all (the `Finding`
  entity it operates on doesn't even carry one, only `cited_event_ids`).
  `data-base/07-schema-feedback.md`'s "event_signature_class" third
  component was never actually implemented this way. Since this feature
  must write keys the already-running reader can match — a 3-component
  writer against a 2-component reader would make every lookup miss and
  damping silently never apply — this feature follows the shipped 2-component
  format instead. Every FR/edge case/entity below that referenced a third
  component has been corrected accordingly; `data-base/
  07-schema-feedback.md`'s prose is corrected in the same pass
  (`research.md` Decision 1, matching this repo's own "fix a cross-file
  inconsistency everywhere it appears" convention, `AGENTS.md`).

**Input**: User description: "Feature 010: feedback-memory (Build-order phase 10 ·
Learning loop). Implements REQ-M4-01 through REQ-M4-05 and prohibitions
REQ-M4-P1/P2 from requirements/04-feedback-memory.md, using the damping formula
from requirements/13-scoring-calibration-appendix.md REQ-M6-CAL-03a/b, the
schema in data-base/07-schema-feedback.md (feedback_verdicts, damping_weights),
and the flow in sequences/03-sequence-feedback-loop.md.

Allow any finding-bearing card (dashboard, evidence trace panel, ask-agent
answers) to be marked with a verdict of correct, false_alarm, or resolved via a
single-click control with no modal or confirmation toast. Each verdict is
logged append-only in feedback_verdicts (matched to a pattern_signature of
reader_type + finding_type + event_signature_class) and upserts a
damping_weights row whose weight is recomputed via weight = clamp(0.5 ^
false_alarm_count x 1.15 ^ correct_count, 0, 1.0). This damping weight is
consumed as a multiplicative term (0 to 1.0) by the scoring engine (M6,
REQ-M6-01) on every future scoring run — it never rewrites a past score_run.
Whenever a damped finding is displayed with damping < 1.0, its plain-language
disclosure_text (e.g. "weight reduced — your team dismissed this pattern
twice") must be shown alongside it, so the learning is never a silent black
box. No model weights, prompts, or embeddings are ever changed by feedback —
this is pure counting and lookup. Damping applies only to matched patterns,
never as blanket suppression of an entire reader type, and a dismissed finding
type must remain visible (damped and labeled), never hidden or deleted."

## Note on scope for this feature

Requirement content is **not** restated here — every functional requirement
cites the `REQ-<ID>` that is its source of truth (`requirements/
04-feedback-memory.md`, and `requirements/13-scoring-calibration-appendix.md`
for the exact damping formula).

**In scope**: the one-click verdict control on any finding-bearing card
(dashboard, evidence trace panel, ask-agent answers); the append-only
`feedback_verdicts` log; the `pattern_signature`-keyed `damping_weights`
upsert and its exact formula (REQ-M6-CAL-03a/b); surfacing `disclosure_text`
wherever a damped finding (`damping < 1.0`) is displayed; and the read-only
contract the scoring engine (M6) consumes on every future run.

**Explicitly out of scope, with a reason each**:

- **The scoring engine's own consumption of the `damping` term inside its
  point formula** (`points = base × influence × criticality × confidence ×
  magnitude × recency × damping`). That formula and its `score_contributions`
  persistence already belong to feature 004 (`requirements/
  06-scoring-engine.md`, REQ-M6-01); this feature only produces the
  `damping_weights` row M6 reads — it does not modify the scoring engine
  itself.
- **Rewriting or annotating any past `score_run`.** Spec §8.7 and REQ-M6-20
  (cited by `sequences/03-sequence-feedback-loop.md`'s key invariant) already
  make history immutable; this feature has nothing to build here beyond not
  violating that boundary.
- **Which specific findings are eligible for a verdict control in the UI
  (card types, layout).** That surface already exists per finding-bearing
  card built by features 006 (dashboard evidence trace)/007 (model
  findings)/008 (ask agent); this feature adds the verdict action to those
  existing surfaces, it does not redesign them.
- **Any change to reader logic, prompts, or models as a consequence of a
  verdict.** REQ-M4-05 makes this an architectural absence, not a feature to
  build and then gate.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Marking a finding false alarm measurably reduces future occurrences of that pattern (Priority: P1)

A CS lead reviewing a finding they know is wrong — the system flagged
"Diego stepping back" as a relationship risk, but he's actually on
pre-announced parental leave — clicks **false alarm** on that card. Nothing
about today's already-computed score changes. But the next time the
Relationship reader raises the same kind of finding (same reader, same
finding type), it counts for less — and if the team dismisses that same
pattern a second time, it counts for even less.

**Why this priority**: This is REQ-M4-01/02/03's entire purpose and the
reason feedback memory exists at all (`specs/ROADMAP.md`, build-order Phase
10, "the learning loop"). Every other requirement in this feature (the
disclosure text, the `correct`/`resolved` distinction) only matters once this
core mechanism — a human correction measurably changing a future outcome —
already works.

**Independent Test**: Seed a validated finding with a known `reader_type` +
`finding_type`, submit a `false_alarm` verdict against it, then seed a
second finding matching the same pattern and confirm
its future `score_contributions.damping` reads `0.500` (REQ-M6-CAL-03a); repeat
the `false_alarm` verdict on the same pattern and confirm the next matching
finding's damping reads `0.250`; confirm the score already computed before
either verdict is byte-for-byte unchanged.

**Acceptance Scenarios**:

1. **Given** a displayed finding-bearing card, **When** the CS lead clicks a
   verdict control, **Then** the system records the verdict (`correct`,
   `false_alarm`, or `resolved`) in a single click, with no modal dialog and
   no confirmation toast (REQ-M4-01, non-functional constraint: spec §11.6).
2. **Given** a recorded `false_alarm` verdict, **When** the system computes
   that pattern's damping weight, **Then** it matches the finding's
   `reader_type` + `finding_type` into a `pattern_signature` and recomputes
   `damping_weights.weight` using
   `clamp(0.5 ^ false_alarm_count × 1.15 ^ correct_count, 0, 1.0)`
   (REQ-M4-02, REQ-M6-CAL-03a) — one `false_alarm` yields `0.500`, a second
   on the same pattern yields `0.250`.
3. **Given** an updated `damping_weights` row, **When** the next scoring run
   processes a new finding matching that pattern, **Then** the scoring
   engine reads the current weight as a multiplicative term
   (`0 ≤ damping ≤ 1.0`) in its point calculation (REQ-M4-03).
4. **Given** a `score_run` already computed before a verdict was submitted,
   **When** that verdict is recorded and the pattern's weight changes,
   **Then** the already-computed `score_run` and its `score_contributions`
   rows remain exactly as they were — feedback only changes future scoring
   runs, never past ones (`sequences/03-sequence-feedback-loop.md` key
   invariant).

---

### User Story 2 - The team can always see why a card's weight was reduced (Priority: P1)

A CS lead looking at a dashboard card, an evidence trace panel entry, or an
ask-agent answer that cites a damped finding sees, right there on the card,
a plain-language reason: "weight reduced — your team dismissed this pattern
twice." The finding itself is never hidden or silently deleted because the
team once dismissed something like it — it stays visible, just labeled and
counted for less.

**Why this priority**: REQ-M4-04 and the explicit prohibition REQ-M4-P1
exist specifically to prevent feedback memory from becoming exactly the kind
of silent, unaccountable "the system learned something" black box the
product deliberately avoids (spec §15, Goodhart's law risk mitigation). A
damping mechanism nobody can see or audit is worse than no damping at all.

**Independent Test**: Seed a `damping_weights` row with `weight < 1.0` and a
non-empty `disclosure_text`; render a finding matching that pattern on each
of the three card surfaces (dashboard, evidence trace panel, ask-agent
answer) and confirm the disclosure text is present and accurate on each;
separately confirm the underlying finding type still appears on a fresh
query even after being dismissed multiple times.

**Acceptance Scenarios**:

1. **Given** a finding whose matching pattern has `damping_weights.weight <
   1.0`, **When** that finding is displayed on any surface, **Then** the
   card shows the pattern's current `disclosure_text` in plain language
   (REQ-M4-04).
2. **Given** a pattern that has never received a verdict, **When** a
   matching finding is displayed, **Then** no damping disclosure is shown
   (its weight is the un-dampened default) — the disclosure only ever
   appears when it is true and relevant.
3. **Given** a finding type that has been marked `false_alarm` repeatedly,
   **When** a new matching finding is generated, **Then** it still appears
   on the dashboard/evidence trace — damped and labeled, never hidden or
   silently discarded (REQ-M4-P1).
4. **Given** the set of verdict controls available anywhere in the system,
   **When** a CS lead looks for a way to dismiss an entire reader type in
   one action, **Then** no such control exists — every verdict is scoped to
   the specific finding or issue clicked, matched only against its own
   pattern, never applied as blanket suppression across a reader
   (REQ-M4-P2).

---

### User Story 3 - Correct and resolved verdicts behave differently from false alarm (Priority: P2)

When the team confirms a finding was right (`correct`) or that the
underlying issue has since been fixed (`resolved`), the system records that
too — but neither one damps future findings the way a false alarm does.
`correct` gradually rebuilds a pattern's trust after a prior false alarm,
though never in one step; `resolved` doesn't touch the weight at all, since
it's a statement about the issue, not about whether the reader was right to
flag it.

**Why this priority**: This is P2 relative to Stories 1/2 because the core
damping mechanism (false alarm reducing weight, and disclosure always
visible) already delivers the feature's primary value on its own; the
`correct`/`resolved` distinction refines that mechanism's fairness and
accuracy rather than introducing a new capability.

**Independent Test**: On a pattern already damped to `0.250` by two prior
`false_alarm` verdicts, submit one `correct` verdict and confirm the weight
becomes `0.2875` (REQ-M6-CAL-03a worked value), not `1.0` and not unchanged;
separately submit a `resolved` verdict on an undamped pattern and confirm
`resolved_count` increments while `weight` stays at `1.0`.

**Acceptance Scenarios**:

1. **Given** a pattern with `false_alarm_count = 2` (`weight = 0.250`),
   **When** a `correct` verdict is recorded against that pattern, **Then**
   `correct_count` increments and the weight is recomputed to `0.5² ×
   1.15¹ = 0.2875` — a partial recovery, never an immediate return to `1.0`
   (REQ-M6-CAL-03a worked check).
2. **Given** any pattern, **When** a `resolved` verdict is recorded against
   it, **Then** `resolved_count` increments and feeds the disclosure text,
   but `weight` is left completely unchanged (REQ-M6-CAL-03b).
3. **Given** a verdict of any kind, **When** it is recorded, **Then** no
   model weights, prompts, or embeddings anywhere in the system are altered
   as a side effect — the verdict only ever changes stored counts and a
   derived numeric weight (REQ-M4-05).

---

### Edge Cases

- What happens when a verdict is submitted with neither `finding_id` nor
  `issue_id` set? → Rejected — every verdict must apply to something
  concrete; a verdict with both fields empty is structurally meaningless
  (`data-base/07-schema-feedback.md`'s `CHECK` constraint).
- What happens the first time a pattern ever receives a verdict? → A new
  `damping_weights` row is created (upserted) for that `pattern_signature`
  with counts starting from zero, rather than requiring a pre-seeded row to
  exist.
- What happens when a pattern accumulates enough `false_alarm` verdicts that
  the formula's output would go below `0`? → The weight is clamped at `0`,
  never negative — a negative weight would flip a penalty into a bonus,
  which is never a valid outcome of "the team said this was wrong"
  (`data-base/07-schema-feedback.md`).
- What happens when a pattern accumulates enough `correct` verdicts that the
  formula's output would exceed `1.0`? → The weight is clamped at `1.0`, its
  ceiling — feedback can never make a pattern count for *more* than its
  undamped baseline.
- What happens when the same card is clicked with a different verdict later
  (e.g. `false_alarm` today, `correct` next week after further review)? →
  Both verdicts are recorded as separate, permanent rows in
  `feedback_verdicts` — nothing is ever overwritten or deleted, matching
  this database's append-only convention elsewhere; the weight reflects the
  cumulative history of all verdicts on that pattern, not just the latest
  one.
- What happens when two findings share the same `reader_type` and
  `finding_type` but were triggered by different kinds of underlying events
  (e.g. a `ticket_state_change` versus a `message`)? → They are the *same*
  pattern (`pattern_signature` is `reader_type+finding_type` only,
  Clarifications 2026-08-16 correction) — a verdict on one damps the
  other too. This is the granularity the already-shipped scoring engine
  (feature 004) matches on, and `finding_type_config`
  (`data-base/06-schema-scoring.md`) is itself keyed by `finding_type`
  alone with no event-type breakdown, so this granularity is consistent
  with how the rest of the scoring configuration already treats a finding
  type as one undifferentiated pattern regardless of which event
  triggered it.
- What happens when a `false_alarm` or `correct` verdict is submitted with
  only an `issue_id` and no `finding_id` (e.g. a malformed or malicious
  direct API call, bypassing the UI's own controls)? → Rejected — these two
  verdicts always require a specific `finding_id`, precisely to prevent one
  click on a multi-reader issue from silently touching several different
  readers' damping weights at once (FR-005a, Clarifications, 2026-08-16).
- What happens when an issue-scoped `resolved` verdict is recorded on an
  issue whose findings span multiple readers (e.g. tone, escalation
  language, and CSAT deviation all grouped into one issue)? → It doesn't
  matter which of those readers' patterns absorbs the bookkeeping — the
  verdict is attributed to the issue's top-ranked finding's pattern for
  `resolved_count`/disclosure purposes only, since REQ-M6-CAL-03b already
  guarantees a `resolved` verdict never changes any pattern's weight
  regardless of which one it's attributed to.
- What happens to a `score_contributions` row for a finding that was scored
  *before* a verdict changed its pattern's weight? → It keeps the `damping`
  value that was current at the time it was computed — immutable, like
  every other `score_runs`-derived row (spec §8.7).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: THE SYSTEM MUST allow any finding-bearing card — dashboard,
  evidence trace panel, or ask-agent answer — to be marked with a verdict of
  `correct`, `false_alarm`, or `resolved` (REQ-M4-01).
- **FR-002**: Recording a verdict MUST be a single click, with no modal
  dialog and no confirmation toast (REQ-M4-01, spec §11.6).
- **FR-003**: THE SYSTEM MUST require every recorded verdict to apply to a
  concrete target — either a specific finding or a specific issue — and
  MUST reject a verdict with neither set (`data-base/
  07-schema-feedback.md`'s `CHECK` constraint).
- **FR-004**: Every recorded verdict MUST be appended to a permanent,
  append-only log and MUST never be edited or deleted — a later correction
  is its own new row (REQ-M4-01, `data-base/07-schema-feedback.md`).
- **FR-005**: WHEN a verdict is recorded, THE SYSTEM MUST match it against
  the originating pattern of the finding it targets directly — or, for an
  issue-scoped `resolved` verdict (no `finding_id`), the issue's
  top-ranked finding (`finding_issue_map.rank_within_issue = 1`,
  `data-base/05-schema-reasoning.md`) — using its reader type and finding
  type, joined as `f"{reader_type}+{finding_type}"`, to identify the
  `pattern_signature` that `damping_weights` groups on. This MUST be
  byte-identical to the format the scoring engine already reads
  (`RecomputeScoreUseCase.execute`, `backend/app/scoring/application/
  use_cases.py`) — a mismatched format would make every lookup miss and
  damping silently never apply (REQ-M4-02, Clarifications, 2026-08-16
  correction).
- **FR-005a**: THE SYSTEM MUST require `false_alarm` and `correct` verdicts
  to target a specific `finding_id` — THE SYSTEM MUST reject either verdict
  submitted with only an `issue_id` and no `finding_id`, since matching them
  against every finding grouped under a multi-reader issue could change
  several different readers' damping weights from a single click
  (REQ-M4-P2). A `resolved` verdict MAY target either a `finding_id` or an
  `issue_id` (marking a whole issue as fixed) without this restriction,
  since REQ-M6-CAL-03b already guarantees `resolved` never alters any
  weight regardless of scope (Clarifications, 2026-08-16).
- **FR-006**: WHEN a `false_alarm` or `correct` verdict is recorded, THE SYSTEM MUST recompute that
  pattern's damping weight as `clamp(0.5 ^ false_alarm_count × 1.15 ^
  correct_count, 0, 1.0)`, where `false_alarm_count` and `correct_count` are
  the pattern's running totals after including this verdict
  (REQ-M6-CAL-03a).
- **FR-007**: A `resolved` verdict MUST increment that pattern's
  `resolved_count` and feed its disclosure text, but MUST NOT change
  `weight` (REQ-M6-CAL-03b).
- **FR-008**: WHEN a pattern has no prior `damping_weights` row, THE SYSTEM
  MUST create one on its first verdict rather than requiring the row to be
  pre-seeded (upsert semantics, `data-base/07-schema-feedback.md`).
- **FR-009**: THE SYSTEM MUST expose the current damping weight for each
  pattern as a multiplicative term (`0 ≤ damping ≤ 1.0`) for the scoring
  engine to consume on every future scoring run (REQ-M4-03).
- **FR-010**: THE SYSTEM MUST NEVER modify a previously computed
  `score_run` or its `score_contributions` rows as a result of a new
  verdict — only findings scored *after* the weight changes are affected
  (REQ-M4-03, `sequences/03-sequence-feedback-loop.md` key invariant).
- **FR-011**: WHEN a finding whose matching pattern has `damping < 1.0` is
  displayed on any surface, THE SYSTEM MUST show that pattern's current
  `disclosure_text` in plain language alongside it (REQ-M4-04).
- **FR-012**: THE SYSTEM MUST NEVER hide, suppress, or delete a
  finding-bearing card solely because its pattern has been dismissed —
  a damped finding remains visible, labeled with its disclosure text
  (REQ-M4-P1).
- **FR-013**: THE SYSTEM MUST scope every damping match to the specific
  `pattern_signature` a verdict targets — it MUST NOT provide any control
  or code path that damps an entire reader type in one action
  (REQ-M4-P2).
- **FR-014**: THE SYSTEM MUST NEVER alter a model's weights, prompts, or
  embeddings as a result of a verdict — feedback memory is limited to
  stored counts and a derived numeric weight (REQ-M4-05).
- **FR-015**: THE SYSTEM MUST record `submitted_by_user_id` from the
  authenticated caller's identity, never from free text supplied in the
  request body (`data-base/07-schema-feedback.md`, consistent with
  `/api/ask`'s existing `asked_by_user_id` pattern, feature 008).

### Key Entities

- **Feedback verdict**: One permanent, append-only record per verdict
  click — the target (a specific finding or issue), the verdict value
  (`correct` / `false_alarm` / `resolved`), who submitted it, the pattern
  signature it was matched against, and when. Never edited or deleted.
- **Damping weight**: One record per distinct pattern (reader type +
  finding type) — the current multiplicative weight consumed by scoring,
  running counts of each verdict type, and the precomputed plain-language
  disclosure text. Upserted every time a new verdict matches its pattern.
- **Pattern signature**: The matching key — `reader_type` + `finding_type`
  — that groups individual findings into the pattern a damping weight
  applies to, regardless of which specific event(s) triggered any one
  occurrence. Not a stored entity of its own beyond the key value carried
  on both `feedback_verdicts` and `damping_weights`; its exact format must
  match the already-shipped scoring engine's own construction of the same
  key (Clarifications, 2026-08-16 correction).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Marking a finding `false_alarm` once measurably reduces the
  damping weight for the next matching finding to `0.500`; a second
  `false_alarm` on the same pattern reduces it further to `0.250` — matching
  REQ-M6-CAL-03a's worked values exactly, verified against a real scoring
  run.
- **SC-002**: Whenever a displayed card's damping is below `1.0`, a
  plain-language reason is present and accurate 100% of the time — never a
  silently reduced weight with no visible explanation.
- **SC-003**: Submitting a verdict never changes a `score_run` or
  `score_contributions` row that was already computed before that verdict
  was submitted — verified byte-for-byte unchanged in 100% of exercised
  cases.
- **SC-004**: A CS lead can record a verdict in one click, with no
  additional dialog or confirmation step, in under the same order of time
  it takes to read the card itself.
- **SC-005**: No verdict submission, in any of the exercised cases, results
  in a change to any stored model weight, prompt template, or embedding —
  verified by inspecting every code path a verdict can reach.
- **SC-006**: A finding type that has been dismissed multiple times remains
  discoverable on a fresh query of the dashboard/evidence trace — it is
  never absent as a consequence of feedback, only visibly damped.

## Assumptions

- `pattern_signature` is exactly `reader_type` + `finding_type`, with no
  event-type or other third component — the format the already-shipped
  scoring engine (feature 004) already reads. This feature is a producer
  matching an existing consumer's contract, not free to choose its own
  format (Clarifications, 2026-08-16 correction).
- An issue-scoped `resolved` verdict's `resolved_count`/disclosure
  bookkeeping is attributed to the issue's top-ranked finding's pattern
  (`finding_issue_map.rank_within_issue = 1`) — a low-stakes default since
  REQ-M6-CAL-03b guarantees `resolved` never changes any pattern's weight
  regardless of which one absorbs the count (Clarifications, 2026-08-16).
- Verdict submission is available to any authenticated user of the existing
  session-based auth system (`data-base/12-users-and-auth.md`, feature 002)
  — there is no separate feedback-specific permission tier described
  anywhere in the requirements or architecture.
- `POST /api/feedback` (`architecture/07-api-spec.md`) is the
  already-specified route this feature implements against; this feature
  does not introduce new API surface beyond what that contract already
  defines.
- The scoring engine's own read of `damping_weights.weight` inside its
  point formula (`points = base × influence × criticality × confidence ×
  magnitude × recency × damping`) is feature 004's already-built consumer
  contract (REQ-M6-01); this feature is responsible only for producing a
  correct, current weight for that consumer to read, not for the formula
  itself.
