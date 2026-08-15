# Contract: Evidence trace panel

`architecture/07-api-spec.md` defines the full `EvidenceTraceResponse` schema —
not re-specified here.

## `GET /api/evidence/{score_contribution_id}`

- **Auth**: bearer token required.
- **Path parameter**: `score_contribution_id` — a `score_contributions.id`
  (not a `findings.id` — the same contribution can only ever belong to one
  finding, but the evidence panel is always opened from a rendered
  contribution bar, per FR-007).
- **Response (200)** — `data-model.md`'s worked example, verbatim:

  ```json
  {
    "finding_id": "ba87c77f-...",
    "finding_type": "broken_response_promise",
    "points": 39.0,
    "baseline_value": "responds within 4 promised business hours",
    "current_value": "50.0 business hours elapsed, still open",
    "what_changed": [
      "response time exceeded the promised threshold",
      "the ticket has not yet resolved"
    ],
    "quoted_messages": [
      { "event_id": "45765fc1-...", "text": "Slow API response", "occurred_at": "2026-08-10T12:40:00Z" }
    ],
    "arithmetic_explanation": "Base 20 points for a broken response promise, increased 50% because tracking_api is critical, increased 30% because the ticket is still open and overdue — 39.0 points total."
  }
  ```

  - `baseline_value`/`current_value`/`what_changed`: `data-model.md`'s
    per-`finding_type` dispatch table.
  - `quoted_messages`: every event in the finding's `cited_event_ids`,
    resolved and decrypted where a real body exists; a `ticket_state_change`'s
    own title stands in when there's no message body (still real, still
    attributed, never fabricated — spec.md's Edge Cases).
  - `arithmetic_explanation`: one clause per non-neutral `score_contributions`
    factor, `research.md`'s Decision — never a bare formula, never a generated
    sentence.

- **Response (200), a cited message fails to decrypt**: that one entry in
  `quoted_messages` carries `"text": null` instead of failing the whole
  response (spec.md's Edge Cases) — every other field still renders.
- **Response (200), a `finding_type` outside the five-entry dispatch table**
  (`research.md`'s fallback Decision, `/speckit-analyze` finding CV1 — real
  today for `escalation_language`/`tone_deterioration`/`csat_deviation`, the
  finding types feature 007's readers will eventually own):

  ```json
  {
    "finding_id": "a23cd997-...",
    "finding_type": "escalation_language",
    "points": 9.52,
    "baseline_value": "a detailed comparison for this finding type isn't available until its owning reader ships",
    "current_value": "a detailed comparison for this finding type isn't available until its owning reader ships",
    "what_changed": [],
    "quoted_messages": [
      { "event_id": "585b514e-...", "text": "...", "occurred_at": "2026-08-10T14:14:00Z" }
    ],
    "arithmetic_explanation": "Base 14 points for escalation_language, increased 60% because Ana signs the renewal, reduced 15% because the reader was 85% confident — 9.52 points total."
  }
  ```

  `quoted_messages`/`arithmetic_explanation` are unaffected by the fallback —
  both are already generic over `score_contributions`' stored columns, never
  dependent on the five-entry dispatch (`research.md`).
- **Failure (404)**: `score_contribution_id` doesn't resolve to a real row.
- **Failure (401)**: no token, or an invalid one.

## Traceability

`REQ-M8-08`; `base/...md` §11.4; `architecture/07-api-spec.md`'s
`EvidenceTraceResponse`; `research.md`'s evidence-dispatch and arithmetic-
formatting Decisions.
