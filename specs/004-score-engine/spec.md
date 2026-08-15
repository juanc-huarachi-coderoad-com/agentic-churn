# Feature Specification: Score Engine

**Feature Branch**: `004-score-engine` *(no dedicated branch created — no `before_specify` git hook is configured in `.specify/extensions.yml`; this work continues on the current branch, same as features 001–003)*

**Created**: 2026-08-14

**Status**: Draft

**Input**: User description: "Score engine — build-order Phase 4 (`base/Churn-Sentiment-Agent-Product-Specification.md` §16), which the spec itself calls 'the checkpoint': 'Scoring engine with hand-written findings... Proves the number before any AI exists.' This feature builds M6 (scoring engine) for real, computing `score_runs`/`score_contributions`/`band_history` for the first time, but proven against hand-authored/fixture-seeded findings — not real reader output, since M5 (readers, feature 005) and M5a (validation gate, feature 007) don't exist yet."

## Note on scope for this feature

Requirement content is **not** restated here — every functional requirement cites the
`REQ-<ID>` that is its source of truth. Build-order Phase 4 is explicitly framed by the
product spec itself as "the checkpoint... proves the number before any AI exists" — this
feature is deliberately scoped to prove the scoring *arithmetic* is correct, explainable,
and stable, using hand-authored evidence, before any reader module exists to produce
findings automatically. Five deliberate scope boundaries, each because a downstream
producer doesn't exist yet or a capability is explicitly Post-MVP:

- **Findings are hand-authored, not reader-produced.** No reader (M5, feature 005) or
  validation gate (M5a, feature 007) exists yet. This feature's fixture reproduces
  `examples/01-end-to-end-walkthrough.md` §9's exact 9-finding worked example, inserted
  directly with `status = validated` — the gate doesn't exist to run these findings
  through, so they're seeded pre-validated, matching how feature 003 seeded a client
  profile directly rather than waiting on a profile editor UI.
- **Issue groupings are fixture data; rank-within-issue arithmetic is not.** The
  Recurrence reader's clustering algorithm (REQ-M6-06) doesn't exist until feature 005.
  This feature's fixture hand-assigns findings to `issues`/`finding_issue_map` matching
  the worked example's two issues exactly — but the ranking-by-raw-size and the 0.6ⁿ
  diminishing-weight arithmetic *within* a given grouping (REQ-M6-07/08) is this
  feature's real, tested logic, not fixture data.
- **Only three of seven recomputation triggers get a real caller.** `manual`,
  `hourly_heartbeat`, and `profile_edit_replay` are wired for real. `new_event`,
  `burst_batch`, and `urgent_fast_path` need a live reader pipeline watching ledger
  events, which doesn't exist until features 005/007; `weight_edit_replay` has no
  caller since no weight-editing UI exists yet (Post-MVP,
  `decisions/00-open-questions-resolved.md` Q4). All seven trigger values remain valid
  states — this feature just doesn't build the four callers that don't have anything
  real to call them yet.
- **No new API route.** `architecture/07-api-spec.md` exposes score data exclusively
  through `GET /api/dashboard` (M8), which is feature 006's job. This feature computes
  and persists the score for the first time; wiring it into a dashboard response is a
  later feature's responsibility.
- **Damping is computed for real against data that's always at its default today.**
  `damping_weights` (M4, feature 010) exists as a table since feature 001, but no
  feedback verdict has ever been submitted — every lookup in this feature's own demo
  state returns the undamped default. The formula itself is implemented for real, not
  stubbed, since it's a simple, already-fully-specified calculation with no missing
  dependency.

## Clarifications

### Session 2026-08-14

- Q: REQ-M6-28's `stakes` value has no calibration anywhere in the doc set — unlike
  every other scoring formula (ageing, half-life, damping, hysteresis), which
  `requirements/13-scoring-calibration-appendix.md` pins to exact numbers. How should
  this feature resolve that gap? → A: Compute `stakes` for real now, with new
  seed-default constants pinned in this spec (FR-012) — reusing the established
  `criticality_multiplier` shape for `contract_value_band`, plus a bounded,
  continuous renewal-proximity curve — rather than leaving the MUST requirement
  (REQ-M6-28) unimplemented or deferring it with no consumer to validate against.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The score can be checked by hand against real evidence (Priority: P1)

A CS lead (or a skeptical engineer) can take the same hand-authored findings this
feature ships as its proof fixture, work the arithmetic on a calculator, and arrive at
exactly the score the system displays — the same worked example already published in
`examples/01-end-to-end-walkthrough.md` §9.

**Why this priority**: This is the checkpoint itself. `decisions/01-mvp-scope-and-
phasing.md` quotes the product spec directly: "if the score cannot be explained and
defended with hand-written findings, no amount of AI will fix it." Nothing else in this
feature matters if this doesn't hold exactly.

**Independent Test**: Load the fixture reproducing `examples/01` §9's 9 findings (`fnd-
1`..`fnd-9`) across two hand-assigned issues plus one standalone positive finding,
trigger a score computation, and confirm every `score_contributions` row and the final
`score_runs` totals match the corrected worked numbers to the decimal (`data-model.md`
— `examples/01` §9.2's own published Issue A rank order doesn't match its stated rule;
this feature's `IssueGrouper` implements the rule correctly, not the published
exception): `total_negative_points = 68.04`, `total_positive_points = 4.000`,
`positive_points_applied = 4.000`, `total_points = 64.04`, `score = 85.64`,
`band = at_risk`.

**Acceptance Scenarios**:

1. **Given** the 9-finding fixture, **When** a score is computed, **Then** each
   finding's `points_contributed` matches the worked example's per-finding value
   exactly (e.g. `fnd-1` = 39.00, `fnd-7` = 9.52) — `base × influence × criticality ×
   confidence × magnitude × recency × damping × rank_within_issue_factor` (REQ-M6-01).
2. **Given** Issue A's three findings ranked by raw point size, **When** the rank
   factor is applied, **Then** the 1st/2nd/3rd-ranked findings are weighted at
   100%/60%/36% respectively (`fnd-1`, `fnd-3`, `fnd-2` in that order — raw points
   descending, `data-model.md`), and Issue A's total (48.60) plus Issue B's total
   (19.44) sum in full — issues are never discounted against each other
   (REQ-M6-06..08).
3. **Given** the positive finding (4.00 raw points) against 68.04 negative points,
   **When** the positive cap is applied, **Then** the full 4.00 is subtracted (well
   under the 25%-of-negative ceiling of 17.01) (REQ-M6-13/14).
4. **Given** `total_points = 64.04`, **When** converted to a score, **Then** the
   result is exactly `100 × (1 − e^(−64.04/33)) ≈ 85.64`, classified as `at_risk`
   (REQ-M6-15..17).
5. **Given** any completed score computation, **When**
   `SUM(score_contributions.points_contributed)` is compared against
   `score_runs.total_negative_points`/`total_positive_points`, **Then** they are equal
   to the full stored decimal precision, for every run — not just the worked example
   (REQ-NFR-30, REQ-M6-CAL numbers included).

---

### User Story 2 - Evidence ages honestly, not uniformly (Priority: P1)

An unresolved, overdue promise gets *heavier* the longer it's ignored; a resolved
problem fades on a predictable half-life; an open-but-not-yet-overdue item neither
inflates nor deflates just because time passed.

**Why this priority**: This is what makes the score describe *today's* evidence rather
than a stale snapshot (Appendix A design commitment #8) — and it's the mechanism behind
one of the quiet-period behaviors `sequences/05-flow-recompute-triggers.md` documents
("quiet, we owe a reply → climbs daily"). Without this, the hourly heartbeat trigger
(User Story 4) would have nothing meaningful to recompute.

**Independent Test**: Compute recency for three findings in three different states
(`open`, `resolved`, `open_overdue`) at a fixed reference time, and confirm each
follows its own formula independently of the others.

**Acceptance Scenarios**:

1. **Given** a finding in `open` state, **When** recency is computed at any reference
   time, **Then** it is exactly 1.0 — no fade, no ageing (REQ-M6-10, REQ-M6-12).
2. **Given** a finding in `resolved` state with a known `half_life_days`, **When**
   recency is computed at exactly one half-life after resolution, **Then** it is
   exactly 0.5, and at two half-lives, exactly 0.25 (REQ-M6-09, REQ-M6-CAL-02).
3. **Given** ticket #456's broken-promise finding (`open_overdue`, 19 elapsed hours
   against a 4-hour threshold), **When** recency is computed, **Then** it is exactly
   1.30 (`min(1.0 + 0.08 × ((19−4)/4), 2.0)`), matching `examples/01` §9.2 and
   `requirements/13-scoring-calibration-appendix.md` REQ-M6-CAL-01 exactly.
4. **Given** an `open_overdue` finding with an extreme overdue ratio, **When** recency
   is computed, **Then** it never exceeds the 2.0 ageing cap, however overdue the
   finding gets (REQ-M6-CAL-01b).

---

### User Story 3 - A band label never wobbles on a one-point swing (Priority: P1)

Once the dashboard says "At risk," it takes a real, sustained recovery — not a single
lucky run — to say "Watch" again. Once it says "Watch," it takes two consecutive
confirming runs, not one, before it moves at all.

**Why this priority**: `sequences/06-state-band-hysteresis.md`'s whole reason for
existing: a label that flips every time the score crosses 65 by one point trains a CS
lead to ignore it. This is also the other half of the "checkpoint" claim — a correct
score means nothing if its displayed *label* is noisy.

**Independent Test**: Replay the exact two-week worked example from
`sequences/06-state-band-hysteresis.md`'s own worked example (week 0: score 78, enters
At risk; week 1: score 61 — below the 65 entry threshold but above the 55 exit
threshold) and confirm the band stays `at_risk` across both runs.

**Acceptance Scenarios**:

1. **Given** a score newly crossing 65 for the first time, **When** the band is
   evaluated, **Then** it does not display `at_risk` until this qualifying score holds
   for two consecutive runs (REQ-M6-19, REQ-M6-CAL-07 — every trigger type counts
   toward this, including the hourly heartbeat).
2. **Given** a displayed band of `at_risk` and a score that drops to 61, **When** the
   band is re-evaluated, **Then** it remains `at_risk` — only a drop below 55 would
   exit (REQ-M6-18).
3. **Given** `band_history` for a sequence of runs, **When** inspected, **Then** it
   records `consecutive_runs_in_band` per run, independent of and never fed back into
   the score calculation itself (REQ-M6-20, REQ-M6-P2).

---

### User Story 4 - The score recomputes on a schedule and after real context changes (Priority: P2)

The score is never stale by more than an hour even with zero new evidence (because
ageing changes it), always reflects the latest client-profile edit immediately, and is
never silently computed on a known-incomplete picture.

**Why this priority**: Lower priority than the arithmetic itself (User Stories 1–3)
because it's about *when* the (already-correct) computation runs, not whether it's
correct — but still real, wired behavior, not a stub, since the hourly heartbeat and
profile-edit paths both already have a real home to extend (feature 003's `worker.py`
and `SubmitProfileUseCase`).

**Independent Test**: Trigger a manual recompute, confirm a `score_runs` row appears
with `trigger = manual`; wait for (or force) the worker's hourly heartbeat and confirm
a second row appears with `trigger = hourly_heartbeat`; submit a client profile edit
(feature 003's `POST /api/profile/reload`) and confirm a third row appears with
`trigger = profile_edit_replay`, using the newly-current profile's multipliers.

**Acceptance Scenarios**:

1. **Given** the worker's existing APScheduler heartbeat, **When** an hour elapses,
   **Then** a new score run is recorded with `trigger = hourly_heartbeat`, reflecting
   any recency drift even if no new finding exists (REQ-M6-24).
2. **Given** a client profile edit accepted via `POST /api/profile/reload`, **When**
   the resulting replay completes, **Then** a new score run is recorded with `trigger =
   profile_edit_replay`, using the newly-current profile version's influence/
   criticality multipliers (REQ-M6-25, REQ-M3-05).
3. **Given** a scoring run where `coverage_reports.sources_read < sources_expected`
   for the most recent collector activity, **When** the run would otherwise compute,
   **Then** the score is instead frozen at its last value with `is_frozen = true` and
   `source_degraded = true`, rather than silently scoring on an incomplete picture
   (REQ-M6-26, REQ-NFR-32).
4. **Given** any trigger, **When** the run executes, **Then** the score is recomputed
   entirely from zero — the prior `score_runs` row is never read as an input to the new
   one (REQ-M6-20, REQ-M6-P2).

---

### Edge Cases

- What happens when no findings exist at all (a brand-new or perfectly healthy
  account)? `total_negative_points = 0`, `total_points = 0`, `score = 0`, `band =
  healthy` — the saturating formula's natural zero case, not a special-cased branch
  (P6: silence is a success state, expressed as the score's own resting value).
- What happens when a finding belongs to no issue (a standalone finding, like `fnd-9`)?
  It is scored with `rank_within_issue_factor = 1.000` and no discount — standalone
  findings are never penalized for not being clustered (REQ-M6-06's grouping is
  additive, not a prerequisite for being counted).
- What happens when positive points would, uncapped, exceed negative points entirely
  (a very healthy account with one large positive signal)? The 25%-of-negative cap
  still applies even though it would produce a near-zero or unintuitive result —
  goodwill softens, never erases or inverts, real evidence (REQ-M6-P3).
- What happens when the client profile has no `first_response` commitment, or a
  finding's product area/stakeholder doesn't resolve? `influence`/`criticality` default
  to 1.0 (REQ-M6-03, matching feature 003's precedent that an unresolved participant
  never silently attaches to the wrong multiplier).
- What happens when two triggers fire for the same underlying change (e.g. a profile
  edit that also happens to land within an hourly heartbeat window)? Each trigger
  produces its own independent `score_runs` row — runs are never deduplicated or
  merged, since REQ-M6-20 already guarantees each is a from-zero recomputation, so a
  redundant run is a safe no-op, not a correctness risk (matching feature 003's
  `research.md` precedent for replay-triggered-by-multiple-causes).
- What happens on the very first scoring run an account ever has — before any
  `band_history` row exists? There is no prior band to protect via hysteresis, so the
  first run's raw band classification displays immediately, with
  `consecutive_runs_in_band = 1`; the 2-consecutive-run stickiness rule (REQ-M6-19)
  only has something to hold *against* starting on the second run.
- What happens if a source is degraded on that same very first run — before any
  `score_runs` row exists to freeze at? There is no "last value" to fall back to, so
  the run computes and persists normally from the findings that *are* present, still
  marked `source_degraded = true` for visibility (REQ-M6-26 protects against silently
  treating an incomplete picture as complete on a *later* run — it does not require a
  prior value to exist before the system can honestly say "this is degraded").

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST compute each finding's contribution as `base ×
  influence × criticality × confidence × magnitude × recency × damping ×
  rank_within_issue_factor`, using only deterministic arithmetic (REQ-M6-01).
- **FR-002**: The system MUST source `base` from the versioned `finding_type_config`
  table, `influence`/`criticality` from the client profile version recorded on the run,
  and `confidence`/`magnitude` unmodified from the finding itself (REQ-M6-02..04).
- **FR-003**: The system MUST source `damping` from `damping_weights` via the formula
  `clamp(0.5^false_alarm_count × 1.15^correct_count, 0, 1.0)` (REQ-M6-05, REQ-M6-CAL-03a).
- **FR-004**: The system MUST rank findings within a shared issue by raw point size and
  apply a diminishing factor by rank (1st 100%, 2nd 60%, 3rd 36%, continuing ×0.6 per
  step), while counting each distinct issue's contribution in full (REQ-M6-06..08).
- **FR-005**: The system MUST compute `recency` as exactly 1.0 for an `open` finding,
  `0.5^(days_since_resolved / half_life_days)` for a `resolved` finding, and
  `min(1.0 + 0.08 × overdue_ratio, 2.0)` for an `open_overdue` finding, where
  `overdue_ratio = (elapsed_business_hours − threshold_business_hours) /
  threshold_business_hours` (REQ-M6-09..12, REQ-M6-CAL-01/02).
- **FR-006**: The system MUST allow positive findings — `finding_type = commitment_met`,
  the one seeded type matching REQ-M6-13's positive-signal examples (milestones met,
  successful reviews) — to subtract points from the total, capped at 25% of accumulated
  negative severity for that run; every other seeded `finding_type` is negative
  (REQ-M6-13/14, REQ-M6-P3).
- **FR-007**: The system MUST convert total points to a 0–100 score via `100 × (1 −
  e^(−points/33))`, which MUST never reach exactly 100 (REQ-M6-15/16).
- **FR-008**: The system MUST classify score `< 35` as `healthy`, `35 ≤ score < 65` as
  `watch`, and `score ≥ 65` as `at_risk`, applying a hysteresis gap (65 enter / 55 exit
  for `at_risk`) and requiring the qualifying score to hold across two consecutive
  scoring runs — of any trigger type — before the displayed band changes (REQ-M6-17..19,
  REQ-M6-CAL-07).
- **FR-009**: The system MUST recompute every score from zero on every run, never using
  the previous score as an input (REQ-M6-20, REQ-M6-P2).
- **FR-010**: The system MUST recompute on an hourly heartbeat, and MUST trigger a full
  recompute when a client profile edit's replay completes (REQ-M6-24/25).
- **FR-011**: The system MUST freeze the score at its last value and mark the run as
  degraded when a required source's coverage is incomplete, rather than computing on
  incomplete data as if it were complete (REQ-M6-26, REQ-NFR-32).
- **FR-012**: The system MUST compute `stakes = contract_value_multiplier ×
  renewal_proximity_factor` as a value separate from the score, never folded into the
  score itself, used only for sorting/ranking purposes (REQ-M6-27/28). New seed-default
  constants pinned by this feature (2026-08-14 clarification — no prior calibration
  existed for this formula, unlike every other scoring number): `contract_value_
  multiplier` reuses the existing `criticality_multiplier` scale (`strategic` = 1.5,
  `standard` = 1.0, `smb` = 0.6); `renewal_proximity_factor = clamp(2.0 −
  (days_until_renewal / 90), 0.5, 2.0)` — renewal today or overdue clamps to the 2.0
  maximum, renewal 180+ days out clamps to the 0.5 floor, 90 days out is exactly the
  1.0 baseline.
- **FR-013**: The system MUST persist `score_runs`, `score_contributions` (one row per
  finding, decimal-exact), and `band_history` for every run (data-base/06-schema-
  scoring.md).
- **FR-014**: The system MUST NEVER call a language model anywhere in the scoring
  computation path (REQ-M6-P1) — enforced by the existing `.importlinter` `scoring-
  domain-purity` contract and AST check (feature 001).
- **FR-015**: Adding any single validated negative finding to an existing state MUST
  NEVER decrease the resulting score, for any existing state (REQ-M6-P4, REQ-NFR-31).
- **FR-016**: `score_contributions.points_contributed`, summed per run and split by
  `is_positive`, MUST reconcile exactly (to the full stored decimal precision) with
  `score_runs.total_negative_points`/`total_positive_points` (REQ-NFR-30).

### Key Entities

No new tables — `findings`, `finding_type_config`, `issues`, `finding_issue_map`,
`quarantine` (`data-base/05-schema-reasoning.md`); `score_runs`, `score_contributions`,
`band_history` (`data-base/06-schema-scoring.md`) all already exist from feature 001's
migration. This feature is the first to read the former (via a hand-authored fixture)
and write the latter for real.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A skeptical reader can reproduce every `score_contributions` value and
  the final score by hand, using only a calculator and the published worked example —
  100% of the fixture's 9 findings match to the decimal.
- **SC-002**: Score contributions reconcile exactly to the run's totals for every
  scoring run produced anywhere in the test suite, including randomly generated cases,
  not just the hand-worked example (property-based testing, thousands of generated
  cases per run).
- **SC-003**: Adding any single negative finding to any existing, valid scoring state
  never produces a lower score — verified across thousands of randomly generated cases,
  not just the hand-worked example.
- **SC-004**: A band label changes at most once every two scoring runs, never on a
  single-run score fluctuation within the hysteresis gap.
- **SC-005**: No language-model call exists anywhere in the scoring engine's code path,
  verified by static/dependency analysis on every change.
- **SC-006**: Replaying an identical ledger, profile version, weight version, and
  damping state twice yields an identical score, to the decimal, 100% of the time.

## Assumptions

- Findings for this feature are hand-authored/fixture-seeded, matching build-order
  Phase 4's own "hand-written findings" framing — real reader-produced findings arrive
  in feature 005, and the validation gate that would normally set `status = validated`
  arrives in feature 007. This feature inserts its fixture findings directly with
  `status = validated`, honestly labeled as a fixture rather than gate output.
- Issue groupings (`issues`, `finding_issue_map`) are likewise fixture data for this
  feature — the Recurrence reader's clustering algorithm (feature 005) will produce
  these automatically once it exists; this feature's rank-within-issue arithmetic
  operates correctly regardless of how a grouping was produced.
- Only `manual`, `hourly_heartbeat`, and `profile_edit_replay` triggers have real
  callers in this feature. `new_event`, `burst_batch`, and `urgent_fast_path` require a
  live reader pipeline (features 005/007); `weight_edit_replay` has no caller until a
  weight-editing capability exists (Post-MVP, `decisions/00-open-questions-
  resolved.md` Q4).
- This feature does not expose any new API route — `GET /api/dashboard` (feature 006)
  is the first and only consumer-facing surface for score data.
- Damping is computed via the real formula against the real `damping_weights` table,
  which currently has no rows (no feedback verdict has ever been submitted, feature
  010) — every lookup in this feature's own demo state therefore returns the undamped
  default (1.0), which is itself the correct, honest behavior for an account with no
  feedback history yet.
- `stakes`'s constants (FR-012) are a new seed default this feature introduces, the
  same status as `finding_type_config`'s seeded weights (`decisions/00-open-questions-
  resolved.md` Q4) — reasonable and defensible now, replaceable later without an
  architecture change, only a constant edit and a replay.
- Positive-vs-negative finding classification (FR-006) is inferred, not published
  anywhere as a formal flag — no `is_positive`/sign column exists on `findings` or
  `finding_type_config`. `commitment_met` is the only one of the 9 seeded types that
  semantically matches REQ-M6-13's positive-signal examples, and it's exactly the type
  `examples/01` §9.4's `fnd-9` (ticket #398 resolved fast) uses. A future reader-added
  finding type would need this classification decided the same way (a small, explicit
  lookup, not inferred from a database column) — the same "small config table
  maintained separately from client data" pattern `data-base/04-schema-context.md`'s
  Notes section already establishes for multiplier categories.
