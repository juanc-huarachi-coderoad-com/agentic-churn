# Contract: Dashboard (full)

`architecture/07-api-spec.md` defines the full `DashboardResponse` schema —
not re-specified here. This feature completes it; `specs/002-dashboard-shell/
contracts/dashboard.md` documents the narrowed shell response this route
returned before this feature (still the response for `no_profile`/`learning`
states — see below, unchanged from that contract).

## `GET /api/dashboard`

- **Auth**: bearer token required (`contracts/auth.md`, feature 002).
- **Response (200)** — `state` drives which shape renders:

  **`no_profile` / `learning`** (feature 002's states, `learning`'s message now
  computed for real — `research.md`):

  ```json
  {
    "client_header": { "client_name": "Meridian Logistics" },
    "state": "learning",
    "learning_message": "Still learning — 3 of 6 signal types available."
  }
  ```

  **`healthy_quiet`** (FR-004, REQ-M8-05):

  ```json
  {
    "client_header": { "client_name": "Meridian Logistics", "band": "healthy", "days_to_renewal": 85 },
    "state": "healthy_quiet",
    "message": "Nothing needs you today. Last checked 4 minutes ago."
  }
  ```

  **`source_down` / `catching_up` / `unresolved_person`** — same full shape as
  `normal` below, with an added `state`/`message` pair rendered as a banner
  above the normal component set (FR-006):

  ```json
  { "state": "source_down", "message": "Email hasn't been read since Tue 09:14 — reconnect." }
  ```

  **`normal`** — the full `DashboardResponse` (`architecture/07-api-spec.md`),
  e.g. this deployment's real worked contribution (`data-model.md`):

  ```json
  {
    "client_header": { "client_name": "Meridian Logistics", "band": "at_risk", "days_to_renewal": 85 },
    "state": "normal",
    "score_block": { "score": 85.63, "band": "at_risk", "trend": [85.63, 85.63] },
    "contribution_bars": [
      { "score_contribution_id": "ba87c77f-...", "label": "broken_response_promise", "points": 39.0, "is_positive": false },
      { "score_contribution_id": "2f29429f-...", "label": "commitment_met", "points": 4.0, "is_positive": true }
    ],
    "pulse_timeline": [
      { "event_id": "45765fc1-...", "occurred_at": "2026-08-10T12:40:00Z", "severity": "at_risk", "quoted_text": "Slow API response" }
    ],
    "stakeholder_cards": [
      { "stakeholder_id": "21000000-...", "name": "Ana Reyes", "role": "CTO", "tone_trajectory": "unknown", "last_seen_at": "2026-08-13T14:14:00Z", "status": "active" }
    ],
    "coverage_line": { "sources_read": 3, "sources_expected": 3, "complete_to": "2026-08-15T13:01:00Z", "status": "ok" }
  }
  ```

  - `client_header.client_name`: current `client_profile_versions` row
    (REQ-M8-01, unchanged from feature 002). `client_header.band`: `score_
    block.band` echoed. `client_header.days_to_renewal`: computed from that
    same `client_profile_versions` row's `renewal_date`, feature 002's
    `ClientProfileRepositoryPort` extended by one field (`research.md`'s
    Decision, `/speckit-analyze` finding CV2) — not a new port.
  - `score_block.trend`: last 14 days, one point per day — that day's last
    `score_runs.score` (`research.md`).
  - `contribution_bars`: every `score_contributions` row for the latest
    `score_runs.id`, `label` = the finding's `finding_type` (no separate label
    column exists on `finding_type_config` — `checklists/requirements.md`'s
    own note on this).
  - `pulse_timeline`: 14-day window, finding-cited events only, `severity` per
    `research.md`'s mapping.
  - `stakeholder_cards`: every current profile stakeholder; `tone_trajectory`
    always `"unknown"`; `status` from the 4-week activity window
    (`research.md`).
  - `coverage_line`: latest `coverage_reports` row.

- **Response (200), no current profile**: unchanged from feature 002 —
  `{"client_header": null, "state": "no_profile"}`.
- **Failure (401)**: no token, or an invalid one — see `contracts/auth.md`.

## Traceability

`REQ-M8-01` … `REQ-M8-10`, `REQ-M8-P1`, `REQ-M8-P2`; `architecture/07-api-
spec.md` §Dashboard reads; `research.md`'s state-precedence and window
Decisions.
