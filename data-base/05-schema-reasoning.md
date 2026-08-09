# 05 · Schema — Reasoning (M5, M5a)

See `requirements/05-interpreters-readers.md`.

## `findings`

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

## `issues`

Groups of findings sharing one underlying cause (REQ-M6-06).

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `label` | TEXT | Human-readable issue name, e.g. "Issue A — tracking tool" |
| `cluster_method` | ENUM(`embedding_similarity`,`shared_entity`,`manual`) | |
| `created_at` | TIMESTAMPTZ | |

## `finding_issue_map`

| Field | Type | Description |
|---|---|---|
| `finding_id` | UUID FK → `findings.id` | |
| `issue_id` | UUID FK → `issues.id` | |
| `rank_within_issue` | INTEGER | 1st, 2nd, 3rd… drives diminishing weights (REQ-M6-07: 100%/60%/36%/22%) |

*(Composite PK: `finding_id, issue_id`)*

## `quarantine`

Findings that failed the validation gate — retained, never scored, become the evaluation dataset (REQ-M5A-04).

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `finding_id` | UUID FK → `findings.id` | |
| `failed_check` | ENUM(`schema_invalid`,`cited_event_missing`,`insufficient_evidence`,`confidence_below_floor`) | |
| `detail` | TEXT | |
| `created_at` | TIMESTAMPTZ | |

## `validation_failures`

Fine-grained log, one row per failed check (a finding can fail more than one check).

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `quarantine_id` | UUID FK → `quarantine.id` | |
| `check_name` | TEXT | |
| `expected` | TEXT | |
| `actual` | TEXT | |

## `finding_type_config`

Global (per-deployment) seed table — the `base` weight per finding type (REQ-M6-02), plus each type's confidence floor and evidence-count floor used by the validation gate.

| Field | Type | Description |
|---|---|---|
| `finding_type` | TEXT PK | |
| `base_points` | NUMERIC(6,2) | e.g. broken response promise = 20 |
| `confidence_floor` | NUMERIC(3,2) | Minimum confidence to pass M5a |
| `min_evidence_count` | INTEGER | Minimum cited events to pass M5a |
| `half_life_days` | NUMERIC(6,2) NULL | Used once `state = resolved` (REQ-M6-09) |
| `version` | TEXT | Config version, recorded on every score run for replay |

## Notes

- `findings.cited_event_ids` non-empty constraint is what makes "a finding without evidence" structurally unrepresentable at the database layer, not just at the application layer (P1).
- `finding_issue_map.rank_within_issue` is assigned by the scoring engine at scoring time (largest points first), not by the reader — readers never rank (REQ-M5-P1).
