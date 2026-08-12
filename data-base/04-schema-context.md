# 04 · Schema — Client profile & context (M3)

See `requirements/03-client-profile.md`. Directly models the spec §6.2 YAML profile as versioned relational rows. Examples below use the same Meridian Logistics scenario as `examples/01-end-to-end-walkthrough.md`.

**Why this schema exists, in plain terms:** every other reasoning table in this database asks "what happened?" This one alone answers "**to whom**, and **how much does it matter**?" A slow reply to the CTO who signs the renewal is not the same event as a slow reply to a trial user who signed up yesterday — this schema is the only place that difference is captured, as an explicit multiplier a human wrote down, not something the system infers on its own.

## `client_profile_versions`

**In plain terms:** the client profile as a whole — one row per edit, never overwritten. If the CS lead changes the renewal date today, that's a *new* row, not a change to the old one, so a scoring run from last month can still be explained using exactly the profile that was true when it ran.

Append-only. One row per edit.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | Referenced by every scoring run (REQ-M3-05) |
| `version_number` | INTEGER | Monotonically increasing |
| `client_name` | TEXT | e.g. "Meridian Logistics" |
| `renewal_date` | DATE | |
| `contract_value_band` | ENUM(`strategic`,`standard`,`smb`) | Feeds the `stakes` calculation (REQ-M6-28), never the score itself |
| `business_goals` | TEXT[] | |
| `working_hours_start` / `working_hours_end` | TIME | |
| `timezone` | TEXT | IANA tz name |
| `languages` | TEXT[] | |
| `communication_norms` | TEXT | Free-text norms description, supplied to readers as context only (never scoring logic — REQ-M3-P1) |
| `exclusions` | TEXT[] | Thread categories deliberately not collected (REQ-NFR-17) |
| `authored_by_user_id` | UUID FK → `users.id` | CS lead who submitted this version (`data-base/12-users-and-auth.md`) — a real identity, not free text |
| `created_at` | TIMESTAMPTZ | |
| `is_current` | BOOLEAN | Exactly one TRUE row per deployment at any time |

**Example row:**

| id | version_number | client_name | renewal_date | contract_value_band | working_hours | timezone | exclusions | authored_by_user_id | is_current |
|---|---|---|---|---|---|---|---|---|---|
| `pv-3` | 3 | Meridian Logistics | 2026-11-08 | `strategic` | 08:00–18:00 | America/Bogota | `{legal_threads, commercial_negotiation}` | Marta's user row | **true** |

If Marta edits the working hours next month, the system writes `pv-4` with `is_current = true` and flips `pv-3.is_current` to `false` — `pv-3` is never deleted, so any score computed while it was current can still be explained against the exact rules that produced it.

## `stakeholders`

**In plain terms:** the "who matters, and how much" list. This is where the CS lead tells the system, in a form it can do arithmetic with, that Ana isn't just another contact — she's the person whose opinion is worth 60% more than an average one, because she signs the check.

Versioned alongside the profile — a new profile version may add/edit rows, but historical scoring runs still resolve through `client_profile_versions.id` + the stakeholder rows active at that version.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `profile_version_id` | UUID FK → `client_profile_versions.id` | |
| `external_id` | TEXT | Stable ID across versions, e.g. `stk_ana` |
| `name` | TEXT | |
| `role` | TEXT | e.g. "CTO" |
| `influence` | ENUM(`sponsor`,`daily_user`,`unknown`) | |
| `influence_multiplier` | NUMERIC(3,2) | e.g. sponsor = 1.60, daily_user = 1.20, unknown = 0.80 (REQ-M3-03) |
| `signs_renewal` | BOOLEAN | At least one TRUE row required per profile version (REQ-M3-07) |
| `identifiers` | TEXT[] | Email addresses / usernames used by `identity_map` |

**Example rows** — the two people the whole worked example revolves around:

| id | external_id | name | role | influence | influence_multiplier | signs_renewal | identifiers |
|---|---|---|---|---|---|---|---|
| `stk-ana` | `stk_ana` | Ana Reyes | CTO | `sponsor` | 1.60 | **true** | `{ana.reyes@meridian.com}` |
| `stk-diego` | `stk_diego` | Diego Marín | Dev lead | `daily_user` | 1.20 | false | `{diego@meridian.com}` |

Read `influence_multiplier` as "how much more this person's signal counts than a neutral baseline of 1.00." A finding about Ana literally counts 60% more than the exact same finding about an unresolved, unnamed contact (multiplier 0.80 for `unknown`) — a 2× difference in weight for the identical event, purely because of who said it. That's product principle **P7 — context over sentiment** expressed as a single column.

## `product_areas`

**In plain terms:** the "what matters, and how much" list — the product-side counterpart to stakeholders. Not every feature is equally important to a client; this is where that's written down explicitly instead of assumed.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `profile_version_id` | UUID FK → `client_profile_versions.id` | |
| `key` | TEXT | e.g. `tracking_api` |
| `criticality` | ENUM(`critical`,`standard`,`peripheral`) | |
| `criticality_multiplier` | NUMERIC(3,2) | e.g. critical = 1.50, standard = 1.00, peripheral = 0.60 (REQ-M3-03) |

**Example rows:**

| id | key | criticality | criticality_multiplier |
|---|---|---|---|
| `pa-tracking` | `tracking_api` | `critical` | 1.50 |
| `pa-reporting` | `reporting` | `standard` | 1.00 |

A broken-promise finding tied to `tracking_api` (Meridian's core workflow) is worth 50% more than the identical finding tied to `reporting` (useful, not load-bearing) — again, an explicit, human-authored number, not a guess the system makes about which features "seem important."

## `commitments`

**In plain terms:** the promises the client was actually made, written down precisely enough that a computer can check whether they were kept — "we'll respond to P1 tickets within 4 business hours" instead of a vague sense of "we should probably be responsive."

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `profile_version_id` | UUID FK → `client_profile_versions.id` | |
| `type` | ENUM(`first_response`,`recurring_sync`,`milestone`) | |
| `priority` | TEXT NULL | e.g. `P1`, applies to `first_response` |
| `threshold_business_hours` | NUMERIC(6,2) NULL | e.g. 4 |
| `cadence` | TEXT NULL | e.g. "weekly" for recurring syncs, drives the Absence collector |

**Example row** — the promise ticket #456 broke in the worked example:

| id | type | priority | threshold_business_hours |
|---|---|---|---|
| `cmt-p1-response` | `first_response` | `P1` | 4.0 |

This is the exact row `response_pairs.commitment_id` (`data-base/03-schema-ledger.md`) points to when computing that ticket #456's 19-hour reply time was 15 hours late — the "4" here is the number the Commitment reader checks every response against.

## `profile_history_entries`

**In plain terms:** a short, plain-English timeline of things worth remembering about this account — not used in any calculation, just context a reader (or a human) might need to interpret the present correctly.

Free-form narrative history (spec §6.2 `history:` block) — context for readers, not scoring input.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `profile_version_id` | UUID FK → `client_profile_versions.id` | |
| `event_date` | DATE | |
| `description` | TEXT | e.g. "major outage, improvement plan agreed" |

**Example row:**

| event_date | description |
|---|---|
| 2026-03-02 | "Major outage on tracking_api, improvement plan agreed with Ana" |

## Notes

- `stakeholders.signs_renewal` must have ≥ 1 TRUE row per `profile_version_id` — validated by REQ-M3-07 before a version is accepted.
- Multiplier *values* live on the row (`influence_multiplier`, `criticality_multiplier`); the *mapping* from category → default value is a small seed/config table maintained separately from client data so it can be tuned globally without touching every deployment's profile (see `05-schema-reasoning.md` → `finding_type_config`).
- In Phase 1, every table on this page is edited by the CS lead directly through the YAML profile file, not a UI — see `decisions/00-open-questions-resolved.md` Q2 and `decisions/01-mvp-scope-and-phasing.md`.
