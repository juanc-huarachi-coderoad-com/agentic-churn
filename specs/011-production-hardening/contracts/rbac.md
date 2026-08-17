# Contract: Role-based access, applied to existing routes

Not a new route — a new authorization dependency (`require_full_access`,
`app.auth.application.dependencies`, research.md Decision 2) applied to the write-capable
subset of the routes `architecture/07-api-spec.md` already documents. No request/response
shape changes on any of them; only the set of callers who can reach them changes.

## Routes gaining `require_full_access` (was `get_current_user`)

| Route | Existing file |
|---|---|
| `POST /api/feedback` | `app/context/adapters/feedback_router.py` |
| `POST /api/profile/reload` | `app/context/adapters/profile_router.py` |
| `POST /api/profile` (new, this feature) | `app/context/adapters/profile_router.py` |
| `POST /api/ask` | `app/experience/adapters/ask_router.py` |
| `POST /api/drafts` | `app/experience/adapters/draft_router.py` |
| `POST /api/drafts/{id}/copy` | `app/experience/adapters/draft_router.py` |
| `POST /api/drafts/{id}/log-as-sent` | `app/experience/adapters/draft_router.py` |

## Routes unchanged (`get_current_user`, read-only)

| Route | Existing file |
|---|---|
| `GET /api/dashboard` | `app/experience/adapters/dashboard_router.py` |
| `GET /api/evidence/{id}` | `app/experience/adapters/evidence_router.py` |
| `GET /api/coverage` | `app/experience/adapters/coverage_router.py` |
| `GET /api/profile` | `app/context/adapters/profile_router.py` |

## New response for a blocked account executive

| Status | Body |
|---|---|
| `403` | `{"detail": "This action is not available for your account."}` — a plain, non-technical message (matching the existing `401`'s already-generic wording, `requirements/14-authentication.md` REQ-AUTH-08's "never reveal more than necessary" precedent), not a raw role-name-dropping error |

No change to `POST /auth/login` or `POST /auth/logout` — every role continues to authenticate
identically; only post-authentication route access narrows for `account_executive`.

## FR-008: every decision is logged, not just enforced

Every call to `require_full_access` (this contract) and `require_admin`
(`contracts/weight-recalibration.md`) emits one structured log line, regardless of outcome:

```json
{"event": "access_decision", "user_id": "uuid", "role": "account_executive", "outcome": "denied"}
```

This is a plain `logging` call, not a new database table or column — `users.role` is mutable,
so this is the only record of which role a given request was actually authorized under at the
time (`/speckit-analyze` finding G1).
