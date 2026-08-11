# 02 · Schema — Ingestion (M1)

Tables that back the Signal collectors and Absence collector. See `requirements/01-signal-collectors.md`.

Every table on this page answers a "where did this come from, and can we prove it?" question — nothing here decides whether anything matters. All examples below reuse the same worked scenario as `examples/01-end-to-end-walkthrough.md` (client: Meridian Logistics), so you can cross-reference the two documents directly.

## `sources`

**In plain terms:** the phone book of connected systems for this one client deployment. One row exists per system before any data ever flows — it's set up once, during onboarding, not created dynamically.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `source_type` | ENUM(`zendesk`,`jira`,`intercom`,`gmail`,`microsoft365`,`slack`,`teams`,`warehouse`,`csat`,`nps`,`calendar`,`transcripts`,`salesforce`,`contracts`) | Which adapter this row configures |
| `display_name` | TEXT | Human label shown on the coverage line |
| `auth_scope` | TEXT | Documented OAuth/API scope granted (read-only) |
| `status` | ENUM(`connected`,`degraded`,`disconnected`) | Current connectivity state |
| `last_successful_sync_at` | TIMESTAMPTZ | Drives the "complete to HH:MM" coverage line |
| `created_at` | TIMESTAMPTZ | |

**Example row:**

| id | source_type | display_name | status | last_successful_sync_at |
|---|---|---|---|---|
| `src-tickets` | `zendesk` | Meridian — Support | `connected` | 2026-08-07 07:41 |

## `collector_runs`

**In plain terms:** a receipt for every time an adapter went and fetched something — whether triggered by a webhook (the source pushed to us) or a scheduled poll (we asked the source). If a collector ever runs and finds nothing new, there's still a row here, just with `envelopes_emitted = 0`.

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

**Example row:** the Zendesk poll that picked up ticket #456's reopen and ticket #398's resolution in the same run:

| id | source_id | trigger | envelopes_emitted | duplicates_skipped | error |
|---|---|---|---|---|---|
| `run-2` | `src-tickets` | `poll` | 2 | 0 | *(null)* |

If this exact poll ran again five minutes later before anything new happened at Zendesk, you'd expect a **new** `collector_runs` row with `envelopes_emitted = 0` and `duplicates_skipped = 0` — not a second copy of ticket #456. The de-duplication happens one layer down, in `raw_envelopes`, via `idempotency_key`.

## `coverage_reports`

**In plain terms:** the honest answer to "how much of the world did we actually see this time?" — this is what makes the dashboard's coverage line ("Reading 5 of 5 sources · complete to 10:16") true rather than a guess.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `collector_run_id` | UUID FK → `collector_runs.id` | |
| `sources_expected` | INTEGER | Number of configured sources |
| `sources_read` | INTEGER | Number successfully read this run |
| `gap_reason` | TEXT NULL | Human-readable reason for any shortfall |
| `complete_to` | TIMESTAMPTZ | Latest timestamp the report can vouch for |
| `created_at` | TIMESTAMPTZ | |

**Example row — a clean run** (all five Phase-1-and-beyond sources connected in this illustration):

| collector_run_id | sources_expected | sources_read | gap_reason | complete_to |
|---|---|---|---|---|
| `run-5` | 5 | 5 | *(null)* | 2026-08-07 10:16 |

**Example row — a degraded run**, for contrast (Slack briefly disconnected):

| collector_run_id | sources_expected | sources_read | gap_reason | complete_to |
|---|---|---|---|---|
| `run-9` | 5 | 4 | "Slack OAuth token expired 08-09 14:02" | 2026-08-09 09:00 |

That second row is exactly what makes `requirements/11-non-functional-requirements.md` REQ-NFR-07 real: the scoring engine sees `sources_read < sources_expected` and freezes the score with a visible banner instead of silently scoring on 4/5 of the picture as if it were the whole thing.

## `identity_map`

**In plain terms:** answers "who actually sent this?" by mapping a raw email address or username to a real person in the client profile — or explicitly recording that nobody could be matched, rather than guessing.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `source_identifier` | TEXT | Raw address/user ID as seen in the source (e.g. `ana.reyes@meridian.com`) |
| `source_type` | ENUM (same as `sources.source_type`) | |
| `stakeholder_id` | UUID FK → `stakeholders.id`, NULL | NULL means unresolved (REQ-M1-05) — a valid, queryable state |
| `match_confidence` | NUMERIC(3,2) NULL | Fuzzy-match score if a suggestion exists; NULL if exact match |
| `resolved_by` | ENUM(`exact_match`,`human_confirmed`,`unresolved`) | |
| `first_seen_at` | TIMESTAMPTZ | Powers the "Someone at meridian.com has written 3 times…" unresolved-person state (spec §11.5) |

**Example rows** — one resolved, one deliberately not:

| source_identifier | source_type | stakeholder_id | match_confidence | resolved_by |
|---|---|---|---|---|
| `ana.reyes@meridian.com` | `gmail` | `stk-ana` | *(null)* | `exact_match` |
| *(Zendesk's generic support-desk contact address)* | `zendesk` | *(null)* | *(null)* | `unresolved` |

The second row is not an error — it's the system correctly refusing to guess. Ticket #456 still gets collected, still gets a Commitment finding, and still contributes to the score in Step 9 of `examples/01-end-to-end-walkthrough.md` — it just does so without a stakeholder-specific `influence` multiplier, because nobody named is attached to it.

## `raw_envelopes`

**In plain terms:** the one consistent shape every source's output gets forced into before it's allowed anywhere near the permanent record. This is also where the message body gets encrypted and where anything on the client profile's exclusion list gets stripped out — both *before* storage, never after.

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
| `data_key_ref` | TEXT | Reference to the per-deployment data key — a `.env`-scoped key file in Phase 1, KMS-wrapped in Phase 2 (crypto-shredding target either way) |
| `ledger_event_id` | UUID FK → `events.id`, NULL | Set once appended to the ledger; NULL if quarantined pre-ledger |
| `created_at` | TIMESTAMPTZ | |

**Example row** — Ana's Monday-morning email, on its way into the ledger:

| id | source_native_id | idempotency_key | occurred_at | identity_status | redacted_fields | ledger_event_id |
|---|---|---|---|---|---|---|
| `env-1` | `gmail-msg-8831` | `hash(gmail, 8831)` | 2026-08-03 09:14 | `resolved` | `{}` | `evt-1` |

`redacted_fields` is `{}` (empty) here because nothing in this particular email touched an excluded topic. If Ana had cc'd Meridian's legal counsel about a contract dispute in the same thread, the `commercial_negotiation` exclusion (spec §6.3) would strip that portion before this row is even written, and `redacted_fields` would read `{"legal_cc_thread"}` — the redaction is visible and auditable, not silently vanished.

## Notes

- `idempotency_key` carries a `UNIQUE` constraint — the database itself is the second line of defense (beyond application-level dedup) against duplicate ingestion (REQ-NFR-27).
- `identity_map.stakeholder_id = NULL` is a first-class, queryable state — never backfilled with a guess.
