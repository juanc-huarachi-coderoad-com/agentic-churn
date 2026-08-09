# 04 · Schema — Client profile & context (M3)

See `requirements/03-client-profile.md`. Directly models the spec §6.2 YAML profile as versioned relational rows.

## `client_profile_versions`

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
| `authored_by` | TEXT | CS lead who submitted this version |
| `created_at` | TIMESTAMPTZ | |
| `is_current` | BOOLEAN | Exactly one TRUE row per deployment at any time |

## `stakeholders`

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

## `product_areas`

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `profile_version_id` | UUID FK → `client_profile_versions.id` | |
| `key` | TEXT | e.g. `tracking_api` |
| `criticality` | ENUM(`critical`,`standard`,`peripheral`) | |
| `criticality_multiplier` | NUMERIC(3,2) | e.g. critical = 1.50, standard = 1.00, peripheral = 0.60 (REQ-M3-03) |

## `commitments`

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `profile_version_id` | UUID FK → `client_profile_versions.id` | |
| `type` | ENUM(`first_response`,`recurring_sync`,`milestone`) | |
| `priority` | TEXT NULL | e.g. `P1`, applies to `first_response` |
| `threshold_business_hours` | NUMERIC(6,2) NULL | e.g. 4 |
| `cadence` | TEXT NULL | e.g. "weekly" for recurring syncs, drives the Absence collector |

## `profile_history_entries`

Free-form narrative history (spec §6.2 `history:` block) — context for readers, not scoring input.

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | |
| `profile_version_id` | UUID FK → `client_profile_versions.id` | |
| `event_date` | DATE | |
| `description` | TEXT | e.g. "major outage, improvement plan agreed" |

## Notes

- `stakeholders.signs_renewal` must have ≥ 1 TRUE row per `profile_version_id` — validated by REQ-M3-07 before a version is accepted.
- Multiplier *values* live on the row (`influence_multiplier`, `criticality_multiplier`); the *mapping* from category → default value is a small seed/config table maintained separately from client data so it can be tuned globally without touching every deployment's profile (see `06-schema-scoring.md` → `finding_type_config`).
