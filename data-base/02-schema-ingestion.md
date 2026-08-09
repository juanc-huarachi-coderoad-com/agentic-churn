# 02 · Schema — Ingestion (M1)

Tables that back the Signal collectors and Absence collector. See `requirements/01-signal-collectors.md`.

## `sources`

One row per connected source system for this deployment.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `source_type` | ENUM(`zendesk`,`jira`,`intercom`,`gmail`,`microsoft365`,`slack`,`teams`,`warehouse`,`csat`,`nps`,`calendar`,`transcripts`,`salesforce`,`contracts`) | Which adapter this row configures |
| `display_name` | TEXT | Human label shown on the coverage line |
| `auth_scope` | TEXT | Documented OAuth/API scope granted (read-only) |
| `status` | ENUM(`connected`,`degraded`,`disconnected`) | Current connectivity state |
| `last_successful_sync_at` | TIMESTAMPTZ | Drives the "complete to HH:MM" coverage line |
| `created_at` | TIMESTAMPTZ | |

## `collector_runs`

One row per collector execution (webhook trigger or scheduled poll).

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `source_id` | UUID FK → `sources.id` | |
| `trigger` | ENUM(`webhook`,`poll`,`manual`) | |
| `window_start` | TIMESTAMPTZ | Start of the fetch window, including the deliberate overlap |
| `window_end` | TIMESTAMPTZ | |
| `envelopes_emitted` | INTEGER | Count for quick health inspection |
| `duplicates_skipped` | INTEGER | Idempotency-key collisions found (proves REQ-M1-03/REQ-NFR-27) |
| `error` | TEXT NULL | Populated on failure; NULL on success |
| `started_at` / `finished_at` | TIMESTAMPTZ | |

## `coverage_reports`

One row per `collector_runs` execution, or one rollup row per scoring-relevant time window — the artifact behind spec's coverage line and REQ-M1-07.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `collector_run_id` | UUID FK → `collector_runs.id` | |
| `sources_expected` | INTEGER | Number of configured sources |
| `sources_read` | INTEGER | Number successfully read this run |
| `gap_reason` | TEXT NULL | Human-readable reason for any shortfall |
| `complete_to` | TIMESTAMPTZ | Latest timestamp the report can vouch for |
| `created_at` | TIMESTAMPTZ | |

## `identity_map`

Resolved (and explicitly unresolved) mappings from source-native identifiers to profile stakeholders.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `source_identifier` | TEXT | Raw address/user ID as seen in the source (e.g. `ana.reyes@meridian.com`) |
| `source_type` | ENUM (same as `sources.source_type`) | |
| `stakeholder_id` | UUID FK → `stakeholders.id`, NULL | NULL means unresolved (REQ-M1-05) — a valid, queryable state |
| `match_confidence` | NUMERIC(3,2) NULL | Fuzzy-match score if a suggestion exists; NULL if exact match |
| `resolved_by` | ENUM(`exact_match`,`human_confirmed`,`unresolved`) | |
| `first_seen_at` | TIMESTAMPTZ | Powers the "Someone at meridian.com has written 3 times…" unresolved-person state (spec §11.5) |

## `raw_envelopes`

The standard wrapper every collector produces before ledger append — kept as a staging/audit table distinct from the immutable `events` table so malformed envelopes never corrupt the ledger.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `collector_run_id` | UUID FK → `collector_runs.id` | |
| `source_native_id` | TEXT | The source system's own record ID |
| `idempotency_key` | TEXT UNIQUE | `hash(source_type, source_native_id)` — enforces REQ-M1-03 at the DB level |
| `occurred_at` | TIMESTAMPTZ | When it happened per the source system |
| `identity_status` | ENUM(`resolved`,`unresolved`) | |
| `redacted_fields` | TEXT[] | Which fields were stripped per `exclusions` (REQ-M1-09) |
| `payload_encrypted` | BYTEA | Envelope-encrypted raw payload |
| `data_key_ref` | TEXT | Reference to the per-deployment KMS-wrapped data key (crypto-shredding target) |
| `ledger_event_id` | UUID FK → `events.id`, NULL | Set once appended to the ledger; NULL if quarantined pre-ledger |
| `created_at` | TIMESTAMPTZ | |

## Notes

- `idempotency_key` carries a `UNIQUE` constraint — the database itself is the second line of defense (beyond application-level dedup) against duplicate ingestion (REQ-NFR-27).
- `identity_map.stakeholder_id = NULL` is a first-class, queryable state — never backfilled with a guess.
