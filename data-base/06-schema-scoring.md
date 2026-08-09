# 06 · Schema — Scoring (M6)

See `requirements/06-scoring-engine.md`. These tables must reconcile to the decimal (REQ-NFR-30).

## `score_runs`

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

## `score_contributions`

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

## `band_history`

Display-only trend/notification/stickiness support (spec §8.7 — history is not a scoring input, but is used for these four things).

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `score_run_id` | UUID FK → `score_runs.id` | |
| `band` | ENUM(`healthy`,`watch`,`at_risk`) | |
| `consecutive_runs_in_band` | INTEGER | Used to enforce the two-consecutive-run stickiness rule (REQ-M6-19) |
| `notified` | BOOLEAN | Whether this band change triggered a notification |
| `created_at` | TIMESTAMPTZ | |

## Notes

- `SUM(score_contributions.points_contributed) = score_runs.total_negative_points - score_runs.total_positive_points-excluded-rows` is the exact reconciliation check behind REQ-NFR-30 — implemented as an automated test that runs after every scoring pipeline change.
- `damping NUMERIC(4,3) CHECK (damping <= 1.000)` enforces REQ-M6-P3 at the schema level, not just in application logic.
- `score_runs.score` never reaches 100.00 in practice because of the asymptotic formula (REQ-M6-16) — no additional `CHECK` is needed, but a test asserts this over a wide input range.
