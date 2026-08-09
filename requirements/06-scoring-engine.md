# 06 · Scoring engine (M6)

Tier 3 · Reasoning — spec §7 (M6), §8 (full scoring model)

## Purpose

Findings in, number out. Deliberately unintelligent: plain arithmetic a person can verify on paper. No model call exists anywhere in this component (P2).

## User stories

- As a **CS lead**, I want to verify the score's arithmetic on paper, so that I stop questioning the number and start using it.
- As a **CS lead**, I want the score to never reach 100, so that a bad situation always visibly has room to get worse.
- As a **CS lead**, I want the band label to resist wobbling, so that I'm not notified every time the score crosses 65 by one point.

## Functional requirements

### Per-finding weight

| ID | Requirement |
|---|---|
| REQ-M6-01 | THE SYSTEM SHALL compute each finding's `points` as `base × influence × criticality × confidence × magnitude × recency × damping`, using only deterministic arithmetic — no model call anywhere in this computation. |
| REQ-M6-02 | `base` SHALL come from a versioned per-finding-type configuration table, not from the finding itself. |
| REQ-M6-03 | `influence` and `criticality` SHALL come from the client profile version recorded on the run (REQ-M3-05). |
| REQ-M6-04 | `confidence` and `magnitude` SHALL come directly from the finding (REQ-M5-02/03), unmodified. |
| REQ-M6-05 | `damping` SHALL come from feedback memory (REQ-M4-03) and SHALL always be ≤ 1.0. |

### Grouping into issues

| ID | Requirement |
|---|---|
| REQ-M6-06 | THE SYSTEM SHALL cluster findings sharing one underlying cause into an **issue** (using the Recurrence reader's clustering plus shared entity/time heuristics). |
| REQ-M6-07 | Within one issue, THE SYSTEM SHALL apply diminishing weight by rank: 1st finding 100%, 2nd 60%, 3rd 36%, 4th 22%, continuing the same ratio (0.6ⁿ) for further findings. |
| REQ-M6-08 | Across different issues, THE SYSTEM SHALL count each issue's contribution in full — breadth is never discounted, only repetition within one issue. |

### Time and recency

| ID | Requirement |
|---|---|
| REQ-M6-09 | A finding in `resolved` state SHALL fade according to a per-finding-type half-life. |
| REQ-M6-10 | A finding in `open` state SHALL NOT fade at all. |
| REQ-M6-11 | A finding in `open_overdue` state SHALL gain an ageing multiplier that increases `recency` above 1.0. |
| REQ-M6-12 | THE SYSTEM SHALL NEVER apply blanket time decay to an open, unresolved finding — decay applies only to the resolved state. |

### Positive signals

| ID | Requirement |
|---|---|
| REQ-M6-13 | THE SYSTEM SHALL allow positive findings (milestones met, successful reviews, active champions, executive engagement) to subtract points from the total. |
| REQ-M6-14 | Total positive-signal subtraction SHALL be capped at 25% of accumulated negative severity for that run — positive signals reduce, but never zero out, negative evidence. |

### Points → score

| ID | Requirement |
|---|---|
| REQ-M6-15 | THE SYSTEM SHALL convert total points to a 0–100 score via `score = 100 × (1 − e^(−points / 33))`. |
| REQ-M6-16 | THE SYSTEM SHALL NEVER allow the score to reach exactly 100 (property of the saturating exponential — must not be clamped/rounded to 100). |

### Bands and hysteresis

| ID | Requirement |
|---|---|
| REQ-M6-17 | THE SYSTEM SHALL classify score < 35 as `Healthy`, 35 ≤ score < 65 as `Watch`, and score ≥ 65 as `At risk`. |
| REQ-M6-18 | WHEN the band is `At risk`, THE SYSTEM SHALL NOT demote it to `Watch` until the score falls below 55 (hysteresis gap between 65 enter / 55 exit). |
| REQ-M6-19 | A band change (in either direction) SHALL require the qualifying score to hold across two consecutive scoring runs before the displayed band changes. |

### Recomputation

| ID | Requirement |
|---|---|
| REQ-M6-20 | THE SYSTEM SHALL recompute the score from zero on every run — the previous score SHALL NEVER be an input to the new calculation. |
| REQ-M6-21 | WHEN a single new event arrives, THE SYSTEM SHALL recompute the score within ~40 seconds end to end. |
| REQ-M6-22 | WHEN multiple events arrive close together, THE SYSTEM SHALL batch them into a 30-second window and issue one recompute, not one per event. |
| REQ-M6-23 | WHEN an urgent phrase is detected (Intent reader, closed enumeration), THE SYSTEM SHALL recompute immediately, skipping the batch window. |
| REQ-M6-24 | THE SYSTEM SHALL recompute on an hourly heartbeat regardless of new events, because recency/ageing terms change with time alone. |
| REQ-M6-25 | WHEN the client profile or a base-weight configuration changes, THE SYSTEM SHALL trigger a full replay and recompute (per REQ-M2-07/REQ-M3-06). |
| REQ-M6-26 | IF a required source is degraded/disconnected during a run, THEN THE SYSTEM SHALL freeze the score at its last value and display a visible staleness warning rather than compute on incomplete data as if it were complete. |

### Risk vs. stakes

| ID | Requirement |
|---|---|
| REQ-M6-27 | THE SYSTEM SHALL keep renewal proximity and contract value **out of** the score formula — the score reflects relationship evidence only. |
| REQ-M6-28 | THE SYSTEM SHALL compute a separate **stakes** value (renewal proximity × contract value band) for prioritization/display, and SHALL multiply score × stakes only for sorting/ranking purposes, never write the multiplied value back as "the score." |

## Explicit prohibitions

| ID | Prohibition |
|---|---|
| REQ-M6-P1 | THE SCORING ENGINE SHALL NEVER call a language model. |
| REQ-M6-P2 | THE SCORING ENGINE SHALL NEVER use the previous score as an input to the current calculation. |
| REQ-M6-P3 | THE SCORING ENGINE SHALL NEVER let a positive finding reduce the score by more than the 25% cap. |
| REQ-M6-P4 | Adding a negative finding SHALL NEVER lower the score (monotonicity — spec §14.3). |

## Inputs / Outputs

- **Input:** validated findings (M5a), base-weight config, client profile multipliers (M3), damping weights (M4).
- **Output:** `score_runs`, `score_contributions` (per-finding/issue breakdown, decimal-exact), `band_history` — consumed by M7 (Narrator), M8 (dashboard), M9 (ask agent lookups).

## Non-functional constraints

- Determinism: identical inputs (ledger + profile version + weight version + damping state) must always produce an identical score (spec §9.4).
- Score contributions must reconcile to the total **to the decimal** (spec §14.3).

## Acceptance criteria

- [ ] Score contributions sum exactly to the total displayed score's point total, to the decimal.
- [ ] Adding any single negative finding never decreases the resulting score, for any existing state (monotonicity test).
- [ ] A band never flips on a one-run wobble across the hysteresis band.
- [ ] No model/API call is present in the scoring engine's code path (verified by static/dependency check).
- [ ] Replaying identical ledger + profile + weights + damping state twice yields an identical score.

## Traceability

Spec §7 M6, §8.1–§8.9 (full scoring model), §10 (worked arithmetic example), §14.3 (engineering acceptance criteria).
