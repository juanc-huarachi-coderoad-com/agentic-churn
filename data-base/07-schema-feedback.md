# 07 · Schema — Feedback memory (M4)

See `requirements/04-feedback-memory.md`. Examples below continue Step 12 of `examples/01-end-to-end-walkthrough.md` — the week after the main scenario, when Diego's "stepping back" finding turns out to be a false alarm.

**Why this schema exists, in plain terms:** two tiny tables that make "the system learns from correction" true without any machine-learning training pipeline. A human clicks one button; one row gets written; one number in another table changes. That's the entire mechanism.

## `feedback_verdicts`

**In plain terms:** a permanent log of every time a human told the system "you got this one right / wrong / it's resolved now." Nothing is ever deleted from this log, even if it later turns out the verdict itself was a mistake — corrections get their own new row, same as everywhere else in this database.

Append-only log of every verdict click.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `finding_id` | UUID FK → `findings.id`, NULL | The specific finding the verdict applies to, if card-scoped |
| `issue_id` | UUID FK → `issues.id`, NULL | If the verdict applies to a whole issue card |
| `verdict` | ENUM(`correct`,`false_alarm`,`resolved`) | REQ-M4-01 |
| `submitted_by_user_id` | UUID FK → `users.id` | A real identity, not free text — see `data-base/12-users-and-auth.md` |
| `pattern_signature` | TEXT | `reader_type + finding_type + event_signature_class` — the key `damping_weights` groups on (REQ-M4-02) |
| `created_at` | TIMESTAMPTZ | |

A `CHECK` constraint (`finding_id IS NOT NULL OR issue_id IS NOT NULL`) guarantees every verdict applies to *something* — a verdict with both fields NULL would be meaningless and is structurally rejected.

**Example row** — the CS lead correcting the Relationship reader about Diego:

| id | finding_id | verdict | submitted_by_user_id | pattern_signature |
|---|---|---|---|---|
| `fv-1` | `fnd-5` | `false_alarm` | Marta's user row | `relationship+relationship_change` |

`fnd-5` was the finding that Diego had "effectively become inactive in the channel" — it turned out he was on pre-announced parental leave the whole time, something only a human on the CS team knew. The system had no way to know that on its own; this row is how it finds out.

## `damping_weights`

**In plain terms:** one row per *pattern* of finding (not per individual finding) — the running answer to "how much should we trust this specific type of observation, given what the team has told us about it so far?" This is the number the scoring engine actually reads; `feedback_verdicts` is just the history that produced it.

Current damping multiplier per pattern — one row per `pattern_signature`, upserted as new verdicts arrive.

| Field | Type | Description |
|---|---|---|
| `pattern_signature` | TEXT PK | Matches `feedback_verdicts.pattern_signature` |
| `weight` | NUMERIC(4,3) CHECK (weight BETWEEN 0 AND 1.000) | Current damping term consumed by `score_contributions.damping` (REQ-M4-03). The lower bound matters too: a negative weight would flip a penalty into a bonus, which is never a valid outcome of "the team said this was a false alarm" |
| `false_alarm_count` | INTEGER | Running tally, feeds the disclosure string (REQ-M4-04) |
| `resolved_count` | INTEGER | |
| `correct_count` | INTEGER | |
| `last_updated_at` | TIMESTAMPTZ | |
| `disclosure_text` | TEXT | e.g. "weight reduced — your team dismissed this pattern twice" — precomputed for direct display |

**Example row** — before and after the `fv-1` verdict above:

| pattern_signature | weight (before) | weight (after) | false_alarm_count | disclosure_text |
|---|---|---|---|---|
| `relationship+relationship_change` | 1.000 | **0.500** | 1 | "weight reduced — your team flagged this pattern as a false alarm" |

Nothing about last week's already-computed score changes because of this update — `score_runs` rows are never rewritten (`data-base/06-schema-scoring.md`). The **next** time a `relationship_change` finding is scored, though, its `score_contributions.damping` cell will read `0.500` instead of `1.000`, cutting that single line item's point contribution in half — and the card shown to the CS lead will display the `disclosure_text` above, so the "learning" is visible, not a silent adjustment.

## Notes

- `weight BETWEEN 0 AND 1.000` at the schema level is a second enforcement layer for REQ-M6-P3, alongside the matching `CHECK` on `score_contributions.damping` (`data-base/06-schema-scoring.md`).
- No table here stores model weights, embeddings, or any ML artifact — feedback memory is pure counting and lookup, matching REQ-M4-05 (no retraining).
