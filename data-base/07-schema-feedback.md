# 07 · Schema — Feedback memory (M4)

See `requirements/04-feedback-memory.md`.

## `feedback_verdicts`

Append-only log of every verdict click.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `finding_id` | UUID FK → `findings.id`, NULL | The specific finding the verdict applies to, if card-scoped |
| `issue_id` | UUID FK → `issues.id`, NULL | If the verdict applies to a whole issue card |
| `verdict` | ENUM(`correct`,`false_alarm`,`resolved`) | REQ-M4-01 |
| `submitted_by` | TEXT | User identifier |
| `pattern_signature` | TEXT | `reader_type + finding_type + event_signature_class` — the key `damping_weights` groups on (REQ-M4-02) |
| `created_at` | TIMESTAMPTZ | |

## `damping_weights`

Current damping multiplier per pattern — one row per `pattern_signature`, upserted as new verdicts arrive.

| Field | Type | Description |
|---|---|---|
| `pattern_signature` | TEXT PK | Matches `feedback_verdicts.pattern_signature` |
| `weight` | NUMERIC(4,3) CHECK (weight <= 1.000) | Current damping term consumed by `score_contributions.damping` (REQ-M4-03) |
| `false_alarm_count` | INTEGER | Running tally, feeds the disclosure string (REQ-M4-04) |
| `resolved_count` | INTEGER | |
| `correct_count` | INTEGER | |
| `last_updated_at` | TIMESTAMPTZ | |
| `disclosure_text` | TEXT | e.g. "weight reduced — your team dismissed this pattern twice" — precomputed for direct display |

## Notes

- `weight <= 1.000` at the schema level is a second enforcement layer for REQ-M6-P3, alongside the `CHECK` on `score_contributions.damping`.
- No table here stores model weights, embeddings, or any ML artifact — feedback memory is pure counting and lookup, matching REQ-M4-05 (no retraining).
