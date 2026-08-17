# Contract: `PATCH /api/admin/finding-types/{finding_type}`

New route — no prior document names it, since weight recalibration (Q4) was always described
as a workshop *process* (`decisions/00-open-questions-resolved.md`) whose *system-side*
deliverable this feature defines for the first time (spec.md Assumptions).

## Request

```json
{
  "base_points": "number (>= 0)"
}
```

Only `base_points` is editable through this route — `confidence_floor`, `min_evidence_count`,
and `half_life_days` (`finding_type_config`'s other tunable columns) are out of this feature's
scope; the weight-elicitation workshop this route serves (`decisions/00-open-questions-
resolved.md` Q4) is specifically about the point value, not the validation gate's thresholds.

## Responses

| Status | When | Body |
|---|---|---|
| `200` | Weight updated, `finding_type_config.version` bumped, `finding_type_config_changes` row inserted, `RecomputeScoreUseCase` triggered with `trigger="weight_edit_replay"` | `{"finding_type": "string", "base_points": "number", "config_version": "string", "changed_at": "timestamp"}` |
| `401` | Missing/expired/revoked token | `ErrorResponse` |
| `403` | `role != "admin"` (FR-016 — includes `cs_lead`, not just `account_executive`) | `ErrorResponse` |
| `404` | `finding_type` doesn't exist in `finding_type_config` | `ErrorResponse` |
| `422` | `base_points < 0` | `ErrorResponse` |

`changed_by_user_id` is taken from the bearer token, identical to every other "who did this"
column in this codebase.

## Note on scope

This route is deliberately narrower than a general "config editor" — it exists to close the
one gap `decisions/00-open-questions-resolved.md` Q4 names (updating a base weight without a
code deploy), not to become a general-purpose admin console. Adding editability for
`confidence_floor`/`min_evidence_count`/`half_life_days` is a future decision, not a silent
scope expansion of this route.
