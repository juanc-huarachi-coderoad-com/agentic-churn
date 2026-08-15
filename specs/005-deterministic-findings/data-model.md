# Data Model: Deterministic Findings

No new tables — every entity below already exists (`data-base/03-schema-ledger.md`,
`data-base/05-schema-reasoning.md`, feature 001's migration). This document maps
this feature's five readers to the rows they read and write, and works the exact
values `tests/readers/test_run_readers_use_case.py` asserts against.

## Entities this feature reads

- **`events`** (`data-base/02-schema-ledger.md`) — the raw material every reader
  interprets. Commitment reads via `response_pairs`, not `events` directly; Usage
  reads `usage_measurement`/`survey_response` events; Recurrence reads
  `ticket_state_change` titles; Absence reads `absence`-type events; Relationship
  reads participant identity across all event types.
- **`response_pairs`** (`data-base/03-schema-ledger.md`) — already computed by
  feature 003's `ReplayUseCase`. Commitment reads `state`/`business_hours_elapsed`/
  `threshold_business_hours` directly, the same columns feature 004's
  `resolve_lifecycle` already reads for a different purpose (ageing, not
  finding-emission).
- **`client_profile_versions`**/`stakeholders`/`commitments`
  (`data-base/04-schema-context.md`) — Commitment reads the current profile's
  commitment thresholds (already resolved into `response_pairs.threshold_
  business_hours` by replay, so no separate lookup needed); Relationship reads the
  stakeholder list to diff against.

## Entities this feature writes

### `rollups` (first real writer — REQ-M2-06, deferred since feature 003)

| Field | Source |
|---|---|
| `subject_type` / `subject_id` | The metric's owner — `product_area` for `tracking_api` usage, `account` for CSAT |
| `metric` | e.g. `weekly_active_usage`, `csat_score` |
| `value` | The metric's `value_delta_pct` reading for one window's sample — not a separate absolute value; the real `warehouse` event schema (`simulated_collector.py`) only carries a delta, and a delta series is still a valid numeric series to compute a mean/stddev/z-score over (`research.md`'s Decision, revised during `/speckit-analyze`) |
| `is_baseline` | Always `false` — this feature computes, never confirms (`spec.md`'s scope boundary) |

`ComputeRollupsUseCase` truncates and rebuilds this table's rows for the metrics/
subjects the Usage reader consumes, from `events` alone — the same "projection,
rebuildable from `events`" shape `event_threads`/`response_pairs` already have
(`data-base/01-database-overview.md`'s Principle 3), just newly implemented.

### `findings` (first real, non-fixture writer)

Every reader writes `status = pending_validation`, `state = NULL` (set later by
the scoring engine, feature 004's own precedent — this feature never sets it).

## Worked example — reproducing `examples/01` §6

Matching `examples/01-end-to-end-walkthrough.md` §6's worked findings — this is
`spec.md`'s SC-001, restated here as the concrete values a test asserts against.
`confidence`/`magnitude` use this feature's own formulas (`research.md`'s
Decisions), not `examples/01`'s illustrative hand-picked numbers — SC-001 only
requires `finding_type`/`cited_event_ids` to match exactly (five of six exactly,
`fnd-2` with a corrected, broader citation — see below).

| Finding | Reader | `finding_type` | Formula | Value |
|---|---|---|---|---|
| `fnd-1` | Commitment | `broken_response_promise` | `confidence = 1.0`; `magnitude = min(overdue_ratio, 1.0)` where `overdue_ratio = (19−4)/4 = 3.75` | `magnitude = 1.00`, `confidence = 1.00` — matches `examples/01` exactly, since the ratio already saturates the clamp |
| `fnd-9` | Commitment | `commitment_met` | `confidence = 1.0`; `magnitude = 1.0 − (elapsed/threshold) = 1.0 − (2/4)` | `magnitude = 0.50`, `confidence = 1.00` — `examples/01` publishes `0.40`; this feature's formula-derived value differs, which SC-001 doesn't require to match |
| `fnd-4` | Absence | `contact_absence` | `confidence = 0.85` fixed; `magnitude = min(silence_days / (2 × cadence_days), 1.0)`, both derived from the real event's own `window_start`/`last_contact_at`/`occurred_at` (`research.md`'s Decision, corrected during implementation — the real payload has no `missed_count` field) | Exact value depends on the real absence event's timing when the reader actually runs — verified at `quickstart.md` validation time, not hand-computed here (same treatment as `fnd-3` originally received); `confidence = 0.85` matches `examples/01`'s illustrative value regardless |
| `fnd-5` | Relationship | `relationship_change` | `confidence = 0.7` fixed; `magnitude = 0.5` fixed (reduced-strength signal, `research.md`'s Decision) | `magnitude = 0.50`, `confidence = 0.70` — confidence matches `examples/01` exactly |
| `fnd-2` | Recurrence | `recurring_issue` | `confidence` = HDBSCAN's own cluster-membership probability for this point; `magnitude = min((cluster_size−1)/3.0, 1.0)` where `cluster_size = 2` | `magnitude = 0.33`; `confidence` verified at implementation time (depends on the real embedding vectors for "Slow API response" appearing twice — expected high, near 1.0, given the two titles are textually identical) |
| `fnd-3` | Usage | `usage_deviation` | z-score of `w34`'s `value_delta_pct = -22` against the 5 historical readings' (`w29`..`w33`: `-2, 1, -3, 2, -1`) sample mean (`-0.6`) and sample stddev (`≈2.074`) | `z ≈ -10.32` — decisively beyond `|z| > 2`. Historical readings added during `/speckit-analyze` (`research.md`'s Decision) — the fixture originally had only one warehouse event, which could never clear FR-008's 3-sample floor |

**`fnd-2`'s citation, corrected**: `examples/01`'s published `fnd-2` cites only
`[evt-2]` (ticket #456's reopened event alone) — a narrative shorthand reading the
event's own `reopen_count` field. This feature's real clustering-based
implementation cites **two** real events — ticket #456's original creation
(`zendesk-456-created`, a new fixture event this feature adds, `research.md`'s
Decision) and its reopening (`zendesk-456-reopened`, already real since feature
003) — because a cluster of size 1 cannot exist. `finding_type` is unchanged;
only the citation is broader, which is *more* evidence, not less (REQ-M5-05).

## Validation

- **Per-reader unit tests**: each reader's pure decision logic (Commitment's
  threshold comparison, Usage's z-score, Absence's missed-count scaling,
  Relationship's fixed-value reduced-strength signal) is tested with plain values,
  no database — mirroring feature 004's domain-service testing pattern.
- **Real-DB integration test** (`test_run_readers_use_case.py`): runs all five
  readers against the real, already-ingested Meridian ledger (plus the new
  `zendesk-456-created` fixture event) and asserts the worked-example table above.
- **Cache/idempotency**: re-running `RunReadersUseCase` against an unchanged
  ledger produces zero additional findings (REQ-M5-15, SC-003).
- **Failure isolation**: a forced Recurrence failure (e.g. an invalid
  `OPENAI_API_KEY`) still leaves the other four readers' findings persisted
  (FR-014a).
