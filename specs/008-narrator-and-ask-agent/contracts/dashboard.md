# Contract: Dashboard (adds narration)

`architecture/07-api-spec.md` defines the full `DashboardResponse` schema.
`specs/006-dashboard-evidence-trace/contracts/dashboard.md` documents every
field this route returned before this feature — unchanged here except for one
addition. This feature fills in the one field 006 explicitly left blocked:
`narrator_outputs` was permanently empty until now (`specs/
006-dashboard-evidence-trace/spec.md`'s own scope boundary).

## `GET /api/dashboard` — one new field

Same route, same auth, same `state` precedence as feature 006 — not
re-specified here. Added to the `normal` (and `source_down`/`catching_up`/
`unresolved_person`, which share the full shape) response only:

```json
{
  "client_header": { "client_name": "Meridian Logistics", "band": "at_risk", "days_to_renewal": 85 },
  "state": "normal",
  "score_block": { "score": 85.63, "band": "at_risk", "trend": [85.63, 85.63] },
  "contribution_bars": ["... unchanged from feature 006 ..."],
  "narrator": {
    "headline": "We took 19 hours to reply to a P1 ticket — we promised 4 — and Ana is pulling back at the same time.",
    "reasons": [
      { "text": "We took 19 hours to reply to ticket #456 — we promised 4.", "points": 39.0, "evidence_event_ids": ["45765fc1-..."] }
    ],
    "actions": [
      { "text": "Escalate #456 with engineering today", "owner": "Marta", "due_date": "2026-08-16" }
    ]
  },
  "pulse_timeline": ["... unchanged ..."],
  "stakeholder_cards": ["... unchanged ..."],
  "coverage_line": ["... unchanged ..."]
}
```

- `narrator`: `null` when no `narrator_outputs` row exists yet for the latest
  `score_runs.id` — the same "absent, not empty" discipline every other
  optional field on this response already follows (REQ-M8-P2), never an empty
  object or empty strings standing in for "not narrated yet."
- `narrator.headline`: either the fact-checked LLM headline, or the
  deterministic fallback template (`data-model.md`, `architecture/
  06-error-handling.md`) when every LLM candidate failed its fact-check —
  both are valid, real `narrator_outputs.headline` values; the response does
  not distinguish which produced this particular string (`fact_check_passed`
  is a persistence-layer field, not part of this contract).
- `narrator.reasons` / `narrator.actions`: only fact-check-passed reasons and
  owner-and-date-complete actions ever appear — never a discarded sentence,
  never a candidate action missing either field (REQ-M7-05/07).
- No field is added for the Ask bar's `Idle`/`Thinking`/`Answered` states —
  see `contracts/ask.md`; that's frontend request-lifecycle state around
  `POST /api/ask`, not part of this response.

## Traceability

`REQ-M8-01`, `REQ-M7-02` … `REQ-M7-08`; `architecture/07-api-spec.md`
`DashboardResponse`; `data-model.md`'s `NarratorOutput` shape;
`specs/006-dashboard-evidence-trace/contracts/dashboard.md` (everything else
on this route, unchanged).
