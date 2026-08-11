# 06 · Schema — Scoring (M6)

See `requirements/06-scoring-engine.md`. These tables must reconcile to the decimal (REQ-NFR-30). Examples below are the exact numbers computed in `examples/01-end-to-end-walkthrough.md` §9 — read that section alongside this one if you want to see the arithmetic worked out by hand first.

**Why this schema exists, in plain terms:** every table before this one produced *inputs* — facts, opinions, weights. This is where those inputs turn into the one number a person actually looks at. Nothing here calls a language model; it's the one part of the whole system that is deliberately, strictly a calculator.

## `score_runs`

**In plain terms:** one row per "the system recomputed the score." It always starts from zero and adds up everything currently true — it never nudges last time's number up or down.

One row per scoring recomputation.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `trigger` | ENUM(`new_event`,`burst_batch`,`urgent_fast_path`,`hourly_heartbeat`,`profile_edit_replay`,`weight_edit_replay`,`manual`) | Which REQ-M6-2x trigger fired this run |
| `profile_version_id` | UUID FK → `client_profile_versions.id` | Exact context version used (REQ-M3-05) |
| `finding_type_config_version` | TEXT | Which weight config version was used |
| `total_negative_points` | NUMERIC(10,3) | Sum before the positive-signal cap |
| `total_positive_points` | NUMERIC(10,3) | Raw positive-signal sum, before the 25% cap is applied |
| `positive_points_applied` | NUMERIC(10,3) | `MIN(total_positive_points, 0.25 * total_negative_points)` (REQ-M6-14) |
| `total_points` | NUMERIC(10,3) | `total_negative_points - positive_points_applied` |
| `score` | NUMERIC(5,2) | `100 * (1 - e^(-total_points/33))` (REQ-M6-15) |
| `band` | ENUM(`healthy`,`watch`,`at_risk`) | Displayed band, after hysteresis (REQ-M6-17..19) |
| `raw_band` | ENUM(`healthy`,`watch`,`at_risk`) | Band the raw score alone would imply, before hysteresis — kept for debugging |
| `stakes` | NUMERIC(6,3) NULL | Renewal proximity × contract value band, computed but never folded into `score` (REQ-M6-27/28) |
| `source_degraded` | BOOLEAN | TRUE if computed while a required source was disconnected (drives REQ-NFR-32 visual distinction) |
| `is_frozen` | BOOLEAN | TRUE if this run is a carried-forward frozen value, not a fresh computation (REQ-M6-26) |
| `computed_at` | TIMESTAMPTZ | |

**Example row** — the run that produced the worked example's final answer:

| id | trigger | total_negative_points | total_positive_points | positive_points_applied | total_points | score | band |
|---|---|---|---|---|---|---|---|
| `run-score-1` | `burst_batch` | 67.310 | 4.000 | 4.000 | 63.310 | **85.30** | `at_risk` |

Read left to right: 67.31 points of real problems, 4.00 points of genuine goodwill (well under the 25%-of-negative cap, so it applies in full), netting to 63.31 total points, which the saturating formula converts to a score of 85.30 out of a ceiling that never quite reaches 100.

## `score_contributions`

**In plain terms:** the itemized receipt behind the total — one row per finding, showing every single multiplier that went into its final point value. If you ever want to check the score's arithmetic by hand, this is the table you'd export.

Per-finding line items — must sum exactly to `score_runs.total_points`.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `score_run_id` | UUID FK → `score_runs.id` | |
| `finding_id` | UUID FK → `findings.id` | |
| `issue_id` | UUID FK → `issues.id`, NULL | NULL for standalone findings |
| `base` | NUMERIC(8,3) | |
| `influence` | NUMERIC(4,3) | |
| `criticality` | NUMERIC(4,3) | |
| `confidence` | NUMERIC(4,3) | |
| `magnitude` | NUMERIC(4,3) | |
| `recency` | NUMERIC(4,3) | |
| `damping` | NUMERIC(4,3) | Always ≤ 1.000 (REQ-M6-05, REQ-M6-P3 enforced by `CHECK`) |
| `rank_within_issue_factor` | NUMERIC(4,3) | 1.000 / 0.600 / 0.360 / 0.220 … (REQ-M6-07) |
| `points_contributed` | NUMERIC(8,3) | `base * influence * criticality * confidence * magnitude * recency * damping * rank_within_issue_factor` |
| `is_positive` | BOOLEAN | TRUE for milestone/goodwill findings |

**Example rows** — two contrasting line items from `run-score-1`:

| finding_id | base | influence | criticality | confidence | magnitude | recency | damping | rank_factor | points_contributed |
|---|---|---|---|---|---|---|---|---|---|
| `fnd-1` (broken promise, ticket #456) | 20.000 | 1.000 | 1.500 | 1.000 | 1.000 | 1.300 | 1.000 | 1.000 | **39.000** |
| `fnd-7` (Ana's escalation language) | 14.000 | 1.600 | 1.000 | 0.850 | 0.500 | 1.000 | 1.000 | 1.000 | **9.520** |

`fnd-1`'s `recency = 1.300` is the "open and overdue" ageing multiplier in action — the ticket is still unresolved, so the clock keeps working against it rather than fading. `fnd-7`'s `influence = 1.600` is Ana's sponsor multiplier, carried straight through from `data-base/04-schema-context.md`'s `stakeholders` table into this exact row.

Summing every row's `points_contributed` for `run-score-1` (nine rows total, one of them negative because `is_positive = true`) reproduces `score_runs.total_points = 63.310` exactly — this is the decimal-exact reconciliation required by REQ-NFR-30, and it's what lets a skeptical CS lead check the number with a calculator instead of taking it on faith.

## `band_history`

**In plain terms:** the memory of which band the account has been in, run after run — used only for display and for the "don't flip the label on a one-run wobble" rule (hysteresis), never as an input to the score itself.

Display-only trend/notification/stickiness support (spec §8.7 — history is not a scoring input, but is used for these four things).

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `score_run_id` | UUID FK → `score_runs.id` | |
| `band` | ENUM(`healthy`,`watch`,`at_risk`) | |
| `consecutive_runs_in_band` | INTEGER | Used to enforce the two-consecutive-run stickiness rule (REQ-M6-19) |
| `notified` | BOOLEAN | Whether this band change triggered a notification |
| `created_at` | TIMESTAMPTZ | |

**Example row:**

| score_run_id | band | consecutive_runs_in_band | notified |
|---|---|---|---|
| `run-score-1` | `at_risk` | 2 | **true** |

`consecutive_runs_in_band = 2` is why the dashboard is allowed to actually *show* "At risk" rather than holding at "Watch" for one more run — the account had already crossed 65 the run before this one, so this second high run confirms it (see `sequences/06-state-band-hysteresis.md` for the full state diagram).

## Notes

- `SUM(score_contributions.points_contributed)` for a given `score_run_id`, split by `is_positive`, reproduces `score_runs.total_negative_points` and `score_runs.total_positive_points` exactly — this is the reconciliation check behind REQ-NFR-30, implemented as an automated test that runs after every scoring pipeline change.
- `damping NUMERIC(4,3) CHECK (damping <= 1.000)` enforces REQ-M6-P3 at the schema level, not just in application logic.
- `score_runs.score` never reaches 100.00 in practice because of the asymptotic formula (REQ-M6-16) — no additional `CHECK` is needed, but a test asserts this over a wide input range.
