# 03 · Schema — Event ledger (M2)

The single source of truth. See `requirements/02-event-ledger.md`. Examples below reuse the same scenario as `examples/01-end-to-end-walkthrough.md`.

## `events`

**In plain terms:** this is *the* table — one row per fact that happened, and it is never edited or deleted. Think of it as a diary that only ever gets new pages added, never a page torn out or rewritten. Every other table in this document either feeds this one or reads from it.

Append-only. **No `UPDATE`/`DELETE` grant exists on this table for the application role.**

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `envelope_id` | UUID FK → `raw_envelopes.id` | |
| `event_type` | ENUM(`message`,`ticket_state_change`,`usage_measurement`,`survey_response`,`meeting`,`absence`,`crm_change`) | |
| `occurred_at` | TIMESTAMPTZ NOT NULL | **Bitemporal field 1** — when it happened |
| `recorded_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | **Bitemporal field 2** — when the ledger learned of it |
| `stakeholder_id` | UUID FK → `stakeholders.id`, NULL | Resolved participant, if any |
| `product_area_id` | UUID FK → `product_areas.id`, NULL | |
| `body_encrypted` | BYTEA NULL | Message body, envelope-encrypted; NULL after retention expiry (crypto-shredded) |
| `data_key_ref` | TEXT NULL | Data-key reference (`.env`-scoped in Phase 1, KMS in Phase 2); setting this NULL (destroying the key) is the deletion mechanism |
| `structured_payload` | JSONB | Non-body structured fields (ticket priority, usage delta, survey score, etc.) |
| `supersedes_event_id` | UUID FK → `events.id`, NULL | Set when this event is a correction of a prior one (REQ-M2-03) |
| `thread_key` | TEXT NULL | Cross-channel thread identifier assigned by stitching |
| `prev_event_hash` | TEXT | Hash-chain link (REQ-M2-08) |
| `event_hash` | TEXT | `H(payload + prev_event_hash)` |
| `created_at` | TIMESTAMPTZ | Row insert time (equals `recorded_at` in practice; kept separate for clarity) |

**Example rows** — two of the six events from the worked example, chosen to show the contrast between a message and a structured system fact:

| id | event_type | occurred_at | stakeholder_id | structured_payload (readable form) |
|---|---|---|---|---|
| `evt-1` | `message` | 2026-08-03 09:14 | `stk-ana` | "Please advise on the timeline. I need to brief the board on Thursday." |
| `evt-2` | `ticket_state_change` | 2026-08-03 07:40 | *(null)* | `{ticket: 456, title: "Slow API response", reopen_count: 2}` |

Notice `evt-1` has a real `stakeholder_id` (Ana resolved cleanly via `identity_map`) while `evt-2` doesn't (the Zendesk reporter never resolved to a named person) — both are perfectly valid, permanent facts either way.

**A worked example of a correction**, to show `supersedes_event_id` in action: suppose Zendesk later reclassifies ticket #456 from priority P2 to P1. The system does **not** go back and edit `evt-2` — it inserts a brand-new row:

| id | event_type | occurred_at | supersedes_event_id | structured_payload (readable form) |
|---|---|---|---|---|
| `evt-2b` | `ticket_state_change` | 2026-08-04 10:00 | `evt-2` | `{ticket: 456, priority_changed: "P2 -> P1"}` |

Anyone querying "what was true as of August 3rd" still sees the original P2 classification in `evt-2`, unmodified — and anyone querying "what's true now" follows the `supersedes_event_id` chain forward to `evt-2b`. Both questions have honest, different, simultaneously-correct answers, which is only possible because nothing was overwritten.

## `event_threads` *(PROJECTION — rebuildable)*

**In plain terms:** a single customer issue often shows up in more than one place — an email, then a ticket, then a Slack thread about the same problem. This table is how the system remembers "these three messages, from three different systems, are actually one conversation."

Cross-channel thread stitching results.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `thread_key` | TEXT | Matches `events.thread_key` |
| `event_id` | UUID FK → `events.id` | |
| `stitch_confidence` | NUMERIC(3,2) | Confidence the event belongs to this thread (REQ-M2-04) |
| `stitch_method` | ENUM(`participant_subject`,`ticket_reference`,`timing_heuristic`,`manual`) | |

**Example rows** — if a Slack message later referenced "ticket #456" directly, it would join the same thread:

| thread_key | event_id | stitch_confidence | stitch_method |
|---|---|---|---|
| `thread-456` | `evt-2` | 1.00 | `ticket_reference` *(the ticket itself, thread anchor)* |
| `thread-456` | `evt-slack-99` | 0.88 | `ticket_reference` *(Slack message mentioning "#456")* |

## `response_pairs` *(PROJECTION — rebuildable)*

**In plain terms:** turns "a client asked something" and "we (eventually) replied" into one measurable pair, so a promise like "we respond within 4 business hours" can be checked with simple arithmetic instead of someone eyeballing two timestamps.

A client message and its first qualifying reply, in business hours.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `client_event_id` | UUID FK → `events.id` | The inbound message/ticket |
| `reply_event_id` | UUID FK → `events.id`, NULL | NULL while still open |
| `commitment_id` | UUID FK → `commitments.id`, NULL | Which promise this pair is measured against |
| `business_hours_elapsed` | NUMERIC(10,2) NULL | Computed per the client profile's working calendar/timezone (REQ-M2-05) |
| `state` | ENUM(`open`,`resolved`,`open_overdue`) | Feeds directly into REQ-M6-09/10/11 recency terms |
| `profile_version_id` | UUID FK → `client_profile_versions.id` | Which calendar/commitment definition was used |

**Example rows** — the two tickets from the worked example, one broken promise and one kept one:

| client_event_id | business_hours_elapsed | state | (in plain terms) |
|---|---|---|---|
| `evt-2` (ticket #456) | 19.0 | `open_overdue` | Promised 4 hours, took 19, and still not resolved — the clock keeps aging |
| `evt-3` (ticket #398) | 2.0 | `resolved` | Promised 4 hours, took 2 — comfortably inside SLA |

## `rollups` *(PROJECTION — rebuildable)*

**In plain terms:** the system's memory of "what's normal" for a person or a metric, kept up to date so a reader never has to re-scan months of history just to answer "is this unusual?"

Per-person / per-metric aggregates used as reader baselines and dashboard sparklines.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `subject_type` | ENUM(`stakeholder`,`product_area`,`account`) | |
| `subject_id` | UUID | Polymorphic reference to `stakeholders.id` / `product_areas.id` / NULL for account-level |
| `metric` | TEXT | e.g. `avg_words_per_message`, `greeting_rate`, `feature_usage_weekly` |
| `window_start` / `window_end` | TIMESTAMPTZ | |
| `value` | NUMERIC | |
| `is_baseline` | BOOLEAN | TRUE if this window was human-confirmed as the healthy baseline (REQ-M5-06) |
| `computed_at` | TIMESTAMPTZ | |

**Example rows** — Ana's writing-style baseline, and this week's actual value, side by side:

| subject_type | subject_id | metric | window | value | is_baseline |
|---|---|---|---|---|---|
| `stakeholder` | `stk-ana` | `avg_words_per_message` | last healthy quarter | 47 | **true** |
| `stakeholder` | `stk-ana` | `avg_words_per_message` | this week | 14 | false |

The Tone reader (Step 4 of `examples/01-end-to-end-walkthrough.md`) is exactly this comparison — 14 words against a confirmed-healthy baseline of 47 — turned into a finding. This is also what "baseline-relative, never absolute sentiment" (spec P7) means concretely: there's no universal "47 words is normal" rule anywhere in the system, only *this specific person's* own history.

## Notes

- `events.occurred_at` vs `events.recorded_at`: querying "what did we know as of last Tuesday" filters on `recorded_at` up to that point in time, ordering the timeline by `occurred_at`. This is what makes historical replay honest (REQ-M2-09).
- `supersedes_event_id` forms a forward-only correction chain — the original row is never touched, only referenced.
- All three projection tables can be `TRUNCATE`d and rebuilt from `events` + `client_profile_versions` alone (see `01-database-overview.md`).
