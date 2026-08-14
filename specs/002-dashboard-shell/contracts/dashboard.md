# Contract: Dashboard (shell)

`architecture/07-api-spec.md` defines the full `DashboardResponse` schema
(`client_header`, `score_block`, `contribution_bars`, `pulse_timeline`,
`stakeholder_cards`, `coverage_line`) — that schema is not re-specified here. This
feature populates only a subset of it honestly; the rest is feature 006's job.

## `GET /api/dashboard`

- **Auth**: bearer token required (`contracts/auth.md`).
- **Response (200)**, this feature's actual shape — a narrowed view of the full schema:

  ```json
  {
    "client_header": { "client_name": "Meridian Logistics" },
    "state": "learning",
    "learning_message": "Still learning — 0 of 6 signal types available."
  }
  ```

  - `client_header.client_name`: read from the current (`is_current = true`)
    `client_profile_versions` row (`REQ-M8-01`).
  - `state`: always `"learning"` in this feature — no other dashboard state
    (`healthy`/`watch`/`at_risk`) is reachable until `score_runs` data exists
    (feature 006). This is an honest, permanent-for-now value, not a placeholder to be
    silently swapped later without a spec change.
  - `learning_message`: the exact copy pattern from `REQ-M8-07` — "still learning — N of
    6 signal types available" — with `N = 0`, since no source collectors are connected
    yet (build-order Phase 3+).
  - `score_block`, `contribution_bars`, `pulse_timeline`, `stakeholder_cards`,
    `coverage_line` from the full schema are **absent** from this feature's response
    (not present as empty arrays/nulls masquerading as "no data yet" — genuinely not
    part of this feature's contract, to avoid the frontend building against a shape that
    would need reworking once feature 006 fills them in for real).

- **Response (200), no current profile**: `{"client_header": null, "state": "no_profile"}`
  — the explicit state from spec.md's Edge Cases, for a freshly-provisioned, unseeded
  database.
- **Failure (401)**: no token, or an invalid one — see `contracts/auth.md`.

## Traceability

`REQ-M8-01`, `REQ-M8-05`, `REQ-M8-07`; `architecture/07-api-spec.md` §Dashboard reads.
