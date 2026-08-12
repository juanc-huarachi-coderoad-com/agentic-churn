# 05 · Schema — Reasoning (M5, M5a)

See `requirements/05-interpreters-readers.md`. Examples below reuse the nine validated findings (plus one quarantined) from `examples/01-end-to-end-walkthrough.md`.

**Why this schema exists, in plain terms:** everything before this point (`data-base/02`, `data-base/03`) is just facts — messages, tickets, numbers. This schema is where the system is finally allowed to have an *opinion* about those facts ("this looks like a broken promise"), but every opinion has to point back at the specific facts that produced it, or it's not allowed to exist (`findings.cited_event_ids` — see below).

## `findings`

**In plain terms:** one row per observation a reader made — "Ana's tone got worse," "this ticket broke a promise," "usage is down." A finding is a claim, not yet a certainty; the next table (`quarantine`) is where weak claims get caught before they can affect anything.

Every structured observation, before or after validation (status column distinguishes).

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `reader_type` | ENUM(`commitment`,`usage`,`recurrence`,`absence`,`relationship`,`tone`,`intent`,`meeting`) | |
| `reader_version` | TEXT | Prompt/model or algorithm version that produced this finding (REQ-M5-15, architecture Rule 5) |
| `finding_type` | TEXT | e.g. `broken_response_promise`, `tone_deterioration`, `usage_drop` — maps to `finding_type_config.base` |
| `magnitude` | NUMERIC(3,2) | 0–1, size of the change (REQ-M5-03) |
| `confidence` | NUMERIC(3,2) | 0–1, certainty of the reader (REQ-M5-03) |
| `cited_event_ids` | UUID[] NOT NULL, `array_length >= 1` | Non-empty by constraint (REQ-M5-05) |
| `stakeholder_id` | UUID FK → `stakeholders.id`, NULL | |
| `product_area_id` | UUID FK → `product_areas.id`, NULL | |
| `status` | ENUM(`pending_validation`,`validated`,`quarantined`) | |
| `state` | ENUM(`open`,`resolved`,`open_overdue`) NULL | Set once scored (REQ-M6-09/10/11) |
| `created_at` | TIMESTAMPTZ | |

**Example rows** — three findings from the worked example, chosen to show the range: a fully-deterministic one, an LLM one, and the one that later gets quarantined:

| id | reader_type | finding_type | magnitude | confidence | cited_event_ids | status |
|---|---|---|---|---|---|---|
| `fnd-1` | `commitment` | `broken_response_promise` | 1.00 | 1.00 | `{evt-2}` | `validated` |
| `fnd-6` | `tone` | `tone_deterioration` | 0.60 | 0.80 | `{evt-1}` | `validated` |
| `fnd-10` | `tone` | `tone_deterioration` | 0.55 | 0.55 | `{evt-5}` | `quarantined` |

`fnd-1` needed zero uncertainty — it's arithmetic (19 hours vs. a 4-hour promise), so `confidence = 1.00`. `fnd-6` came from a language model comparing Ana's email against her own baseline, so it carries real but imperfect confidence. `fnd-10` attempted the same kind of tone judgment about Diego in Slack, but with only one prior message to compare against, its own confidence came out too low to survive — see `quarantine` below.

## `issues`

**In plain terms:** a folder that groups several findings together because they're all symptoms of the same underlying problem — so scoring doesn't count one broken feature five separate times.

Groups of findings sharing one underlying cause (REQ-M6-06).

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `label` | TEXT | Human-readable issue name, e.g. "Issue A — tracking tool" |
| `cluster_method` | ENUM(`embedding_similarity`,`shared_entity`,`manual`) | |
| `created_at` | TIMESTAMPTZ | |

**Example rows:**

| id | label | cluster_method |
|---|---|---|
| `iss-A` | Issue A — tracking_api reliability | `shared_entity` |
| `iss-B` | Issue B — Ana & Diego disengaging | `embedding_similarity` |

`iss-A` was grouped because three findings all reference the same ticket/product area — an easy, literal match. `iss-B` is more interesting: Ana's email tone, Ana's escalation language, Ana's CSAT score, and Diego's silence come from **three different sources and two different people**, yet an embedding-similarity comparison recognizes they're all describing one story (the relationship cooling), not four unrelated ones.

## `finding_issue_map`

**In plain terms:** the actual grouping — which findings belong to which issue, and in what order of importance within that issue. The order is what the diminishing-returns rule (100% / 60% / 36% / 22%…) is applied to.

| Field | Type | Description |
|---|---|---|
| `finding_id` | UUID FK → `findings.id` | |
| `issue_id` | UUID FK → `issues.id` | |
| `rank_within_issue` | INTEGER | 1st, 2nd, 3rd… drives diminishing weights (REQ-M6-07: 100%/60%/36%/22%) |

*(Composite PK: `finding_id, issue_id`)*

**Example rows** — Issue A's three findings, ranked by how much raw weight each carries:

| finding_id | issue_id | rank_within_issue |
|---|---|---|
| `fnd-1` (broken promise) | `iss-A` | 1 |
| `fnd-2` (recurrence) | `iss-A` | 2 |
| `fnd-3` (usage down) | `iss-A` | 3 |

`fnd-1` counts at 100% of its own points; `fnd-2` — even though it's a real, separate observation — counts at only 60% of its own points because it's the *second* finding inside the same story; `fnd-3` at 36%. The full arithmetic for both issues is worked out in `examples/01-end-to-end-walkthrough.md` §9.

## `quarantine`

**In plain terms:** the "rejected, but not forgotten" pile. A finding lands here instead of being scored, and — importantly — it is never edited or "fixed" to try again. It just sits here, honestly, as a record of a claim that didn't clear the bar.

Findings that failed the validation gate — retained, never scored, become the evaluation dataset (REQ-M5A-04).

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `finding_id` | UUID FK → `findings.id`, **UNIQUE** | A finding is quarantined at most once — never re-submitted for another attempt (REQ-M5A-03: never repaired, never retried). The `UNIQUE` constraint makes the 1-to-0-or-1 relationship shown in `09-erd-full.md` actually true in the schema |
| `failed_check` | ENUM(`schema_invalid`,`cited_event_missing`,`insufficient_evidence`,`confidence_below_floor`) | |
| `detail` | TEXT | |
| `created_at` | TIMESTAMPTZ | |

**Example row** — `fnd-10` from above, rejected:

| id | finding_id | failed_check | detail |
|---|---|---|---|
| `q-1` | `fnd-10` | `confidence_below_floor` | "confidence 0.55 < required 0.65 for tone_deterioration" |

## `validation_failures`

**In plain terms:** the receipt for *why*, specifically, a quarantined finding failed — useful when a finding fails more than one check at once and each reason needs to be recorded separately.

Fine-grained log, one row per failed check (a finding can fail more than one check).

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `quarantine_id` | UUID FK → `quarantine.id` | |
| `check_name` | TEXT | |
| `expected` | TEXT | |
| `actual` | TEXT | |

**Example row:**

| quarantine_id | check_name | expected | actual |
|---|---|---|---|
| `q-1` | `confidence_floor` | "≥ 0.65" | "0.55" |

## `finding_type_config`

**In plain terms:** the price list. Before any finding can be turned into points, the system needs to know how many points that *type* of finding is worth at its full strength, and what bar it has to clear to be trusted at all. This table is set once by the product team (Phase 1: seed defaults; Phase 2: tuned in a workshop with real CS leads — see `decisions/00-open-questions-resolved.md` Q4), not something a reader decides for itself.

Global (per-deployment) seed table — the `base` weight per finding type (REQ-M6-02), plus each type's confidence floor and evidence-count floor used by the validation gate.

| Field | Type | Description |
|---|---|---|
| `finding_type` | TEXT PK | |
| `base_points` | NUMERIC(6,2) | e.g. broken response promise = 20 |
| `confidence_floor` | NUMERIC(3,2) | Minimum confidence to pass M5a |
| `min_evidence_count` | INTEGER | Minimum cited events to pass M5a |
| `half_life_days` | NUMERIC(6,2) NULL | Used once `state = resolved` (REQ-M6-09) |
| `version` | TEXT | Config version, recorded on every score run for replay |

**Example rows** — the seed values used throughout `examples/01-end-to-end-walkthrough.md`:

| finding_type | base_points | confidence_floor | min_evidence_count | half_life_days |
|---|---|---|---|---|
| `broken_response_promise` | 20.00 | 0.50 | 1 | 14 |
| `tone_deterioration` | 10.00 | 0.65 | 3 | 21 |
| `recurring_issue` | 12.00 | 0.60 | 1 | 30 |
| `usage_deviation` | 15.00 | 0.60 | 1 | 21 |
| `escalation_language` | 14.00 | 0.60 | 1 | 14 |
| `contact_absence` | 12.00 | 0.60 | 1 | 30 |
| `relationship_change` | 8.00 | 0.55 | 1 | 30 |
| `csat_deviation` | 10.00 | 0.60 | 1 | 21 |
| `commitment_met` | 10.00 | 0.50 | 1 | 7 |

*(These nine rows are exactly the finding types used in `examples/01-end-to-end-walkthrough.md` — cross-check any of that document's arithmetic against this table directly.)*

Reading the `tone_deterioration` row is what explains why `fnd-10` was quarantined a few sections up: its confidence (0.55) simply didn't clear this row's `confidence_floor` (0.65).

## Notes

- `findings.cited_event_ids` non-empty constraint is what makes "a finding without evidence" structurally unrepresentable at the database layer, not just at the application layer (P1).
- `finding_issue_map.rank_within_issue` is assigned by the scoring engine at scoring time (largest points first), not by the reader — readers never rank (REQ-M5-P1).
