# 03 · Schema — Event ledger (M2)

The single source of truth. See `requirements/02-event-ledger.md`.

## `events`

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
| `data_key_ref` | TEXT NULL | KMS data-key reference; setting this NULL (destroying the key) is the deletion mechanism |
| `structured_payload` | JSONB | Non-body structured fields (ticket priority, usage delta, survey score, etc.) |
| `supersedes_event_id` | UUID FK → `events.id`, NULL | Set when this event is a correction of a prior one (REQ-M2-03) |
| `thread_key` | TEXT NULL | Cross-channel thread identifier assigned by stitching |
| `prev_event_hash` | TEXT | Hash-chain link (REQ-M2-08) |
| `event_hash` | TEXT | `H(payload + prev_event_hash)` |
| `created_at` | TIMESTAMPTZ | Row insert time (equals `recorded_at` in practice; kept separate for clarity) |

## `event_threads` *(PROJECTION — rebuildable)*

Cross-channel thread stitching results.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `thread_key` | TEXT | Matches `events.thread_key` |
| `event_id` | UUID FK → `events.id` | |
| `stitch_confidence` | NUMERIC(3,2) | Confidence the event belongs to this thread (REQ-M2-04) |
| `stitch_method` | ENUM(`participant_subject`,`ticket_reference`,`timing_heuristic`,`manual`) | |

## `response_pairs` *(PROJECTION — rebuildable)*

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

## `rollups` *(PROJECTION — rebuildable)*

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

## Notes

- `events.occurred_at` vs `events.recorded_at`: querying "what did we know as of last Tuesday" filters on `recorded_at <= X`, ordering the timeline by `occurred_at`. This is what makes historical replay honest (REQ-M2-09).
- `supersedes_event_id` forms a forward-only correction chain — the original row is never touched, only referenced.
- All three projection tables can be `TRUNCATE`d and rebuilt from `events` + `client_profile_versions` alone (see `01-database-overview.md`).
