# Contract: Ask agent

> **Superseded for the answered-response shape**: `specs/014-ask-agent-response-formats/
> contracts/ask.md` is the current source of truth for `POST /api/ask`'s *answered* response
> — `AskComponentResponse`'s flat shape below is replaced by an `AskAnsweredResponse`
> carrying an ordered `parts` list (text and/or component parts). The decline/fallback
> response (`AskFallbackResponse`) documented below is unchanged and still authoritative.

`architecture/07-api-spec.md` already defines `POST /api/ask`'s request/
response schemas (`AskRequest`, `AskComponentResponse`, `AskFallbackResponse`)
— not re-specified here. This feature is the first to actually implement the
route; two additions to the documented schema, both from `/speckit-clarify`
(`spec.md` Clarifications, `research.md` Decisions 5/6).

## `POST /api/ask`

- **Auth**: bearer token required, same as every other route
  (`contracts/auth.md`, feature 002). `asked_by_user_id` is taken from the
  token, never the request body (matches `requested_by_user_id`'s existing
  pattern on `draft_messages`).
- **Request**: `{"question": "why did the score go up?"}`

### Response (200) — one of three shapes

**A rendered component** (7 of the 8 intents — `AskComponentResponse`):

```json
{
  "intent": "score_delta",
  "component": "delta_breakdown",
  "component_props": {
    "previous_score": 92.1,
    "current_score": 85.63,
    "causes": [
      { "label": "broken_response_promise", "points": -39.0, "score_contribution_id": "ba87c77f-..." }
    ]
  }
}
```

**The draft-composer handoff** (the 8th intent — same schema, new
`component` value, `research.md` Decision 5):

```json
{
  "intent": "write_to_stakeholder",
  "component": "draft_handoff",
  "component_props": { "issue_id": "iss-A", "stakeholder_id": "stk-ana" }
}
```

Not answered inline — feature 009's draft composer is what actually consumes
`component_props`; this feature only produces the handoff response, matching
`spec.md` FR-012a.

**A decline or fallback** (`AskFallbackResponse`):

```json
{ "fallback_text": "I describe today, I don't forecast.", "sources": [], "declined_reason": "prediction" }
```

```json
{ "fallback_text": "Ana doesn't have enough message history yet for a baseline comparison.", "sources": [], "declined_reason": "insufficient_history" }
```

`declined_reason`'s five values, each condition:

| Value | When |
|---|---|
| `prediction` | REQ-M9-05 — a forecasting question |
| `colleague_judgment` | REQ-M9-06 — a judgment/character-assessment question about a colleague or client stakeholder |
| `source_not_connected` | REQ-M9-07 — the referenced data source has no connected source |
| `insufficient_history` | New this feature (Clarifications) — "is this normal for X?" about a stakeholder with fewer than 5 confirmed-baseline messages; distinct from `source_not_connected` because the source *is* connected |
| `unclear` | `NULL` `matched_intent` — no known intent matched (REQ-M9-04) |

- **Failure (401)**: no token, or an invalid one.
- **Timing**: every response — component, handoff, decline, or fallback —
  completes within 3 seconds (REQ-M9-08); decline/fallback paths are
  typically far faster since neither calls a tool
  (`architecture/06-error-handling.md`'s 2.5s/no-retry budget).
- **Logging**: every call, regardless of outcome, produces exactly one
  `ask_queries` row (`data-model.md`).

## A guarantee this route depends on, not just documents

Every finding-lookup answer this route can render is backed by a
`status = 'validated'`-filtered read (`data-model.md`'s `FindingReadPort`
note) — a quarantined finding (feature 007's validation gate) is
structurally unreachable through `/api/ask`, the same as it is through the
scoring engine itself (FR-024). This was a real gap in the reused feature
006 read path, found and closed during `/speckit-analyze`, not an
assumption this contract merely restates.

## Traceability

`REQ-M9-01` … `REQ-M9-08`, `REQ-M9-P1` … `REQ-M9-P3`; `architecture/
07-api-spec.md` `/api/ask`; `decisions/03-langgraph-for-ask-agent.md`;
`data-model.md`'s `AskAgentState`/port shapes; `sequences/
02-sequence-ask-agent.md`.
