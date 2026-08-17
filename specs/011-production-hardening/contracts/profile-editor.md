# Contract: `POST /api/profile`

`architecture/07-api-spec.md` already names this route as the Post-MVP replacement for
`/api/profile/reload`'s YAML-file workflow — this feature is its first real implementation.
`/api/profile/reload` is **not removed** — it stays available for a deployment that still
prefers direct YAML editing (`decisions/00-open-questions-resolved.md` Q2 never mandated
retiring it, only adding the UI alternative).

**`GET /api/profile`'s `ProfileResponse` gains two fields** (`exclusions: list[str]`,
`communication_norms: str | None`) — a real gap found while wiring the editor: FR-017
requires the editor to *view* both, but neither was ever in the response at all, even before
this feature. `ProfileVersionSummary` (`app.context.application.ports`) and both its adapter
construction sites (`insert_new_version`, `get_current`) gained the same two fields.

## Request

**Corrected during implementation**: the field names below were originally invented at
plan time without reading the actual domain schema. The route instead accepts
`ClientProfileInput` (`backend/app/context/domain/profile_schema.py`) **directly and
unmodified** as its body — the exact same Pydantic model `load_profile_yaml` already builds
from the YAML file, so FastAPI validates a JSON submission with byte-identical rules,
including every field-level and cross-field rule (e.g. "at least one stakeholder must have
`signs_renewal: true`"), with no separate request model to keep in sync:

```json
{
  "client": "string",
  "renewal_date": "date (ISO-8601)",
  "contract_value_band": "strategic | standard | smb",
  "business_goals": ["string"],
  "stakeholders": [
    {
      "id": "string", "name": "string", "role": "string | null",
      "influence": "sponsor | daily_user | unknown", "signs_renewal": "boolean",
      "identifiers": ["string"]
    }
  ],
  "product_areas": [{"key": "string", "criticality": "critical | standard | peripheral"}],
  "commitments": [
    {
      "type": "string", "priority": "string | null",
      "threshold_business_hours": "number | null", "cadence": "string | null"
    }
  ],
  "communication": {
    "working_hours": "string, e.g. \"08:00-18:00\"",
    "timezone": "string",
    "languages": ["string"],
    "norms": "string | null"
  },
  "exclusions": ["string"],
  "history": [{"date": "date (ISO-8601)", "event": "string"}]
}
```

Note this is **not** the same shape as `GET /api/profile`'s `ProfileResponse` — the read side
is a reduced summary (no `business_goals`, no `communication.working_hours`/`timezone`/
`languages`, no `history`); the frontend editor (`frontend/src/profile-editor/`) resubmits
fixed defaults for those fields rather than exposing them for editing, a documented,
deliberate limitation (FR-017 only requires stakeholders/exclusions/renewal date/contract
value band/communication norms to be viewable and editable, not the full YAML surface).

## Responses

| Status | When | Body |
|---|---|---|
| `200` | Valid submission — new `client_profile_versions` row created, replay + rescore triggered | `ProfileResponse` (the new current version) |
| `401` | Missing/expired/revoked token | `ErrorResponse` |
| `403` | Authenticated as `account_executive` (User Story 2's `require_full_access` gate) | `ErrorResponse` |
| `422` | Same validation rules `POST /api/profile/reload` already enforces (malformed date, reference to a nonexistent stakeholder, etc.) — field-level detail, no new version created | `ErrorResponse` |

`authored_by_user_id` is taken from the bearer token, identical to every other "who did this"
column in this codebase — never from the request body.

## Frontend contract

`frontend/src/profile-editor/` (currently an empty, scaffolded directory) implements a form
(React Hook Form + Zod, per constitution P11) that:
1. Loads current state from `GET /api/profile` on mount (TanStack Query).
2. Submits via `POST /api/profile` on save (TanStack Query mutation).
3. Surfaces `422`'s field-level errors inline, per field — no generic toast for a validation
   failure a specific field caused.
