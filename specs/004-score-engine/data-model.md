# Data Model: Score Engine

## No new tables

Every table this feature touches already exists from feature 001's migration:
`findings`, `finding_type_config`, `issues`, `finding_issue_map`, `quarantine`
(`data-base/05-schema-reasoning.md`); `score_runs`, `score_contributions`,
`band_history` (`data-base/06-schema-scoring.md`). This feature is the first to read
the former (via a hand-authored fixture, not reader output) and write the latter for
real.

## New domain entities (`scoring/domain/entities.py`)

Per `architecture/09-clean-architecture-and-patterns.md`'s already-named pattern
catalog — defined once, here, since `scoring.domain` owns `Finding`'s lifecycle (the
scoring engine is what sets `state`, per `data-base/05`'s own schema comment). Future
modules (`readers`) will re-export these, not redefine them.

| Entity | Fields (beyond the schema's own columns — no restatement) | Notes |
|---|---|---|
| `Finding` | Mirrors `findings` row exactly | `state` starts `None` until scored |
| `Issue` | Mirrors `issues` row | |
| `ScoreRun` | Mirrors `score_runs` row | |
| `ScoreContribution` | Mirrors `score_contributions` row | |

## The fixture: `demo/fixtures/score-engine-findings.json` + `scripts/seed_score_fixture.py`

Reproduces `examples/01-end-to-end-walkthrough.md` §9's exact 9-finding worked example.
Prerequisite: `scripts/run_collector.py` has already run (real MVP-source events exist
in the ledger) — the seed script queries those real events for six of nine citations,
calls `DetectAbsenceUseCase` for a seventh, and inserts one synthetic `survey_response`
event (CSAT, no live collector exists yet) for the last two (`research.md`'s Decision).

### Findings

| id | reader_type | finding_type | magnitude | confidence | cited event (real, resolved at seed time) | stakeholder | product_area |
|---|---|---|---|---|---|---|---|
| `fnd-1` | `commitment` | `broken_response_promise` | 1.00 | 1.00 | ticket `#456` reopened event | *(none)* | `tracking_api` |
| `fnd-2` | `recurrence` | `recurring_issue` | 0.60 | 0.75 | ticket `#456` reopened event (same root cause) | *(none)* | `tracking_api` |
| `fnd-3` | `usage` | `usage_deviation` | 0.55 | 0.90 | `tracking_api` usage-measurement event | *(none)* | `tracking_api` |
| `fnd-4` | `absence` | `contact_absence` | 0.70 | 0.85 | the real `absence`-type event (`DetectAbsenceUseCase`) | Diego | *(none)* |
| `fnd-5` | `relationship` | `relationship_change` | 0.40 | 0.70 | the same real `absence`-type event | Diego | *(none)* |
| `fnd-6` | `tone` | `tone_deterioration` | 0.60 | 0.80 | Ana's first Gmail `message` event | Ana | *(none)* |
| `fnd-7` | `intent` | `escalation_language` | 0.50 | 0.85 | the same Gmail `message` event | Ana | *(none)* |
| `fnd-8` | `usage` | `csat_deviation` | 0.50 | 0.95 | the synthetic `survey_response` event | Ana | *(none)* |
| `fnd-9` | `commitment` | `commitment_met` *(positive)* | 0.40 | 1.00 | ticket `#398` resolved event | *(none)* | `reporting` |

All nine inserted with `status = 'validated'` (the validation gate, feature 007,
doesn't exist yet — see `spec.md`'s Assumptions) and `state = NULL` (set by
`RecomputeScoreUseCase` on the first run — `research.md`'s Decision).

### Issue groupings (`finding_issue_map` — `(finding_id, issue_id)` pairs only)

> **2026-08-21 note.** Doubly confirmed since this was written: `IssueGrouper`
> (`app/scoring/domain/services.py`) only *ranks* findings that already have
> a `finding_issue_map` row — it never creates membership. No use case,
> background job, or reader anywhere in this codebase writes a new
> `issues`/`finding_issue_map` row; the seed data below (and `backend/
> scripts/seed_score_fixture.py`, which loads it) remains the only source
> either table has ever had. `specs/009-draft-composer/contracts/drafts.md`'s
> Amendment stopped the Draft Composer from depending on this; a real
> finding-to-issue clustering effort is still an open, unbuilt feature.

| issue | label | cluster_method | findings |
|---|---|---|---|
| `iss-A` | Issue A — tracking_api reliability | `shared_entity` | `fnd-1`, `fnd-2`, `fnd-3` |
| `iss-B` | Issue B — Ana & Diego disengaging | `embedding_similarity` | `fnd-7`, `fnd-4`, `fnd-6`, `fnd-8`, `fnd-5` |

`fnd-9` belongs to no issue (Edge Cases: a standalone finding scores at
`rank_within_issue_factor = 1.000`, never penalized for not being clustered).
`rank_within_issue` itself is **not** seeded — `IssueGrouper` computes and upserts it
on every run, sorted by raw points descending within each `issue_id` (`research.md`'s
Decision).

## Worked arithmetic

Matching `examples/01-end-to-end-walkthrough.md` §9 exactly — this is `spec.md` User
Story 1's acceptance criteria, restated here as the concrete numbers a test asserts
against.

**Issue A** (rank by raw points — `base × influence × criticality × confidence ×
magnitude`, recency excluded — descending: `fnd-1` = 20×1.0×1.5×1.00×1.00 = **30.00**,
`fnd-3` = 15×1.0×1.5×0.90×0.55 = **11.1375**, `fnd-2` = 12×1.0×1.5×0.75×0.60 =
**8.10** → `fnd-1` 1st, `fnd-3` 2nd, `fnd-2` 3rd):

| Finding | base | influence | criticality | confidence | magnitude | recency | rank factor | points |
|---|---|---|---|---|---|---|---|---|
| `fnd-1` | 20 | 1.0 | 1.5 | 1.00 | 1.00 | 1.30 | 1.00 (1st) | **39.00** |
| `fnd-3` | 15 | 1.0 | 1.5 | 0.90 | 0.55 | 1.00 | 0.60 (2nd) | **6.6825** |
| `fnd-2` | 12 | 1.0 | 1.5 | 0.75 | 0.60 | 1.00 | 0.36 (3rd) | **2.916** |
| | | | | | | | **Issue A total** | **48.5985** |

**A correction to `examples/01` §9.2, found during `/speckit-analyze`**: that document
(and `data-base/05-schema-reasoning.md`'s own example rows) publish `fnd-2` at rank 2
and `fnd-3` at rank 3 — but `fnd-3`'s raw point value (11.1375) is higher than
`fnd-2`'s (8.10) under the stated rule itself ("ranked by how much raw weight each
carries," `data-base/05`). The published rank order doesn't match the rule it claims to
follow — a genuine authoring inconsistency in the upstream worked example, not a
design choice this feature needs to accommodate. `IssueGrouper` implements the rule
correctly and generally (no fixture-specific exception, no hardcoded issue IDs) — the
numbers above are what that correct implementation produces, and are this feature's
actual acceptance criteria, superseding `examples/01` §9.2's published `fnd-2`/`fnd-3`
values for this fixture. `examples/01` itself is unaffected by this feature's scope —
correcting that document is a separate, later concern if anyone chooses to.

**Issue B** (rank order matching `data-base/05`'s own example rows and `examples/01`
§9.3 exactly: `fnd-7` 1st, `fnd-4` 2nd, `fnd-6` 3rd, `fnd-8` 4th, `fnd-5` 5th):

| Finding | base | influence | criticality | confidence | magnitude | recency | rank factor | points |
|---|---|---|---|---|---|---|---|---|
| `fnd-7` | 14 | 1.6 | 1.0 | 0.85 | 0.50 | 1.00 | 1.00 (1st) | **9.52** |
| `fnd-4` | 12 | 1.2 | 1.0 | 0.85 | 0.70 | 1.00 | 0.60 (2nd) | **5.1408** |
| `fnd-6` | 10 | 1.6 | 1.0 | 0.80 | 0.60 | 1.00 | 0.36 (3rd) | **2.7648** |
| `fnd-8` | 10 | 1.6 | 1.0 | 0.95 | 0.50 | 1.00 | 0.216 (4th) | **1.6416** |
| `fnd-5` | 8 | 1.2 | 1.0 | 0.70 | 0.40 | 1.00 | 0.1296 (5th) | **0.3484** |
| | | | | | | | **Issue B total** | **19.4156** |

Raw points *do* descend in this exact order (`fnd-7` = 14×1.6×0.85×0.50 = 9.52 down to
`fnd-5` = 8×1.2×0.70×0.40 = 2.688), so Issue B's rank assignment reproduces mechanically
from "raw points descending" with no correction needed — only Issue A's published
order in `examples/01` had the inconsistency noted above.

**Standalone positive** (`rank_within_issue_factor = 1.000`, no issue):

| Finding | base | influence | criticality | confidence | magnitude | recency | points |
|---|---|---|---|---|---|---|---|
| `fnd-9` | 10 | 1.0 | 1.0 | 1.00 | 0.40 | 1.00 | **4.00** |

**Totals** (full precision — the two Issue tables above round each rank factor to 4
decimals for readability, but rank_within_issue_factor is a true `0.6**n` power with
no rounding in the actual implementation; these totals use the unrounded values):

```
total_negative_points = 48.5985 + 19.4155648 = 68.0140648
cap = 25% of 68.0140648 = 17.0035162
positive_points_applied = min(4.000, 17.0035162) = 4.000
total_points = 68.0140648 - 4.000 = 64.0140648
score = 100 * (1 - e^(-64.0140648/33)) = 85.627
band: score >= 65 -> raw_band = at_risk
```

`score_runs` stores `total_negative_points`/`total_points` as `NUMERIC(10,3)`
(68.014 / 64.014) and `score` as `NUMERIC(5,2)` (85.63) — see
`backend/tests/scoring/test_worked_example.py` for the exact per-finding figures a
real `RecomputeScoreUseCase` run reproduces to the decimal.

`band_history` for this fixture's second consecutive run at this score level shows
`consecutive_runs_in_band = 2`, `band = at_risk` (displayed) — matching `examples/01`
§9's own framing that "this account was already at 70+ last week," i.e. the worked
example's `score_runs` row is not this fixture's *first* run. The quickstart's
validation sequence runs the fixture through `RecomputeScoreUseCase` twice
consecutively to reach this same confirmed state deterministically, rather than
requiring a real week of elapsed time.

## `stakes` worked check (FR-012, this feature's new seed constants)

Meridian's `contract_value_band = strategic` → `contract_value_multiplier = 1.5`.
`renewal_date = 2026-11-08`; at a reference `as_of` of `2026-08-14` (this feature's
implementation date), `days_until_renewal ≈ 86` →
`renewal_proximity_factor = clamp(2.0 - 86/90, 0.5, 2.0) = clamp(1.044, 0.5, 2.0) =
1.044` → `stakes ≈ 1.5 × 1.044 ≈ 1.567`. Not part of `examples/01`'s published numbers
(no prior calibration existed for this formula — `spec.md`'s Clarifications) — this is
a new worked check this feature introduces, not a reproduction of an existing one.

## Validation

- **Per-finding arithmetic**: `test_worked_example.py` asserts every
  `score_contributions` row above, to the decimal, plus the final `score_runs` totals.
- **Reconciliation**: `test_reconciliation.py` — property-based, thousands of generated
  `findings`/`issues` states, `SUM(points_contributed)` must equal
  `total_negative_points`/`total_positive_points` exactly, every time.
- **Monotonicity**: `test_monotonicity.py` — property-based, adding one more validated
  negative finding to any generated state must never lower the resulting score.
