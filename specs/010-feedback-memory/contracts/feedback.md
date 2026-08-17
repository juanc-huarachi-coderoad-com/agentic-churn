# Contract: `POST /api/feedback`

Already documented in `architecture/07-api-spec.md` (route table + OpenAPI
`FeedbackRequest` schema) since before this feature existed — this feature
is the route's first real implementation, adding no new field to the
already-ratified request schema.

## Request

```json
{
  "finding_id": "uuid | null",
  "issue_id": "uuid | null",
  "verdict": "correct | false_alarm | resolved"
}
```

`submitted_by_user_id` is never in the body — taken from the bearer token
(`CurrentUser.user_id`), matching `/api/ask`'s `asked_by_user_id` and
`/api/drafts`' equivalent precedent.

## Responses

| Status | When | Body |
|---|---|---|
| `204` | Verdict recorded, `damping_weights` upserted | none |
| `401` | Missing/expired/revoked token | `ErrorResponse` (existing auth precedent) |
| `422` | Neither `finding_id` nor `issue_id` set, **or** `verdict` is `false_alarm`/`correct` with only `issue_id` set (FR-005a) | `ErrorResponse` |
| `404` | `finding_id` doesn't resolve to a validated finding, or `issue_id` doesn't resolve to an issue with at least one mapped finding | `ErrorResponse` |

No `200`/`201` — this is a fire-and-forget action, matching `/api/drafts/
{id}/copy`'s existing `204`-only precedent (FR-002: one click, no
confirmation step, spec §11.6). The frontend does not read a response body;
it re-fetches the affected card's data (evidence trace) to pick up the new
`disclosure_text`, the same pattern already used elsewhere in this codebase
for post-mutation refresh (TanStack Query invalidation).

## Additive field: `EvidenceTraceResponse.disclosure_text`

`GET /api/evidence/{score_contribution_id}` — existing route, unchanged
request shape. One new, nullable response field:

```yaml
EvidenceTraceResponse:
  properties:
    # ...existing fields unchanged...
    disclosure_text:
      type: string
      nullable: true
      description: >
        REQ-M4-04. Present only when this finding's pattern currently has
        damping_weights.weight < 1.0; null otherwise — never an empty
        string (research.md Decision 4).
```

This is additive-only — every existing consumer of `EvidenceTraceResponse`
ignoring the new field continues to work unchanged.

## No change to `AskComponentResponse`

`component_props`'s `causes`/`ranked_issues` items already carry
`score_contribution_id` server-side
(`backend/app/experience/adapters/ask_agent_graph.py:224`) — this feature
adds no backend field here, only a frontend type/UI change to read and use
the field that already exists (research.md Decision 3).
