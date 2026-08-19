# Contract: Dashboard (adds `event_type` to pulse events)

`architecture/07-api-spec.md` defines the full `DashboardResponse` schema.
`specs/008-narrator-and-ask-agent/contracts/dashboard.md` documents every field this route
returned before this feature — unchanged here except for one addition, scoped to a single
nested field on `pulse_timeline` items.

## `GET /api/dashboard` — one new field on `PulseEvent`

Same route, same auth, same `state` precedence as features 006/008 — not re-specified
here. Added to every `pulse_timeline[]` entry, in every response state that includes pulse
events (`normal`, `source_down`, `catching_up`, `unresolved_person`):

```json
{
  "pulse_timeline": [
    {
      "event_id": "45765fc1-...",
      "occurred_at": "2026-08-17T09:12:00Z",
      "event_type": "ticket_state_change",
      "severity": "at_risk",
      "quoted_text": "Our team is spending too much time chasing updates.",
      "score_contribution_id": "9c21..."
    }
  ]
}
```

- `event_type`: one of `message | ticket_state_change | usage_measurement |
  survey_response | meeting | absence | crm_change` — the same closed enum already stored
  on `events.event_type` (`data-base/10-ddl-appendix.md`), read verbatim, never translated
  or re-derived by the backend. Always present (`NOT NULL` at the column level); never
  `null`, never an 8th value.
- `severity`: unchanged — still derived server-side from `finding_type`/`is_positive` via
  `pulse_severity()`, not affected by this addition.
- Every other `PulseEvent` field, and every other top-level `DashboardResponse` field
  (`client_header`, `score_block`, `contribution_bars`, `stakeholder_cards`,
  `coverage_line`, `narrator`), is unchanged by this feature.
- No new query parameter, no new endpoint, no change to the `_PULSE_WINDOW_DAYS` window or
  the `DISTINCT ON (e.id)` one-row-per-event contract feature 006 established.

## Traceability

`specs/016-dashboard-mockup-v2-refinement/spec.md` FR-005, FR-005a, FR-006;
`architecture/07-api-spec.md` `PulseEvent`; `data-base/10-ddl-appendix.md`'s `event_type`
enum (lines 124-127); `specs/008-narrator-and-ask-agent/contracts/dashboard.md` and
`specs/006-dashboard-evidence-trace/contracts/dashboard.md` (everything else on this route,
unchanged).
